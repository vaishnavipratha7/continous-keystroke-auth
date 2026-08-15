# Continuous Keystroke Authentication System

> Real-time session hijacking detection using keystroke dynamics and machine learning

[![Python](https://img.shields.io/badge/Python-3.11-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104-009688.svg)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18-61DAFB.svg)](https://reactjs.org/)
[![MongoDB](https://img.shields.io/badge/MongoDB-7.0-47A248.svg)](https://www.mongodb.com/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

## 🎯 Problem Statement

Traditional authentication systems only verify identity at login. Once authenticated, if an attacker physically takes over a user's session, the system cannot detect the switch. This project implements **continuous authentication** that monitors typing patterns throughout the session to detect when a different person takes control.

## 🎬 Demo

![Demo Animation](docs/demo.gif)

**Live Demo**: [https://keystroke-auth-demo.vercel.app](https://keystroke-auth-demo.vercel.app) *(if deployed)*

## ✨ Key Features

- **Real-Time Monitoring**: Analyzes typing dynamics every ~50 keystrokes
- **Fast Detection**: Identifies attackers within 2-3 typing windows (100-150 keys)
- **Explainable AI**: SHAP values show *why* each decision was made
- **Adaptive Learning**: Model improves from confirmed legitimate sessions
- **Zero User Friction**: Invisible monitoring during normal typing
- **Interactive Dashboard**: Live risk visualization with technical metrics

## 📊 Performance Metrics

| Metric | Value | Description |
|--------|-------|-------------|
| **Equal Error Rate (EER)** | 24.43% | Balance point between false accepts and false rejects |
| **Detection Latency** | 2 windows | Average lag after attack begins (~100 keystrokes) |
| **False Accept Rate (FAR)** | 29.30% | Impostor typed accepted as genuine at low threshold |
| **False Reject Rate (FRR)** | 20.62% | Genuine user rejected at low threshold |
| **Dataset** | KeyRecs | 562K+ keystroke events from 100+ users |

### Validation Results

<div align="center">
  <img src="docs/figures/roc_curve.png" width="45%" alt="ROC Curve"/>
  <img src="docs/figures/takeover_detection.png" width="45%" alt="Takeover Detection"/>
</div>

**Left**: ROC curve showing tradeoff between FAR and FRR across thresholds  
**Right**: Real-time anomaly scores during simulated session takeover (orange=attack begins, purple=system locks session)

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     FRONTEND (React + Vite)                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │   Landing    │  │  Enrollment  │  │   Dashboard  │         │
│  │   + Signup   │  │   (Capture   │  │  (Real-time  │         │
│  │              │  │   baseline)  │  │   monitor)   │         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │   History    │  │ SHAP Explain │  │   Results    │         │
│  │   (Past      │  │  (Feature    │  │ (Validation) │         │
│  │   sessions)  │  │  importance) │  │              │         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
└────────────────────────┬────────────────────────────────────────┘
                         │ REST API (HTTP/JSON)
┌────────────────────────▼────────────────────────────────────────┐
│                    BACKEND (FastAPI)                            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │ Auth Service │  │ ML Pipeline  │  │  Database    │         │
│  │ - JWT tokens │  │ - Feature    │  │  - Users     │         │
│  │ - Sessions   │  │   extraction │  │  - Models    │         │
│  │ - Bcrypt     │  │ - Isolation  │  │  - Sessions  │         │
│  │              │  │   Forest     │  │  - Events    │         │
│  │              │  │ - SHAP       │  │              │         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
└────────────────────────┬────────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────────┐
│                   DATA LAYER (MongoDB)                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │ keystroke_   │  │ user_models  │  │ session_     │         │
│  │ events       │  │ (pickled ML) │  │ scores       │         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
└─────────────────────────────────────────────────────────────────┘
```

## 🚀 Quick Start

### Prerequisites

- **Python 3.11+** with pip
- **Node.js 20+** with npm
- **MongoDB 7.0+** (local or Docker)

### 1. Clone Repository

```bash
git clone https://github.com/yourusername/continuous-keystroke-auth.git
cd continuous-keystroke-auth
```

### 2. Start MongoDB

**Using Docker** (recommended):
```bash
docker run -d -p 27017:27017 --name keystroke-mongo mongo:7.0
```

**Or use local MongoDB installation**

### 3. Backend Setup

```bash
# Install dependencies
pip install -r backend/requirements.txt

# Start backend server
uvicorn backend.main:app --reload
```

Backend runs at **http://127.0.0.1:8000**

### 4. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

Frontend runs at **http://localhost:5173**

### 5. Try It Out

1. **Sign Up** → Create account (username + password ≥8 chars)
2. **Enroll** → Type the passage 2-3 times (need 350+ keystrokes)
3. **Session** → Type freely; system monitors in real-time
4. **Demo Attack** → Click "Demo: Synthetic Attack" button to simulate hijacking
5. **Explainability** → Click any flagged window to see SHAP explanation

## 🧪 Optional: Run Validation

```bash
# Download and parse KeyRecs dataset
python scripts/download_data.py
python scripts/parse_dataset.py

# Run validation (generates figures and metrics)
python scripts/run_validation.py

# Run unit tests
pip install pytest
pytest backend/tests/ -v
```

## 🐳 Docker Deployment

```bash
# Build and start all services (MongoDB + Backend + Frontend)
docker-compose up --build

# Access at http://localhost
```

## 🔬 Technical Details

### Feature Engineering

The system extracts 5 features per 50-keystroke window:

| Feature | Description | Example |
|---------|-------------|---------|
| `dwell_mean` | Average key press duration | 0.095s |
| `dwell_std` | Variability in key press duration | 0.023s |
| `flight_mean` | Average time between keys | 0.142s |
| `flight_std` | Variability in inter-key timing | 0.031s |
| `typing_speed` | Keys per second | 6.8 keys/s |

### Machine Learning Pipeline

```python
# 1. Enrollment
events → digraphs → windows (50 each) → features (5-dim vectors)
         ↓
# 2. Training (80/20 split)
train_windows (80%) → IsolationForest(n_estimators=200, contamination=0.05)
calibrate_windows (20%) → thresholds (90th & 99th percentile)

# 3. Session Monitoring
new_window → score → classify (low/medium/high) → flag if 3 consecutive medium/high
```

**Why Isolation Forest?**
- Unsupervised (no labeled attack data needed)
- Fast inference (<5ms per window)
- Robust to outliers
- Naturally assigns anomaly scores

### Risk Classification

```
Anomaly Score < low_cut (90th percentile)  → LOW risk (green)
low_cut ≤ Score < high_cut (99th percentile) → MEDIUM risk (amber)
Score ≥ high_cut                              → HIGH risk (red)

Session FLAGGED after 3 consecutive medium/high windows
```

### Explainability with SHAP

Every flagged window includes SHAP (SHapley Additive exPlanations) values showing feature contributions:

```
Window 7 flagged because:
  typing_speed:  +0.234 (much slower than baseline)
  dwell_mean:    +0.089 (longer key holds)
  flight_std:    -0.023 (less rhythm variation)
```

## 📁 Project Structure

```
continuous-keystroke-auth/
├── backend/
│   ├── main.py              # FastAPI endpoints (auth, enroll, session)
│   ├── pipeline.py          # ML pipeline (features, training, scoring)
│   ├── auth.py              # JWT + bcrypt authentication
│   ├── db.py                # MongoDB connection and queries
│   ├── requirements.txt     # Python dependencies
│   ├── Dockerfile           # Backend container
│   └── tests/
│       └── test_pipeline.py # Unit tests for ML functions
├── frontend/
│   ├── src/
│   │   ├── App.jsx          # React app with all views
│   │   ├── App.css          # Component styles
│   │   └── index.css        # Global styles + design tokens
│   ├── public/
│   │   └── figures/         # Validation result images
│   ├── package.json         # Node dependencies
│   ├── vite.config.js       # Vite build configuration
│   └── Dockerfile           # Frontend container (nginx)
├── scripts/
│   ├── download_data.py     # Fetch KeyRecs dataset
│   ├── parse_dataset.py     # Reconstruct keystroke events
│   ├── run_validation.py    # Cross-validation + metrics
│   └── validation_report.txt # Generated metrics report
├── data/
│   ├── free-text.csv        # Raw KeyRecs data (gitignored)
│   └── reconstructed_events.csv # Processed events (gitignored)
├── docs/
│   └── figures/
│       ├── roc_curve.png    # Performance visualization
│       └── takeover_detection.png # Attack detection timeline
├── docker-compose.yml       # Multi-container orchestration
├── .github/
│   └── workflows/
│       └── tests.yml        # CI/CD pipeline
└── README.md                # This file
```

## 🔬 Research Context

This system extends the work of **Martins et al. (2025)** on keystroke dynamics authentication by addressing key gaps:

| Aspect | Martins et al. (2025) | This System |
|--------|----------------------|-------------|
| **Scope** | Initial authentication | Continuous session monitoring |
| **Detection** | Static (login only) | Real-time (every 50 keystrokes) |
| **Adaptation** | Fixed model | Adaptive learning from safe sessions |
| **Explainability** | None | SHAP values for each decision |
| **User Interface** | N/A | Live dashboard with risk visualization |
| **Dataset** | KeyRecs | KeyRecs (same, for comparability) |

### Dataset Citation

This project uses the **KeyRecs free-text dataset**:

> Bours, P., Mondal, S. *A dataset for exploring user authentication through free-text keystroke dynamics*. Neural Comput & Applic 35, 16077–16093 (2023). https://doi.org/10.1007/s00521-022-07472-0

**License**: CC BY 4.0

### Base Research Citation

Inspired by:

> Martins, J.P., Soares, S.C., Pinho, A.J. et al. *Keystroke dynamics for intelligent biometric authentication with machine learning*. Discov Appl Sci 7, 34 (2025). https://doi.org/10.1007/s42452-025-07449-5

## 🛣️ Future Enhancements

- [ ] **Deep Learning Models**: LSTM/Transformer for temporal patterns (target: <15% EER)
- [ ] **Multi-Factor Fallback**: Trigger 2FA on medium risk instead of immediate lockout
- [ ] **Context Awareness**: Adjust thresholds for fatigue, different keyboards, etc.
- [ ] **Mobile Support**: Touchscreen typing dynamics (tap pressure, finger size)
- [ ] **Multi-Modal**: Combine with mouse dynamics for stronger authentication
- [ ] **Privacy**: Federated learning to train without sharing raw keystroke data
- [ ] **Performance**: Redis caching for model loading, async background training

## 🤝 Contributing

Contributions welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see [LICENSE](LICENSE) file for details.

The KeyRecs dataset is licensed under CC BY 4.0.

## 👤 Author

**Your Name**
- GitHub: [@yourusername](https://github.com/yourusername)
- LinkedIn: [Your Name](https://linkedin.com/in/yourprofile)
- Email: your.email@example.com

## 🙏 Acknowledgments

- Martins et al. for keystroke dynamics research foundation
- Bours & Mondal for the KeyRecs dataset
- scikit-learn and SHAP libraries for ML infrastructure
- FastAPI and React communities for excellent tooling

---

**⭐ Star this repo if you find it useful!**
