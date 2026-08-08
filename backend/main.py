import os
import sys
import pickle
import time
from datetime import datetime
from typing import List, Optional
import pandas as pd

from fastapi import FastAPI, HTTPException, Header, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from bson import ObjectId
import bson

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.db import (
    users_col,
    keystroke_events_col,
    user_models_col,
    session_scores_col,
    get_user_by_username
)
from backend.auth import (
    hash_password,
    verify_password,
    create_session,
    get_user_id_from_token
)
from backend.pipeline import (
    extract_digraphs,
    compute_windows,
    train_user_model,
    calibrate_thresholds,
    score_window,
    explain_window,
    FEATURE_NAMES
)

app = FastAPI(title="Continuous Keystroke Authentication API")

# Enable CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic Schemas
class UserAuthSchema(BaseModel):
    username: str
    password: str

class KeystrokeEventSchema(BaseModel):
    key: str
    down_time: float
    up_time: float

class KeystrokeBatchSchema(BaseModel):
    session_id: Optional[str] = None
    events: List[KeystrokeEventSchema]

# Dependency to get current user from session token
async def get_current_user_id(authorization: Optional[str] = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid Authorization header"
        )
    token = authorization.split(" ")[1]
    user_id = get_user_id_from_token(token)
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired or invalid token"
        )
    return user_id

@app.post("/signup")
async def signup(credentials: UserAuthSchema):
    username = credentials.username.strip()
    if not username or not credentials.password:
        raise HTTPException(status_code=400, detail="Username and password are required")
        
    existing = get_user_by_username(username)
    if existing:
        raise HTTPException(status_code=400, detail="Username already exists")
        
    pwd_hash = hash_password(credentials.password)
    users_col.insert_one({
        "username": username,
        "password_hash": pwd_hash,
        "created_at": datetime.utcnow()
    })
    return {"message": "User created successfully"}

