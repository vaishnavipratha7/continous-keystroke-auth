# Continuous Keystroke Authentication

Real-time session hijacking detection using keystroke dynamics and machine learning.

![Demo](docs/demo.gif)

## What It Does

Monitors your typing pattern in real-time to detect when someone else takes over your keyboard. If an attacker physically accesses your session, the system locks them out within ~100-150 keystrokes.

## Key Features

- **Real-Time Monitoring**: Analyzes typing every 50 keystrokes
- **Fast Detection**: Identifies attackers in 2-3 windows (~2 seconds)
- **Explainable**: Shows why each decision was made (SHAP values)
- **Adaptive**: Learns from your legitimate typing sessions
- **Full Stack**: React frontend + FastAPI backend + MongoDB

## Tech Stack

- **ML**: IsolationForest (unsupervised anomaly detection)
- **Frontend**: React 18 + Vite + Recharts
- **Backend**: FastAPI + SHAP + scikit-learn
- **Database**: MongoDB
- **Deployment**: Docker + Docker Compose

## Quick Start

**Prerequisites**: Python 3.11+, Node 20+, MongoDB

```bash
# 1. Start MongoDB
docker run -d -p 27017:27017 mongo:7.0

# 2. Backend
pip install -r backend/requirements.txt
uvicorn backend.main:app --reload

# 3. Frontend (new terminal)
cd frontend && npm install && npm run dev
```

**Open**: http://localhost:5173

**Try it**: Sign up → Enroll (type passage 2-3 times) → Session → Click "Demo: Synthetic Attack"

## Performance

- **Equal Error Rate**: 24.43% (measured on KeyRecs dataset)
- **Detection Latency**: 2 windows (~100 keystrokes)
- **Dataset**: 562K+ keystroke events from 100+ users

<div align="center">
  <img src="docs/figures/roc_curve.png" width="45%"/>
  <img src="docs/figures/takeover_detection.png" width="45%"/>
</div>

## How It Works

1. **Enrollment**: User types passage → Extract timing features (dwell time, flight time, typing speed)
2. **Training**: IsolationForest learns normal pattern → Calibrate risk thresholds
3. **Monitoring**: Live typing → Score each 50-keystroke window → Flag after 3 consecutive high-risk windows

## Project Structure

```
continuous-keystroke-auth/
├── backend/
│   ├── main.py          # FastAPI endpoints
│   ├── pipeline.py      # ML pipeline
│   ├── auth.py          # JWT authentication
│   └── db.py            # MongoDB interface
├── frontend/src/
│   └── App.jsx          # React dashboard
├── scripts/
│   └── run_validation.py # Performance evaluation
└── docker-compose.yml    # Container orchestration
```

## Research Context

This extends work on keystroke dynamics authentication ([Martins et al., 2025](https://doi.org/10.1007/s42452-025-07449-5)) by implementing continuous (not just initial) authentication with real-time monitoring and adaptive learning. Dataset: [KeyRecs](https://doi.org/10.1007/s00521-022-07472-0) (CC BY 4.0).

## License

MIT License - see [LICENSE](LICENSE) file

## Author

**Your Name** | [GitHub](https://github.com/yourusername) | [LinkedIn](https://linkedin.com/in/yourprofile)
