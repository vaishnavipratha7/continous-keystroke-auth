# Continuous Keystroke Authentication

Real-time session hijacking detection using typing rhythm and unsupervised machine learning.

## Overview

This system extends keystroke authentication from one-time login verification to continuous in-session monitoring. Each user gets their own Isolation Forest model trained only on their typing patterns - no labeled attacker data required.

## Features

- **Per-user unsupervised models** - Isolation Forest trained on individual typing patterns
- **Real-time monitoring** - 50-keystroke windows scored continuously during session
- **Adaptive learning** - Model updates with safe session data
- **MFA challenge** - PIN verification before lockout on sustained anomalies
- **SHAP explanations** - Understand which features triggered each alert

## Results

Validated on KeyRecs dataset (562K+ keystroke events, 100 participants):

- **EER:** 24.43%
- **Detection lag:** ~100 keystrokes after takeover
- **Window size:** 50 digraphs (optimal)

## Tech Stack

**Backend:** FastAPI, MongoDB, scikit-learn (Isolation Forest), SHAP  
**Frontend:** React, Recharts  
**Auth:** bcrypt + JWT sessions

## Setup

**Prerequisites:** Python 3.10+, Node 18+, MongoDB

```bash
# Clone and setup
git clone https://github.com/vaishnavipratha7/continous-keystroke-auth
cd continous-keystroke-auth

# Get dataset
python scripts/download_data.py
python scripts/parse_dataset.py

# Backend
cd backend
pip install -r requirements.txt
cp .env.example .env
uvicorn main:app --reload

# Frontend (new terminal)
cd frontend
npm install
cp .env.example .env
npm run dev
```

Open http://localhost:5173

## Testing

```bash
# Unit tests
cd backend && pytest tests/ -v

# End-to-end test
python scripts/test_e2e.py

# Validation (regenerate metrics)
python scripts/run_validation.py
```

## How It Works

1. **Enrollment** - User types passage, system extracts digraph features (dwell time, flight time, typing speed)
2. **Training** - Isolation Forest learns user's baseline from 80% of enrollment data
3. **Monitoring** - Live typing scored in 50-keystroke windows against baseline
4. **Detection** - 3 consecutive medium/high-risk windows trigger lockout
5. **Adaptation** - Safe sessions retrain model to handle natural drift

## Security

- PIN storage: bcrypt hashed
- Rate limiting: 5 verification attempts max
- Session timeout: 30 minutes inactivity
- Server-side validation only