@app.post("/login")
async def login(credentials: UserAuthSchema):
    username = credentials.username.strip()
    user = get_user_by_username(username)
    if not user or not verify_password(credentials.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid username or password")
        
    token = create_session(str(user["_id"]))
    return {
        "token": token,
        "username": username,
        "user_id": str(user["_id"])
    }

@app.post("/enroll/keystrokes")
async def enroll_keystrokes(batch: KeystrokeBatchSchema, user_id: str = Depends(get_current_user_id)):
    if not batch.events:
        raise HTTPException(status_code=400, detail="No keystroke events provided")
        
    event_docs = []
    for ev in batch.events:
        event_docs.append({
            "user_id": user_id,
            "session_id": "enrollment",
            "key": ev.key,
            "down_time": ev.down_time,
            "up_time": ev.up_time,
            "type": "enrollment",
            "timestamp": datetime.utcnow()
        })
        
    keystroke_events_col.insert_many(event_docs)
    
    # Return count of total enrollment keystrokes for this user
    total_count = keystroke_events_col.count_documents({"user_id": user_id, "type": "enrollment"})
    return {"message": f"Saved {len(batch.events)} events.", "total_enrollment_keystrokes": total_count}

@app.post("/enroll/train")
async def enroll_train(user_id: str = Depends(get_current_user_id)):
    # Retrieve enrollment events
    events = list(keystroke_events_col.find({"user_id": user_id, "type": "enrollment"}).sort("down_time", 1))
    if len(events) < 350:
        raise HTTPException(
            status_code=400, 
            detail=f"Insufficient keystrokes for training. Have {len(events)}, need at least 350."
        )
        
    # Convert to DataFrame
    events_df = pd.DataFrame([{
        "key": ev["key"],
        "down_time": ev["down_time"],
        "up_time": ev["up_time"]
    } for ev in events])
    
    # Process digraphs and windows
    digraphs_df = extract_digraphs(events_df)
    windows_df = compute_windows(digraphs_df)
    
    if len(windows_df) < 1:
        raise HTTPException(
            status_code=400,
            detail=f"Could not construct any windows from typing. Keystrokes may be too sparse or filtered as outliers. Type steadily and continuously."
        )
        
    # Train Isolation Forest
    try:
        model = train_user_model(windows_df)
        low_cut, high_cut = calibrate_thresholds(model, windows_df)
        
        # Check if thresholds are equal (can happen with very little data)
        if low_cut >= high_cut:
            high_cut = low_cut + 0.05
            
        # Pickle model
        model_bytes = pickle.dumps(model)
        
        # Save to database
        user_models_col.update_one(
            {"user_id": user_id},
            {
                "$set": {
                    "model_binary": bson.Binary(model_bytes),
                    "low_cut": float(low_cut),
                    "high_cut": float(high_cut),
                    "updated_at": time.time(),
                    # Store features for retraining/explainability background reference
                    "enrollment_features": windows_df[FEATURE_NAMES].to_dict('records')
                }
            },
            upsert=True
        )
        
        return {
            "message": "Model trained and saved successfully",
            "windows_count": len(windows_df),
            "low_threshold": low_cut,
            "high_threshold": high_cut
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Training failed: {str(e)}")

@app.post("/session/keystrokes")
async def session_keystrokes(batch: KeystrokeBatchSchema, user_id: str = Depends(get_current_user_id)):
    if not batch.session_id:
        raise HTTPException(status_code=400, detail="Session ID is required")
    if not batch.events:
        return {"status": "success", "message": "No events in batch"}
        
    # Store raw session events
    event_docs = []
    for ev in batch.events:
        event_docs.append({
            "user_id": user_id,
            "session_id": batch.session_id,
            "key": ev.key,
            "down_time": ev.down_time,
            "up_time": ev.up_time,
            "type": "session",
            "timestamp": datetime.utcnow()
        })
    keystroke_events_col.insert_many(event_docs)
    
    # Retrieve user model
    model_doc = user_models_col.find_one({"user_id": user_id})
    if not model_doc:
        raise HTTPException(status_code=400, detail="User model not trained. Complete enrollment first.")
        
    model = pickle.loads(model_doc["model_binary"])
    low_cut = model_doc["low_cut"]
    high_cut = model_doc["high_cut"]
    
    # Retrieve all session events to re-evaluate windows
    session_events = list(keystroke_events_col.find({
        "user_id": user_id,
        "session_id": batch.session_id,
        "type": "session"
    }).sort("down_time", 1))
    
    events_df = pd.DataFrame([{
        "key": ev["key"],
        "down_time": ev["down_time"],
        "up_time": ev["up_time"]
    } for ev in session_events])
    
    digraphs_df = extract_digraphs(events_df)
    windows_df = compute_windows(digraphs_df)
    
    total_windows = len(windows_df)
    if total_windows < 1:
        return {
            "status": "collecting", 
            "message": f"Collecting keystroke events. Have {len(digraphs_df)}/50 digraphs for first window."
        }
        
    # Find how many windows have already been scored in this session
    scored_count = session_scores_col.count_documents({
        "user_id": user_id,
        "session_id": batch.session_id
    })
    
    # Score any newly completed windows
    newly_scored = []
    for w_idx in range(scored_count, total_windows):
        win_feat = windows_df.iloc[w_idx]
        score, risk = score_window(model, win_feat, low_cut, high_cut)
        
        score_doc = {
            "user_id": user_id,
            "session_id": batch.session_id,
            "window_index": w_idx,
            "anomaly_score": float(score),
            "risk_level": risk,
            "timestamp": datetime.utcnow()
        }
        session_scores_col.insert_one(score_doc)
        newly_scored.append({"window_index": w_idx, "score": score, "risk": risk})
        
    return {
        "status": "active",
        "total_windows": total_windows,
        "newly_scored": newly_scored
    }

@app.get("/session/score")
async def session_score(session_id: str, user_id: str = Depends(get_current_user_id)):
    # Get score history
    scores_cursor = session_scores_col.find({
        "user_id": user_id,
        "session_id": session_id
    }).sort("window_index", 1)
    
    scores = []
    for s in scores_cursor:
        scores.append({
            "window_index": s["window_index"],
            "anomaly_score": s["anomaly_score"],
            "risk_level": s["risk_level"]
        })
        
    if not scores:
        # Check how many events we have
        event_count = keystroke_events_col.count_documents({
            "user_id": user_id,
            "session_id": session_id,
            "type": "session"
        })
        return {
            "risk_level": "initializing",
            "score_history": [],
            "total_windows": 0,
            "message": f"Type to initialize authentication. Keystrokes logged: {event_count}"
        }
        
    # Determine risk level with consecutive window logic
    # "Require 3 consecutive medium/high windows before flagging a session"
    consecutive_hijack_count = 0
    flagged = False
    
    for s in scores:
        if s["risk_level"] in ["medium", "high"]:
            consecutive_hijack_count += 1
        else:
            consecutive_hijack_count = 0
            
        if consecutive_hijack_count >= 3:
            flagged = True
            
    latest_risk = scores[-1]["risk_level"]
    session_risk = "flagged" if flagged else latest_risk
    
    return {
        "risk_level": session_risk,
        "score_history": scores,
        "total_windows": len(scores)
    }

@app.get("/session/explain/{window_index}")
async def session_explain(session_id: str, window_index: int, user_id: str = Depends(get_current_user_id)):
    # Retrieve user model
    model_doc = user_models_col.find_one({"user_id": user_id})
    if not model_doc:
        raise HTTPException(status_code=404, detail="User model not found")
        
    model = pickle.loads(model_doc["model_binary"])
    
    # Reconstruct features for this session's window
    session_events = list(keystroke_events_col.find({
        "user_id": user_id,
        "session_id": session_id,
        "type": "session"
    }).sort("down_time", 1))
    
    events_df = pd.DataFrame([{
        "key": ev["key"],
        "down_time": ev["down_time"],
        "up_time": ev["up_time"]
    } for ev in session_events])
    
    digraphs_df = extract_digraphs(events_df)
    windows_df = compute_windows(digraphs_df)
    
    if window_index >= len(windows_df) or window_index < 0:
        raise HTTPException(status_code=404, detail=f"Window index {window_index} not found. Total windows: {len(windows_df)}")
        
    win_feat = windows_df.iloc[window_index]
    
    # Calculate SHAP values
    shap_vals = explain_window(model, win_feat)
    
    # Also get the feature values themselves for display context
    feature_values = win_feat[FEATURE_NAMES].to_dict()
    
    return {
        "window_index": window_index,
        "shap_values": shap_vals,
        "feature_values": feature_values
    }

@app.post("/session/end")
async def end_session(session_id: str, user_id: str = Depends(get_current_user_id)):
    """
    POST /session/end - Handles adaptive learning when the session finishes.
    If all windows in the session were low risk, add them to enrollment set and retrain.
    """
    scores = list(session_scores_col.find({
        "user_id": user_id,
        "session_id": session_id
    }))
    
    if not scores:
        return {"message": "Session ended. No scores logged."}
        
    # Determine if hijacked using same consecutive window logic
    consecutive_hijack_count = 0
    flagged = False
    
    # Sort scores by window_index to ensure chronological sequence
    sorted_scores = sorted(scores, key=lambda x: x.get("window_index", 0))
    for s in sorted_scores:
        if s["risk_level"] in ["medium", "high"]:
            consecutive_hijack_count += 1
        else:
            consecutive_hijack_count = 0
            
        if consecutive_hijack_count >= 3:
            flagged = True
            break
            
    is_safe = not flagged
    
    retrained = False
    if is_safe:
        print(f"Session {session_id} was safe (no hijacking detected). Triggering adaptive learning...")
        # Get user model details
        model_doc = user_models_col.find_one({"user_id": user_id})
        if model_doc:
            # Reconstruct window features from this session
            session_events = list(keystroke_events_col.find({
                "user_id": user_id,
                "session_id": session_id,
                "type": "session"
            }).sort("down_time", 1))
            
            events_df = pd.DataFrame([{
                "key": ev["key"],
                "down_time": ev["down_time"],
                "up_time": ev["up_time"]
            } for ev in session_events])
            
            digraphs_df = extract_digraphs(events_df)
            session_windows = compute_windows(digraphs_df)
            
            if len(session_windows) > 0:
                enrollment_features = model_doc.get("enrollment_features", [])
                
                # Combine existing enrollment and new session windows
                combined = enrollment_features + session_windows[FEATURE_NAMES].to_dict('records')
                # Cap at the most recent 500 windows
                combined = combined[-500:]
                
                # Retrain model
                X_train = pd.DataFrame(combined)
                model = train_user_model(X_train)
                low_cut, high_cut = calibrate_thresholds(model, X_train)
                
                if low_cut >= high_cut:
                    high_cut = low_cut + 0.05
                    
                # Save retrained model
                model_bytes = pickle.dumps(model)
                user_models_col.update_one(
                    {"user_id": user_id},
                    {
                        "$set": {
                            "model_binary": bson.Binary(model_bytes),
                            "low_cut": float(low_cut),
                            "high_cut": float(high_cut),
                            "updated_at": time.time(),
                            "enrollment_features": combined
                        }
                    }
                )
                retrained = True
                
    return {
        "message": "Session ended successfully.",
        "adaptive_learning_triggered": is_safe,
        "model_retrained": retrained
    }
