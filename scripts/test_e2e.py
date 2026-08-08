import os
import sys
import requests
import pandas as pd
import time
from pathlib import Path

# Use relative paths based on script location
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
RECONSTRUCTED_CSV = PROJECT_ROOT / "data" / "reconstructed_events.csv"

API_BASE = "http://127.0.0.1:8000"

def run_e2e_test():
    print("Starting automated End-to-End system test...")
    
    # Check if reconstructed events exist
    if not os.path.exists(RECONSTRUCTED_CSV):
        print(f"Error: {RECONSTRUCTED_CSV} not found. Run parse_dataset.py first.")
        sys.exit(1)
        
    df = pd.read_csv(RECONSTRUCTED_CSV)
    
    # Filter p001 (genuine user) and p002 (attacker)
    df_p1 = df[df['participant'] == 'p001'].sort_values('down_time')
    df_p2 = df[df['participant'] == 'p002'].sort_values('down_time')
    
    # Setup test credentials
    username = f"e2e_user_{int(time.time())}"
    password = "SecurePassword123"
    
    # 1. Signup
    print(f"\n1. Signing up user: {username}...")
    signup_res = requests.post(f"{API_BASE}/signup", json={
        "username": username,
        "password": password
    })
    print("Signup Status:", signup_res.status_code, signup_res.json())
    assert signup_res.status_code == 200
    
    # 2. Login
    print("\n2. Logging in...")
    login_res = requests.post(f"{API_BASE}/login", json={
        "username": username,
        "password": password
    })
    print("Login Status:", login_res.status_code)
    assert login_res.status_code == 200
    login_data = login_res.json()
    token = login_data["token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # 3. Biometric Enrollment
    # We take the first 3000 events of p001 to simulate enrollment typing
    enroll_events = df_p1.iloc[:3000].to_dict('records')
    # Convert timestamps to float relative to start of enrollment
    min_time = enroll_events[0]['down_time']
    enroll_payload = []
    for ev in enroll_events:
        enroll_payload.append({
            "key": str(ev['key']),
            "down_time": float(ev['down_time'] - min_time),
            "up_time": float(ev['up_time'] - min_time)
        })
        
    print(f"\n3. Submitting {len(enroll_payload)} enrollment keystroke events...")
    enroll_res = requests.post(f"{API_BASE}/enroll/keystrokes", headers=headers, json={
        "events": enroll_payload
    })
    print("Enroll submit status:", enroll_res.status_code, enroll_res.json())
    assert enroll_res.status_code == 200
    
    # Train the model
    print("Training Isolation Forest biometric model...")
    train_res = requests.post(f"{API_BASE}/enroll/train", headers=headers)
    print("Train status:", train_res.status_code, train_res.json())
    assert train_res.status_code == 200
    train_data = train_res.json()
    print(f"Model calibrated successfully. Low cut: {train_data['low_threshold']:.4f}, High cut: {train_data['high_threshold']:.4f}")
    
    # 4. Active Session Simulation
    session_id = f"e2e_sess_{int(time.time())}"
    print(f"\n4. Starting active session: {session_id}")
    
    # Simulate genuine typing
    # Take p001 events from index 3000 to 3300 (300 events, 6 windows)
    gen_session_events = df_p1.iloc[3000:3300].to_dict('records')
    min_gen_time = gen_session_events[0]['down_time']
    
    # Send genuine keystrokes in batches of 15
    print("\nTyping normally (Genuine User)...")
    batch_size = 15
    for i in range(0, len(gen_session_events), batch_size):
        batch = gen_session_events[i : i + batch_size]
        payload = []
        for ev in batch:
            payload.append({
                "key": str(ev['key']),
                "down_time": float(ev['down_time'] - min_gen_time),
                "up_time": float(ev['up_time'] - min_gen_time)
            })
        
        res = requests.post(f"{API_BASE}/session/keystrokes", headers=headers, json={
            "session_id": session_id,
            "events": payload
        })
        print(f"Sent batch {i//batch_size + 1} status:", res.status_code, res.json())
        assert res.status_code == 200
        
        # Poll score
        score_res = requests.get(f"{API_BASE}/session/score?session_id={session_id}", headers=headers)
        score_data = score_res.json()
        print(f"Current Session Risk: {score_data['risk_level'].upper()} (Windows evaluated: {score_data['total_windows']})")
        
    # Verify that the risk remains low/initializing (not hijacked)
    score_res = requests.get(f"{API_BASE}/session/score?session_id={session_id}", headers=headers)
    score_data = score_res.json()
    print(f"\nGenuine Session Risk State: {score_data['risk_level'].upper()}")
    assert score_data['risk_level'] != 'flagged'
    
    # Now simulate a Takeover Attack (Attacker typing)
    # Take p002 events (300 events, 6 windows) and append them to session
    print("\n--- ATTACK SIMULATION: Attacker takes over keyboard (User p002)... ---")
    attack_events = df_p2.iloc[:300].to_dict('records')
    
    # We continue the timing sequence from the last genuine event
    last_gen_up = gen_session_events[-1]['up_time'] - min_gen_time
    min_att_time = attack_events[0]['down_time']
    
    for i in range(0, len(attack_events), batch_size):
        batch = attack_events[i : i + batch_size]
        payload = []
        for ev in batch:
            payload.append({
                "key": str(ev['key']),
                # Continuation of session timeline
                "down_time": float(ev['down_time'] - min_att_time + last_gen_up + 1.0),
                "up_time": float(ev['up_time'] - min_att_time + last_gen_up + 1.0)
            })
            
        res = requests.post(f"{API_BASE}/session/keystrokes", headers=headers, json={
            "session_id": session_id,
            "events": payload
        })
        print(f"Attacker batch {i//batch_size + 1} status:", res.status_code, res.json())
        assert res.status_code == 200
        
        # Poll score
        score_res = requests.get(f"{API_BASE}/session/score?session_id={session_id}", headers=headers)
        score_data = score_res.json()
        print(f"Current Session Risk: {score_data['risk_level'].upper()} (Windows evaluated: {score_data['total_windows']})")
        
        if score_data['risk_level'] == 'flagged':
            print("\n[ALERT] SYSTEM LOCKDOWN: Hijacker detected and locked out successfully!")
            break
            
    # Verify that the session is flagged as hijacked
    score_res = requests.get(f"{API_BASE}/session/score?session_id={session_id}", headers=headers)
    score_data = score_res.json()
    print(f"\nFinal Session Risk State: {score_data['risk_level'].upper()}")
    assert score_data['risk_level'] == 'flagged'
    
    # 5. Explainability test for a flagged window
    flagged_win_idx = score_data['total_windows'] - 1
    print(f"\n5. Fetching SHAP explanation for flagged window {flagged_win_idx}...")
    explain_res = requests.get(f"{API_BASE}/session/explain/{flagged_win_idx}?session_id={session_id}", headers=headers)
    print("Explain status:", explain_res.status_code)
    assert explain_res.status_code == 200
    explain_data = explain_res.json()
    print("SHAP Values:", explain_data["shap_values"])
    print("Feature Values:", explain_data["feature_values"])
    
    print("\n[SUCCESS] ALL AUTOMATED END-TO-END TESTS PASSED SUCCESSFULLY! The Continuous Keystroke Biometric Authentication system functions flawlessly.")

if __name__ == "__main__":
    run_e2e_test()
