import os
import sys
import numpy as np
import pandas as pd
from pathlib import Path

# Use relative paths based on script location
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent

# Add the project root to python path to import backend modules
sys.path.append(str(PROJECT_ROOT))

from backend.pipeline import (
    extract_digraphs,
    compute_windows,
    train_user_model,
    calibrate_thresholds,
    score_window,
    explain_window,
    FEATURE_NAMES
)

def evaluate_window_size(df, window_size):
    """Evaluate EER for a given window size."""
    participants = sorted(df['participant'].unique())[:10]
    
    all_gen_scores = []
    all_imp_scores = []
    
    user_models = {}
    user_thresholds = {}
    user_test_windows = {}
    
    for u in participants:
        df_u = df[df['participant'] == u]
        dig_u = pd.concat([extract_digraphs(df_u[df_u['session'] == s]) for s in df_u['session'].unique()], ignore_index=True)
        win_u = compute_windows(dig_u, window_size=window_size)
        
        if len(win_u) < 10:
            continue
            
        s_idx = int(len(win_u) * 0.7)
        enroll = win_u.iloc[:s_idx]
        test = win_u.iloc[s_idx:]
        
        # Split enrollment into training (80%) and calibration (20%)
        enroll_s_idx = int(len(enroll) * 0.8)
        train = enroll.iloc[:enroll_s_idx]
        calibrate = enroll.iloc[enroll_s_idx:]
        
        if len(train) < 2 or len(calibrate) < 1:
            continue
        
        model = train_user_model(train)
        low_c, high_c = calibrate_thresholds(model, calibrate)
        
        user_models[u] = model
        user_thresholds[u] = (low_c, high_c)
        user_test_windows[u] = test
    
    # Calculate genuine and impostor scores
    for u_model in user_models.keys():
        model = user_models[u_model]
        test_win = user_test_windows[u_model]
        if len(test_win) > 0:
            gen_scores = model.score_samples(test_win[FEATURE_NAMES].values)
            all_gen_scores.extend(gen_scores)
            
        for u_imp in user_models.keys():
            if u_imp == u_model:
                continue
            imp_win = user_test_windows[u_imp]
            if len(imp_win) > 0:
                imp_scores = model.score_samples(imp_win[FEATURE_NAMES].values)
                all_imp_scores.extend(imp_scores)
    
    if len(all_gen_scores) == 0 or len(all_imp_scores) == 0:
        return 1.0  # worst case
    
    all_gen_scores = np.array(all_gen_scores)
    all_imp_scores = np.array(all_imp_scores)
    
    # Compute EER
    thresholds = np.linspace(
        min(all_gen_scores.min(), all_imp_scores.min()), 
        max(all_gen_scores.max(), all_imp_scores.max()), 
        200
    )
    
    far_list = []
    frr_list = []
    
    for th in thresholds:
        far = np.sum(all_imp_scores < th) / len(all_imp_scores)
        frr = np.sum(all_gen_scores >= th) / len(all_gen_scores)
        
        far_list.append(far)
        frr_list.append(frr)
        
    far_list = np.array(far_list)
    frr_list = np.array(frr_list)
    
    diff = np.abs(far_list - frr_list)
    eer_idx = np.argmin(diff)
    eer = (far_list[eer_idx] + frr_list[eer_idx]) / 2.0
    
    return eer

RECONSTRUCTED_CSV = PROJECT_ROOT / "data" / "reconstructed_events.csv"
REPORT_PATH = SCRIPT_DIR / "validation_report.txt"

