import os
import sys
import pickle
import time
from datetime import datetime, timedelta
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
    session_summaries_col,
    get_user_by_username
)
from backend.auth import (
    hash_password,
    verify_password,
    hash_pin,
    verify_pin,
    create_session,
    get_user_id_from_token,
    delete_session
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

# Setup logging
import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(title="Continuous Keystroke Authentication API")

# Enable CORS for frontend integration
# Allow configurable origin via environment variable
ALLOWED_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://localhost:5174").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health():
    """Health check endpoint for monitoring."""
    return {"status": "ok"}

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
    logger.info(f"Signup attempt for username: {credentials.username}")
    username = credentials.username.strip()
    password = credentials.password
    
    # Validation
    if not username or username.isspace():
        logger.warning(f"Signup rejected: empty username")
        raise HTTPException(status_code=400, detail="Username cannot be empty or only whitespace")
    
    # Validate username format (alphanumeric + underscore only)
    import re
    if not re.match(r'^[a-zA-Z0-9_]{3,20}$', username):
        logger.warning(f"Signup rejected: invalid username format: {username}")
        raise HTTPException(status_code=400, detail="Username must be 3-20 characters, alphanumeric and underscore only")
    
    if not password or len(password) < 8:
        logger.warning(f"Signup rejected: password too short for user {username}")
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters long")
    
    try:
        existing = get_user_by_username(username)
        if existing:
            logger.warning(f"Signup rejected: username {username} already exists")
            raise HTTPException(status_code=400, detail="Username already exists")
        
        pwd_hash = hash_password(password)
        # Generate a random 4-digit MFA PIN for user
        import random
        mfa_pin = str(random.randint(1000, 9999))
        mfa_pin_hash = hash_pin(mfa_pin)  # Hash the PIN before storing
        
        users_col.insert_one({
            "username": username,
            "password_hash": pwd_hash,
            "mfa_pin_hash": mfa_pin_hash,  # Store hash only, never plaintext
            "mfa_attempts": 0,  # Track failed verification attempts
            "created_at": datetime.utcnow()
        })
        logger.info(f"User {username} created successfully with MFA PIN")
        # Return plaintext PIN only once at signup - user must save it
        return {
            "message": "User created successfully",
            "mfa_pin": mfa_pin
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Database error during signup for {username}: {str(e)}")
        raise HTTPException(status_code=500, detail="Database error. Please try again later.")

@app.post("/login")
async def login(credentials: UserAuthSchema):
    username = credentials.username.strip()
    
    try:
        user = get_user_by_username(username)
        if not user or not verify_password(credentials.password, user["password_hash"]):
            raise HTTPException(status_code=401, detail="Invalid username or password")
            
        token = create_session(str(user["_id"]))
        # Don't return MFA PIN - user already saved it at signup
        return {
            "token": token,
            "username": username,
            "user_id": str(user["_id"])
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error for {username}: {str(e)}")
        raise HTTPException(status_code=500, detail="Authentication service error. Please try again.")

@app.post("/logout")
async def logout(authorization: Optional[str] = Header(None)):
    """Delete the current session token."""
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ")[1]
        delete_session(token)
    return {"message": "Logged out successfully"}

@app.post("/enroll/keystrokes")
async def enroll_keystrokes(batch: KeystrokeBatchSchema, user_id: str = Depends(get_current_user_id)):
    if not batch.events:
        raise HTTPException(status_code=400, detail="No keystroke events provided")
    
    try:
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
    except Exception as e:
        logger.error(f"Error saving enrollment keystrokes for user {user_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to save keystroke data. Please try again.")

@app.post("/enroll/train")
async def enroll_train(user_id: str = Depends(get_current_user_id)):
    logger.info(f"Training model for user: {user_id}")
    # Retrieve enrollment events
    events = list(keystroke_events_col.find({"user_id": user_id, "type": "enrollment"}).sort("down_time", 1))
    logger.info(f"Found {len(events)} enrollment events for user {user_id}")
    
    if len(events) < 350:
        logger.warning(f"Insufficient events for user {user_id}: {len(events)}/350")
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
    
    logger.info(f"Extracted {len(digraphs_df)} digraphs and {len(windows_df)} windows for user {user_id}")
    
    if len(windows_df) < 1:
        logger.error(f"No windows generated for user {user_id}")
        raise HTTPException(
            status_code=400,
            detail=f"Could not construct any windows from typing. Keystrokes may be too sparse or filtered as outliers. Type steadily and continuously."
        )
    
    # Split enrollment into training (80%) and calibration (20%) subsets
    split_idx = int(len(windows_df) * 0.8)
    train_windows = windows_df.iloc[:split_idx]
    calibrate_windows = windows_df.iloc[split_idx:]
    
    if len(train_windows) < 1 or len(calibrate_windows) < 1:
        logger.error(f"Insufficient windows for split for user {user_id}")
        raise HTTPException(
            status_code=400,
            detail=f"Insufficient windows for training and calibration. Need at least 2 windows. Have {len(windows_df)} windows."
        )
        
    # Train Isolation Forest on training subset
    try:
        model = train_user_model(train_windows)
        low_cut, high_cut = calibrate_thresholds(model, calibrate_windows)
        
        logger.info(f"Model trained for user {user_id}: low_cut={low_cut:.4f}, high_cut={high_cut:.4f}")
        
        # Check if thresholds are equal (can happen with very little data)
        if low_cut >= high_cut:
            high_cut = low_cut + 0.01
            logger.warning(f"Adjusted high_cut for user {user_id} to avoid threshold collision")
            
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
        
        logger.info(f"Model successfully saved for user {user_id}")
        
        return {
            "message": "Model trained and saved successfully",
            "windows_count": len(windows_df),
            "training_windows": len(train_windows),
            "calibration_windows": len(calibrate_windows),
            "low_threshold": low_cut,
            "high_threshold": high_cut
        }
    except Exception as e:
        logger.error(f"Training failed for user {user_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Training failed: {str(e)}")

@app.get("/enroll/status")
async def enroll_status(user_id: str = Depends(get_current_user_id)):
    """Check if user has a trained biometric model."""
    model_doc = user_models_col.find_one({"user_id": user_id})
    return {
        "has_model": model_doc is not None,
        "enrollment_complete": model_doc is not None
    }

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
            "action_required": "ALLOW_ACCESS",
            "message": f"Type to initialize authentication. Keystrokes logged: {event_count}"
        }
        
    # Determine risk level with consecutive window logic for MFA challenge
    consecutive_hijack_count = 0
    flagged = False
    action_required = "ALLOW_ACCESS"
    
    # Count consecutive medium/high risk windows from the end
    for s in reversed(scores):
        if s["risk_level"] in ["medium", "high"]:
            consecutive_hijack_count += 1
        else:
            break
            
    # MFA Challenge: 2 consecutive medium/high windows
    if consecutive_hijack_count == 2:
        action_required = "PROMPT_MFA_CHALLENGE"
        
    # Terminate: 3+ consecutive medium/high windows
    if consecutive_hijack_count >= 3:
        flagged = True
        action_required = "TERMINATE_SESSION"
    
    latest_risk = scores[-1]["risk_level"]
    
    # Simple risk level reporting
    if flagged:
        session_risk = "flagged"
    else:
        session_risk = latest_risk
    
    return {
        "risk_level": session_risk,
        "score_history": scores,
        "total_windows": len(scores),
        "action_required": action_required,
        "consecutive_warnings": consecutive_hijack_count
    }


@app.post("/session/verify_mfa")
async def verify_mfa(request: dict, user_id: str = Depends(get_current_user_id)):
    """
    Verify user's MFA PIN and reset consecutive warning counter if correct.
    Includes rate limiting: max 5 attempts before account lockout.
    """
    pin_input = request.get("pin", "")
    session_id = request.get("session_id", "")
    
    # Get user document
    user = users_col.find_one({"_id": ObjectId(user_id)})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Rate limiting: check failed attempt count
    attempts = user.get("mfa_attempts", 0)
    if attempts >= 5:
        logger.warning(f"MFA rate limit exceeded for user {user_id}")
        raise HTTPException(
            status_code=429, 
            detail="Too many failed verification attempts. Please log out and log in again to reset."
        )
    
    # Verify PIN against bcrypt hash
    mfa_pin_hash = user.get("mfa_pin_hash", "")
    if not verify_pin(pin_input, mfa_pin_hash):
        # Increment failed attempt counter
        users_col.update_one(
            {"_id": user["_id"]}, 
            {"$inc": {"mfa_attempts": 1}}
        )
        logger.warning(f"MFA verification failed for user {user_id} (attempt {attempts + 1}/5)")
        return {
            "success": False,
            "message": "Invalid PIN",
            "attempts_remaining": 5 - (attempts + 1)
        }
    
    # PIN is correct - reset attempt counter and mark windows as verified
    users_col.update_one(
        {"_id": user["_id"]}, 
        {"$set": {"mfa_attempts": 0}}
    )
    logger.info(f"MFA verification successful for user {user_id}, session {session_id}")
    
    # Get the last 2 windows and update them to "low" risk (reset consecutive counter)
    scores_cursor = session_scores_col.find({
        "user_id": user_id,
        "session_id": session_id,
        "risk_level": {"$in": ["medium", "high"]}
    }).sort("window_index", -1).limit(2)
    
    updated_count = 0
    for score in scores_cursor:
        session_scores_col.update_one(
            {"_id": score["_id"]},
            {"$set": {"risk_level": "low", "mfa_verified": True}}
        )
        updated_count += 1
    
    return {
        "success": True,
        "message": "Identity verified successfully",
        "windows_reset": updated_count
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

@app.get("/session/history")
async def session_history(user_id: str = Depends(get_current_user_id)):
    """
    Returns a list of past sessions for the current user with comprehensive details.
    Each entry includes: session_id, start_time, end_time, final_risk_status, window_count, model_retrained.
    """
    try:
        # Try to get from session_summaries collection first (has more details)
        summaries = list(session_summaries_col.find(
            {"user_id": user_id}
        ).sort("end_time", -1).limit(50))
        
        if summaries:
            result = []
            for summary in summaries:
                duration_seconds = 0
                if summary.get("start_time") and summary.get("end_time"):
                    duration_seconds = (summary["end_time"] - summary["start_time"]).total_seconds()
                
                result.append({
                    "session_id": summary["session_id"],
                    "start_time": summary["start_time"].isoformat() if summary.get("start_time") else None,
                    "end_time": summary["end_time"].isoformat() if summary.get("end_time") else None,
                    "duration_seconds": duration_seconds,
                    "duration_formatted": f"{int(duration_seconds // 60)}m {int(duration_seconds % 60)}s",
                    "final_risk_status": summary.get("final_risk", "unknown"),
                    "window_count": summary.get("total_windows", 0),
                    "low_count": summary.get("low_count", 0),
                    "medium_count": summary.get("medium_count", 0),
                    "high_count": summary.get("high_count", 0),
                    "was_flagged": summary.get("was_flagged", False),
                    "model_retrained": summary.get("model_retrained", False)
                })
            return {"sessions": result}
        
        # Fallback to aggregating from session_scores if no summaries
        pipeline = [
            {"$match": {"user_id": user_id}},
            {"$group": {
                "_id": "$session_id",
                "window_count": {"$sum": 1},
                "start_time": {"$min": "$timestamp"},
                "end_time": {"$max": "$timestamp"},
                "scores": {"$push": {"window_index": "$window_index", "risk_level": "$risk_level"}}
            }},
            {"$sort": {"end_time": -1}},
            {"$limit": 50}
        ]
        
        sessions = list(session_scores_col.aggregate(pipeline))
        
        result = []
        for sess in sessions:
            session_id = sess["_id"]
            
            # Determine final risk status using consecutive-window logic
            scores = sorted(sess["scores"], key=lambda x: x["window_index"])
            consecutive_hijack_count = 0
            flagged = False
            low_count = medium_count = high_count = 0
            
            for s in scores:
                if s["risk_level"] == "low":
                    low_count += 1
                elif s["risk_level"] == "medium":
                    medium_count += 1
                elif s["risk_level"] == "high":
                    high_count += 1
                    
                if s["risk_level"] in ["medium", "high"]:
                    consecutive_hijack_count += 1
                else:
                    consecutive_hijack_count = 0
                    
                if consecutive_hijack_count >= 3:
                    flagged = True
                    break
            
            final_risk = "flagged" if flagged else (scores[-1]["risk_level"] if scores else "unknown")
            
            duration_seconds = 0
            if sess.get("start_time") and sess.get("end_time"):
                duration_seconds = (sess["end_time"] - sess["start_time"]).total_seconds()
            
            result.append({
                "session_id": session_id,
                "start_time": sess["start_time"].isoformat() if sess.get("start_time") else None,
                "end_time": sess["end_time"].isoformat() if sess.get("end_time") else None,
                "duration_seconds": duration_seconds,
                "duration_formatted": f"{int(duration_seconds // 60)}m {int(duration_seconds % 60)}s",
                "final_risk_status": final_risk,
                "window_count": sess["window_count"],
                "low_count": low_count,
                "medium_count": medium_count,
                "high_count": high_count,
                "was_flagged": flagged,
                "model_retrained": False
            })
        
        return {"sessions": result}
    except Exception as e:
        logger.error(f"Error fetching session history for user {user_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch session history")


@app.get("/user/stats")
async def user_stats(user_id: str = Depends(get_current_user_id)):
    """
    Returns aggregate statistics for the current user including:
    - Total sessions
    - Total windows analyzed
    - Safe vs flagged session ratio
    - Model training info
    - Enrollment completion status
    """
    try:
        # Get model info
        model_doc = user_models_col.find_one({"user_id": user_id})
        enrollment_complete = model_doc is not None
        model_last_trained = None
        total_training_windows = 0
        
        if model_doc:
            model_last_trained = model_doc.get("updated_at")
            if model_last_trained:
                model_last_trained = datetime.fromtimestamp(model_last_trained).isoformat()
            enrollment_features = model_doc.get("enrollment_features", [])
            total_training_windows = len(enrollment_features)
        
        # Get session summaries
        summaries = list(session_summaries_col.find({"user_id": user_id}))
        
        total_sessions = len(summaries)
        safe_sessions = sum(1 for s in summaries if not s.get("was_flagged", False))
        flagged_sessions = sum(1 for s in summaries if s.get("was_flagged", False))
        total_windows = sum(s.get("total_windows", 0) for s in summaries)
        times_retrained = sum(1 for s in summaries if s.get("model_retrained", False))
        
        # Calculate average session duration
        durations = []
        for s in summaries:
            if s.get("start_time") and s.get("end_time"):
                duration = (s["end_time"] - s["start_time"]).total_seconds()
                durations.append(duration)
        
        avg_duration = sum(durations) / len(durations) if durations else 0
        
        # Get recent activity (last 7 days)
        seven_days_ago = datetime.utcnow() - timedelta(days=7)
        recent_sessions = sum(1 for s in summaries if s.get("end_time", datetime.min) > seven_days_ago)
        
        return {
            "enrollment_complete": enrollment_complete,
            "model_last_trained": model_last_trained,
            "total_training_windows": total_training_windows,
            "total_sessions": total_sessions,
            "safe_sessions": safe_sessions,
            "flagged_sessions": flagged_sessions,
            "total_windows_analyzed": total_windows,
            "times_model_retrained": times_retrained,
            "average_session_duration": f"{int(avg_duration // 60)}m {int(avg_duration % 60)}s",
            "recent_activity_7days": recent_sessions
        }
    except Exception as e:
        logger.error(f"Error fetching user stats for {user_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch user statistics")

@app.post("/session/end")
async def end_session(session_id: str, user_id: str = Depends(get_current_user_id)):
    """
    POST /session/end - Handles adaptive learning when the session finishes and stores session summary.
    If all windows in the session were low risk, add them to enrollment set and retrain.
    """
    try:
        scores = list(session_scores_col.find({
            "user_id": user_id,
            "session_id": session_id
        }).sort("window_index", 1))
        
        if not scores:
            return {"message": "Session ended. No scores logged.", "model_retrained": False}
        
        # Calculate statistics
        total_windows = len(scores)
        low_count = sum(1 for s in scores if s["risk_level"] == "low")
        medium_count = sum(1 for s in scores if s["risk_level"] == "medium")
        high_count = sum(1 for s in scores if s["risk_level"] == "high")
        
        # Determine if hijacked using same consecutive window logic
        consecutive_hijack_count = 0
        flagged = False
        
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
        final_risk = "flagged" if flagged else (scores[-1]["risk_level"] if scores else "unknown")
        
        # Store session summary
        start_time = scores[0].get("timestamp", datetime.utcnow())
        end_time = scores[-1].get("timestamp", datetime.utcnow())
        
        retrained = False
        if is_safe:
            logger.info(f"Session {session_id} was safe (no hijacking detected). Triggering adaptive learning...")
            # Get user model details
            model_doc = user_models_col.find_one({"user_id": user_id})
            if model_doc:
                # Reconstruct window features from this session
                session_events = list(keystroke_events_col.find({
                    "user_id": user_id,
                    "session_id": session_id,
                    "type": "session"
                }).sort("down_time", 1))
                
                if len(session_events) > 0:
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
                            high_cut = low_cut + 0.01
                            
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
                        logger.info(f"Model retrained for user {user_id} after safe session")
        
        # Store comprehensive session summary
        session_summary = {
            "user_id": user_id,
            "session_id": session_id,
            "start_time": start_time,
            "end_time": end_time,
            "total_windows": total_windows,
            "low_count": low_count,
            "medium_count": medium_count,
            "high_count": high_count,
            "final_risk": final_risk,
            "was_flagged": flagged,
            "model_retrained": retrained,
            "created_at": datetime.utcnow()
        }
        
        session_summaries_col.insert_one(session_summary)
        
        return {
            "message": "Session ended successfully.",
            "adaptive_learning_triggered": is_safe,
            "model_retrained": retrained,
            "session_summary": {
                "total_windows": total_windows,
                "low_count": low_count,
                "medium_count": medium_count,
                "high_count": high_count,
                "final_risk": final_risk,
                "was_flagged": flagged
            }
        }
    except Exception as e:
        logger.error(f"Error ending session {session_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to end session")


# Run the server
if __name__ == "__main__":
    import uvicorn
    logger.info("Starting Continuous Keystroke Authentication Backend API...")
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
