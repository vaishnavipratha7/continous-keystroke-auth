import pytest
import numpy as np
import pandas as pd
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from backend.pipeline import (
    extract_digraphs,
    compute_windows,
    score_window,
    calibrate_thresholds,
    train_user_model,
    FEATURE_NAMES
)


def test_extract_digraphs_basic():
    """Test basic digraph extraction from simple events."""
    events = pd.DataFrame([
        {"key": "a", "down_time": 0.0, "up_time": 0.1},
        {"key": "b", "down_time": 0.15, "up_time": 0.25},
        {"key": "c", "down_time": 0.3, "up_time": 0.4}
    ])
    
    digraphs = extract_digraphs(events)
    
    assert len(digraphs) == 2, "Should produce 2 digraphs from 3 events"
    assert digraphs.iloc[0]['key1'] == 'a'
    assert digraphs.iloc[0]['key2'] == 'b'
    assert np.isclose(digraphs.iloc[0]['dwell'], 0.1, atol=0.01)
    assert np.isclose(digraphs.iloc[0]['flight'], 0.05, atol=0.01)


def test_extract_digraphs_outlier_filtering():
    """Test that outlier digraphs are filtered out."""
    events = pd.DataFrame([
        {"key": "a", "down_time": 0.0, "up_time": 0.1},
        {"key": "b", "down_time": 10.0, "up_time": 10.1},  # 9.9s flight (outlier)
        {"key": "c", "down_time": 10.2, "up_time": 10.3}
    ])
    
    digraphs = extract_digraphs(events)
    
    # First digraph should be filtered due to extreme flight time
    assert len(digraphs) == 1, "Outlier digraph should be filtered"
    assert digraphs.iloc[0]['key1'] == 'b'
    assert digraphs.iloc[0]['key2'] == 'c'


def test_extract_digraphs_empty():
    """Test handling of empty or single-event input."""
    events = pd.DataFrame([{"key": "a", "down_time": 0.0, "up_time": 0.1}])
    digraphs = extract_digraphs(events)
    assert len(digraphs) == 0, "Single event should produce no digraphs"


def test_compute_windows_basic():
    """Test windowing with synthetic uniform digraphs."""
    # Create 60 uniform digraphs
    digraphs = pd.DataFrame([
        {
            "key1": f"k{i}",
            "key2": f"k{i+1}",
            "dwell": 0.1,
            "flight": 0.05,
            "down_time1": i * 0.15,
            "up_time2": (i * 0.15) + 0.15
        }
        for i in range(60)
    ])
    
    windows = compute_windows(digraphs, window_size=50)
    
    assert len(windows) == 1, "60 digraphs should produce 1 window of size 50"
    assert all(col in windows.columns for col in FEATURE_NAMES)
    
    # Check feature values are reasonable
    row = windows.iloc[0]
    assert np.isclose(row['dwell_mean'], 0.1, atol=0.01)
    assert np.isclose(row['flight_mean'], 0.05, atol=0.01)
    assert row['typing_speed'] > 0


def test_compute_windows_insufficient():
    """Test that insufficient digraphs produce no windows."""
    digraphs = pd.DataFrame([
        {"key1": "a", "key2": "b", "dwell": 0.1, "flight": 0.05, "down_time1": 0.0, "up_time2": 0.15}
        for _ in range(10)
    ])
    
    windows = compute_windows(digraphs, window_size=50)
    assert len(windows) == 0, "Fewer than 50 digraphs should produce no windows"


def test_train_and_score_basic():
    """Test model training and scoring with synthetic data."""
    # Create synthetic training data (20 windows)
    train_data = pd.DataFrame([
        {
            'dwell_mean': 0.1 + np.random.normal(0, 0.01),
            'dwell_std': 0.02,
            'flight_mean': 0.05 + np.random.normal(0, 0.005),
            'flight_std': 0.01,
            'typing_speed': 6.0 + np.random.normal(0, 0.5)
        }
        for _ in range(20)
    ])
    
    model = train_user_model(train_data)
    assert model is not None, "Model should be trained"
    
    # Test scoring
    test_window = train_data.iloc[0]
    low_cut, high_cut = calibrate_thresholds(model, train_data)
    
    assert low_cut < high_cut, "Low threshold should be less than high threshold"
    
    score, risk = score_window(model, test_window, low_cut, high_cut)
    
    assert isinstance(score, (float, np.floating)), "Score should be numeric"
    assert risk in ['low', 'medium', 'high'], "Risk should be one of the valid levels"


def test_calibrate_thresholds():
    """Test threshold calibration produces reasonable values."""
    # Synthetic enrollment data
    enroll_data = pd.DataFrame([
        {
            'dwell_mean': 0.1,
            'dwell_std': 0.02,
            'flight_mean': 0.05,
            'flight_std': 0.01,
            'typing_speed': 6.0
        }
        for _ in range(30)
    ])
    
    model = train_user_model(enroll_data)
    low_cut, high_cut = calibrate_thresholds(model, enroll_data)
    
    assert isinstance(low_cut, (float, np.floating))
    assert isinstance(high_cut, (float, np.floating))
    assert low_cut <= high_cut, "Low threshold must not exceed high threshold"


def test_score_window_anomaly_detection():
    """Test that anomalous windows get higher scores."""
    # Normal training data with realistic variance (not identical copies)
    # Real typing has natural variation in timing
    np.random.seed(42)  # For reproducibility
    normal_data = pd.DataFrame([
        {
            'dwell_mean': 0.1 + np.random.normal(0, 0.01),
            'dwell_std': 0.02 + np.random.normal(0, 0.005),
            'flight_mean': 0.05 + np.random.normal(0, 0.005),
            'flight_std': 0.01 + np.random.normal(0, 0.002),
            'typing_speed': 6.0 + np.random.normal(0, 0.5)
        }
        for _ in range(30)
    ])
    
    model = train_user_model(normal_data)
    low_cut, high_cut = calibrate_thresholds(model, normal_data)
    
    # Normal window
    normal_window = normal_data.iloc[0]
    normal_score, normal_risk = score_window(model, normal_window, low_cut, high_cut)
    
    # Anomalous window (very different timing)
    anomalous_window = pd.Series({
        'dwell_mean': 1.5,  # Much longer dwell
        'dwell_std': 0.5,
        'flight_mean': 2.0,  # Much longer flight
        'flight_std': 0.3,
        'typing_speed': 1.0  # Much slower
    })
    
    anomalous_score, anomalous_risk = score_window(model, anomalous_window, low_cut, high_cut)
    
    assert anomalous_score > normal_score, "Anomalous window should have higher score than normal"
    assert anomalous_risk in ['medium', 'high'], "Anomalous window should be flagged as at-risk"