def run_validation():
    print("Loading reconstructed events...")
    if not os.path.exists(RECONSTRUCTED_CSV):
        print(f"Error: Reconstructed events not found at {RECONSTRUCTED_CSV}")
        print("Please run parse_dataset.py first.")
        sys.exit(1)
        
    df = pd.read_csv(RECONSTRUCTED_CSV)
    print(f"Loaded {len(df)} reconstructed key events.")
    
    # WINDOW SIZE COMPARISON: Test window_size=30 vs window_size=50
    print("\n=== Window Size Comparison ===")
    window_sizes_to_test = [30, 50]
    window_size_results = {}
    
    for ws in window_sizes_to_test:
        print(f"\nTesting window_size={ws}...")
        eer = evaluate_window_size(df, ws)
        window_size_results[ws] = eer
        print(f"window_size={ws}: EER = {eer*100:.2f}%")
    
    # Select best window size
    best_ws = min(window_size_results, key=window_size_results.get)
    WINDOW_SIZE = best_ws
    print(f"\n*** Best window_size: {best_ws} with EER={window_size_results[best_ws]*100:.2f}% ***")
    
    # Continue with full validation using best window size
    print(f"\nProceeding with full validation using window_size={WINDOW_SIZE}...")
    
    # 1. Select User 1 (p001) and User 2 (p002) for the Splice Takeover simulation
    user1 = "p001"
    user2 = "p002"
    
    print(f"Extracting digraphs for {user1}...")
    df_u1 = df[df['participant'] == user1]
    digraphs_u1 = pd.concat([extract_digraphs(df_u1[df_u1['session'] == s]) for s in df_u1['session'].unique()], ignore_index=True)
    
    print(f"Extracting digraphs for {user2}...")
    df_u2 = df[df['participant'] == user2]
    digraphs_u2 = pd.concat([extract_digraphs(df_u2[df_u2['session'] == s]) for s in df_u2['session'].unique()], ignore_index=True)
    
    print(f"Windowing digraph streams (size={WINDOW_SIZE})...")
    windows_u1 = compute_windows(digraphs_u1, window_size=WINDOW_SIZE)
    windows_u2 = compute_windows(digraphs_u2, window_size=WINDOW_SIZE)
    
    print(f"User {user1}: {len(windows_u1)} windows. User {user2}: {len(windows_u2)} windows.")
    
    if len(windows_u1) < 10 or len(windows_u2) < 10:
        print("Error: Too few windows for validation. Make sure free-text.csv was parsed correctly.")
        sys.exit(1)
        
    # 2. Train model on first 70% of user1's windows (enrollment)
    split_idx = int(len(windows_u1) * 0.7)
    enroll_u1 = windows_u1.iloc[:split_idx]
    test_u1 = windows_u1.iloc[split_idx:]
    
    # Split enrollment into training (80%) and calibration (20%) subsets
    enroll_split_idx = int(len(enroll_u1) * 0.8)
    train_u1 = enroll_u1.iloc[:enroll_split_idx]
    calibrate_u1 = enroll_u1.iloc[enroll_split_idx:]
    
    print(f"Training Isolation Forest model for {user1} on {len(train_u1)} training windows (80% of enrollment)...")
    model_u1 = train_user_model(train_u1)
    
    print(f"Calibrating risk thresholds on separate {len(calibrate_u1)} calibration windows (20% of enrollment)...")
    low_cut, high_cut = calibrate_thresholds(model_u1, calibrate_u1)
    print(f"Thresholds calibrated: Low/Med threshold (90th pct) = {low_cut:.4f}, Med/High threshold (99th pct) = {high_cut:.4f}")
        
    # 3. Simulate session takeover
    n_gen = min(5, len(test_u1))
    n_att = min(10, len(windows_u2))
    
    spliced_windows = pd.concat([test_u1.iloc[:n_gen], windows_u2.iloc[:n_att]], ignore_index=True)
    
    print(f"\n--- Takeover Simulation Test ---")
    print(f"Splicing {n_gen} genuine windows from {user1} and {n_att} attacker windows from {user2}...")
    
    consecutive_risk_count = 0
    flagged_idx = -1
    
    simulation_results = []
    
    for idx, row in spliced_windows.iterrows():
        source = "Genuine" if idx < n_gen else "Attacker"
        score, risk = score_window(model_u1, row, low_cut, high_cut)
        
        if risk in ['medium', 'high']:
            consecutive_risk_count += 1
        else:
            consecutive_risk_count = 0
            
        flagged = "SAFE"
        if consecutive_risk_count >= 3:
            flagged = "FLAGGED / HIJACKED"
            if flagged_idx == -1:
                flagged_idx = idx
                
        explanation_str = ""
        if risk in ['medium', 'high']:
            exp = explain_window(model_u1, row)
            sorted_exp = sorted(exp.items(), key=lambda item: abs(item[1]), reverse=True)
            explanation_str = f" [Driver: {sorted_exp[0][0]}={sorted_exp[0][1]:.3f}]"
            
        print(f"Window {idx:02d} ({source}): Score={score:.4f}, Risk={risk.upper():<6} Status={flagged}{explanation_str}")
        simulation_results.append({
            'index': idx,
            'source': source,
            'score': score,
            'risk': risk,
            'flagged': flagged == "FLAGGED / HIJACKED",
            'driver': sorted_exp[0][0] if risk in ['medium', 'high'] else "None"
        })
        
    print("\n--- Simulation Summary ---")
    if flagged_idx != -1:
        print(f"Takeover detection triggered at window index {flagged_idx}.")
        if flagged_idx >= n_gen:
            lag = flagged_idx - n_gen
            print(f"SUCCESS: Spliced attacker detected with a lag of {lag} windows (Required: within a few windows).")
        else:
            print("WARNING: Flagged BEFORE the splice point (False Alarm).")
    else:
        print("FAILED: Attack went undetected!")
        
    # 4. Biometric performance evaluation (EER, FAR, FRR at window level)
    # COMPARE MODELS: IsolationForest vs OneClassSVM
    print("\nEvaluating general performance metrics (FAR/FRR/EER) across 10 users...")
    print("Comparing IsolationForest vs OneClassSVM...")
    
    from sklearn.svm import OneClassSVM
    
    participants = sorted(df['participant'].unique())[:10]
    
    all_gen_scores = []
    all_imp_scores = []
    
    all_gen_scores_svm = []
    all_imp_scores_svm = []
    
    user_models = {}
    user_models_svm = {}
    user_thresholds = {}
    user_thresholds_svm = {}
    user_test_windows = {}
    
    for u in participants:
        df_u = df[df['participant'] == u]
        dig_u = pd.concat([extract_digraphs(df_u[df_u['session'] == s]) for s in df_u['session'].unique()], ignore_index=True)
        win_u = compute_windows(dig_u, window_size=WINDOW_SIZE)
        
        if len(win_u) < 10:
            continue
            
        s_idx = int(len(win_u) * 0.7)
        enroll = win_u.iloc[:s_idx]
        test = win_u.iloc[s_idx:]
        
        # Split enrollment into training (80%) and calibration (20%)
        enroll_s_idx = int(len(enroll) * 0.8)
        train = enroll.iloc[:enroll_s_idx]
        calibrate = enroll.iloc[enroll_s_idx:]
        
        # Train IsolationForest
        model = train_user_model(train)
        low_c, high_c = calibrate_thresholds(model, calibrate)
        
        user_models[u] = model
        user_thresholds[u] = (low_c, high_c)
        user_test_windows[u] = test
        
        # Train OneClassSVM
        X_train_vals = train[FEATURE_NAMES].values
        X_calibrate_vals = calibrate[FEATURE_NAMES].values
        
        model_svm = OneClassSVM(kernel='rbf', gamma='auto', nu=0.05)
        model_svm.fit(X_train_vals)
        
        # Calibrate SVM thresholds
        raw_scores_svm = model_svm.decision_function(X_calibrate_vals)
        anomaly_scores_svm = -raw_scores_svm
        low_c_svm = np.percentile(anomaly_scores_svm, 90)
        high_c_svm = np.percentile(anomaly_scores_svm, 99)
        
        user_models_svm[u] = model_svm
        user_thresholds_svm[u] = (low_c_svm, high_c_svm)
        
    # Calculate genuine and impostor scores for both models
    for u_model in user_models.keys():
        # IsolationForest
        model = user_models[u_model]
        test_win = user_test_windows[u_model]
        if len(test_win) > 0:
            gen_scores = model.score_samples(test_win[FEATURE_NAMES].values)
            all_gen_scores.extend(gen_scores)
            
        for u_imp in user_models.keys():
            if u_imp == u_model:
                continue
            imp_win = user_test_windows[u_imp]
            if len(imp_win) > 0:
                imp_scores = model.score_samples(imp_win[FEATURE_NAMES].values)
                all_imp_scores.extend(imp_scores)
        
        # OneClassSVM
        model_svm = user_models_svm[u_model]
        if len(test_win) > 0:
            gen_scores_svm = -model_svm.decision_function(test_win[FEATURE_NAMES].values)
            all_gen_scores_svm.extend(gen_scores_svm)
            
        for u_imp in user_models_svm.keys():
            if u_imp == u_model:
                continue
            imp_win = user_test_windows[u_imp]
            if len(imp_win) > 0:
                imp_scores_svm = -model_svm.decision_function(imp_win[FEATURE_NAMES].values)
                all_imp_scores_svm.extend(imp_scores_svm)
                
    all_gen_scores = np.array(all_gen_scores)
    all_imp_scores = np.array(all_imp_scores)
    all_gen_scores_svm = np.array(all_gen_scores_svm)
    all_imp_scores_svm = np.array(all_imp_scores_svm)
    
    print(f"Total genuine test windows: {len(all_gen_scores)}")
    print(f"Total impostor test windows: {len(all_imp_scores)}")
    
    # Compute FAR, FRR at different thresholds to find EER for IsolationForest
    thresholds = np.linspace(
        min(all_gen_scores.min(), all_imp_scores.min()), 
        max(all_gen_scores.max(), all_imp_scores.max()), 
        200
    )
    
    far_list = []
    frr_list = []
    
    for th in thresholds:
        far = np.sum(all_imp_scores < th) / len(all_imp_scores)
        frr = np.sum(all_gen_scores >= th) / len(all_gen_scores)
        
        far_list.append(far)
        frr_list.append(frr)
        
    far_list = np.array(far_list)
    frr_list = np.array(frr_list)
    
    diff = np.abs(far_list - frr_list)
    eer_idx = np.argmin(diff)
    eer = (far_list[eer_idx] + frr_list[eer_idx]) / 2.0
    eer_threshold = thresholds[eer_idx]
    
    # Compute EER for OneClassSVM
    thresholds_svm = np.linspace(
        min(all_gen_scores_svm.min(), all_imp_scores_svm.min()), 
        max(all_gen_scores_svm.max(), all_imp_scores_svm.max()), 
        200
    )
    
    far_list_svm = []
    frr_list_svm = []
    
    for th in thresholds_svm:
        far_svm = np.sum(all_imp_scores_svm < th) / len(all_imp_scores_svm)
        frr_svm = np.sum(all_gen_scores_svm >= th) / len(all_gen_scores_svm)
        
        far_list_svm.append(far_svm)
        frr_list_svm.append(frr_svm)
        
    far_list_svm = np.array(far_list_svm)
    frr_list_svm = np.array(frr_list_svm)
    
    diff_svm = np.abs(far_list_svm - frr_list_svm)
    eer_idx_svm = np.argmin(diff_svm)
    eer_svm = (far_list_svm[eer_idx_svm] + frr_list_svm[eer_idx_svm]) / 2.0
    eer_threshold_svm = thresholds_svm[eer_idx_svm]
    
    avg_low_cut = np.mean([user_thresholds[u][0] for u in user_thresholds])
    avg_high_cut = np.mean([user_thresholds[u][1] for u in user_thresholds])
    
    far_at_low = np.sum(all_imp_scores < avg_low_cut) / len(all_imp_scores)
    frr_at_low = np.sum(all_gen_scores >= avg_low_cut) / len(all_gen_scores)
    
    far_at_high = np.sum(all_imp_scores < avg_high_cut) / len(all_imp_scores)
    frr_at_high = np.sum(all_gen_scores >= avg_high_cut) / len(all_gen_scores)
    
    print(f"\n--- Population Metrics ---")
    print(f"IsolationForest - Equal Error Rate (EER): {eer * 100:.2f}% at threshold = {eer_threshold:.4f}")
    print(f"OneClassSVM - Equal Error Rate (EER): {eer_svm * 100:.2f}% at threshold = {eer_threshold_svm:.4f}")
    print(f"\nBest model: {'IsolationForest' if eer < eer_svm else 'OneClassSVM'} (lower EER is better)")
    print(f"At Calibrated Low Threshold (avg={avg_low_cut:.4f}): FAR={far_at_low*100:.2f}%, FRR={frr_at_low*100:.2f}% (Risk: Medium)")
    print(f"At Calibrated High Threshold (avg={avg_high_cut:.4f}): FAR={far_at_high*100:.2f}%, FRR={frr_at_high*100:.2f}% (Risk: High)")
    
    # 5. Generate visualization figures
    print("\nGenerating validation figures...")
    import matplotlib
    matplotlib.use('Agg')  # Non-interactive backend
    import matplotlib.pyplot as plt
    
    # Create docs/figures directory
    figures_dir = os.path.join(os.path.dirname(__file__), "..", "docs", "figures")
    os.makedirs(figures_dir, exist_ok=True)
    
    # Figure 1: ROC Curve
    fig1, ax1 = plt.subplots(figsize=(8, 6))
    ax1.plot(far_list, 1 - frr_list, 'b-', linewidth=2, label=f'ROC Curve (EER={eer*100:.2f}%)')
    ax1.plot([0, 1], [0, 1], 'r--', linewidth=1, label='Random Classifier')
    ax1.scatter([far_list[eer_idx]], [1 - frr_list[eer_idx]], color='red', s=100, zorder=5, label=f'EER Point')
    ax1.set_xlabel('False Accept Rate (FAR)', fontsize=12)
    ax1.set_ylabel('True Accept Rate (1 - FRR)', fontsize=12)
    ax1.set_title('ROC Curve - Continuous Keystroke Authentication', fontsize=14, fontweight='bold')
    ax1.legend(loc='lower right')
    ax1.grid(True, alpha=0.3)
    roc_path = os.path.join(figures_dir, "roc_curve.png")
    fig1.savefig(roc_path, dpi=150, bbox_inches='tight')
    print(f"Saved ROC curve to {roc_path}")
    plt.close(fig1)
    
    # Figure 2: Anomaly Score Chart for Takeover Simulation
    fig2, ax2 = plt.subplots(figsize=(10, 6))
    window_indices = [res['index'] for res in simulation_results]
    scores = [res['score'] for res in simulation_results]
    colors = ['green' if res['source'] == 'Genuine' else 'red' for res in simulation_results]
    
    ax2.plot(window_indices, scores, 'o-', linewidth=2, markersize=8, color='blue', alpha=0.7)
    for i, (idx, score, color) in enumerate(zip(window_indices, scores, colors)):
        ax2.scatter([idx], [score], color=color, s=100, zorder=5, edgecolors='black', linewidths=1.5)
    
    # Mark splice point and detection point
    ax2.axvline(x=n_gen - 0.5, color='orange', linestyle='--', linewidth=2, label='Splice Point (Attack Begins)')
    if flagged_idx != -1:
        ax2.axvline(x=flagged_idx, color='purple', linestyle='--', linewidth=2, label=f'Detection Point (Window {flagged_idx})')
    
    # Mark thresholds
    ax2.axhline(y=low_cut, color='yellow', linestyle=':', linewidth=1.5, label=f'Low Threshold ({low_cut:.3f})', alpha=0.7)
    ax2.axhline(y=high_cut, color='red', linestyle=':', linewidth=1.5, label=f'High Threshold ({high_cut:.3f})', alpha=0.7)
    
    ax2.set_xlabel('Window Index', fontsize=12)
    ax2.set_ylabel('Anomaly Score', fontsize=12)
    ax2.set_title('Session Takeover Detection - Anomaly Score Timeline', fontsize=14, fontweight='bold')
    ax2.legend(loc='upper left', fontsize=9)
    ax2.grid(True, alpha=0.3)
    takeover_path = os.path.join(figures_dir, "takeover_detection.png")
    fig2.savefig(takeover_path, dpi=150, bbox_inches='tight')
    print(f"Saved takeover detection chart to {takeover_path}")
    plt.close(fig2)
    
    # Write report
    with open(REPORT_PATH, 'w') as f:
        f.write("CONTINUOUS KEYSTROKE AUTHENTICATION - ML VALIDATION REPORT\n")
        f.write("==========================================================\n\n")
        f.write(f"Dataset used: KeyRecs free-text subset\n")
        f.write(f"Total events loaded: {len(df)}\n\n")
        f.write(f"--- Window Size Comparison ---\n")
        for ws, ws_eer in window_size_results.items():
            f.write(f"window_size={ws}: EER = {ws_eer*100:.2f}%\n")
        f.write(f"Selected window size: {WINDOW_SIZE} (best EER)\n\n")
        f.write(f"--- Takeover Simulation (User p001 model vs User p002 attacker) ---\n")
        f.write(f"Spliced windows: {n_gen} genuine, {n_att} attacker\n")
        for res in simulation_results:
            f.write(f"Window {res['index']:02d} ({res['source']}): score={res['score']:.4f}, risk={res['risk'].upper():<6}, hijacked={res['flagged']}, primary_driver={res['driver']}\n")
        f.write(f"\nTakeover detection status: ")
        if flagged_idx != -1:
            f.write(f"SUCCESS (Triggered at window {flagged_idx}, lag={flagged_idx - n_gen} windows)\n")
        else:
            f.write("FAILED (No trigger)\n")
            
        f.write(f"\n--- Cross-User Population Metrics (10 Users) ---\n")
        f.write(f"Total genuine test windows evaluated: {len(all_gen_scores)}\n")
        f.write(f"Total impostor test windows evaluated: {len(all_imp_scores)}\n\n")
        f.write(f"Model Comparison:\n")
        f.write(f"IsolationForest - Equal Error Rate (EER): {eer * 100:.2f}% at threshold = {eer_threshold:.4f}\n")
        f.write(f"OneClassSVM - Equal Error Rate (EER): {eer_svm * 100:.2f}% at threshold = {eer_threshold_svm:.4f}\n")
        f.write(f"Best model: {'IsolationForest' if eer < eer_svm else 'OneClassSVM'} (lower EER is better)\n\n")
        f.write(f"IsolationForest Performance at Calibrated Thresholds:\n")
        f.write(f"FAR/FRR at low_cut threshold ({avg_low_cut:.4f}): FAR={far_at_low*100:.2f}%, FRR={frr_at_low*100:.2f}%\n")
        f.write(f"FAR/FRR at high_cut threshold ({avg_high_cut:.4f}): FAR={far_at_high*100:.2f}%, FRR={frr_at_high*100:.2f}%\n")
        
    print(f"\nValidation report saved to {REPORT_PATH}")

if __name__ == "__main__":
    run_validation()
