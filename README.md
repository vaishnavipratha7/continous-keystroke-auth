# Continuous Keystroke Biometric Authentication System

A real-time continuous authentication system that monitors typing dynamics to detect session hijacking attempts. This system extends the work of [Martins et al. (2025)](https://doi.org/10.1007/s42452-025-07449-5) on keystroke dynamics for intelligent biometric authentication, implementing continuous (not just initial) authentication with adaptive learning and session hijacking detection.

## Key Features

- **Continuous Monitoring**: Real-time keystroke analysis during active sessions
- **Session Hijacking Detection**: Identifies attackers within 2-3 typing windows
- **Explainable AI**: SHAP values explain why anomalies are flagged
- **Adaptive Learning**: Model improves from legitimate user sessions
- **Live Dashboard**: Real-time visualization of authentication status

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         FRONTEND (React)                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │  Enrollment  │  │   Dashboard  │  │ SHAP Explain │         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
└────────────────────────┬────────────────────────────────────────┘
                         │ HTTP/JSON
┌────────────────────────▼────────────────────────────────────────┐
│                      BACKEND (FastAPI)                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │     Auth     │  │   Pipeline   │  │   Database   │         │
│  │   (JWT)      │  │ (Isolation   │  │  (MongoDB)   │         │
│  │              │  │   Forest)    │  │              │         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
└─────────────────────────────────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────────┐
│                    DATA PROCESSING                              │
│  KeyRecs Dataset → Digraph Extraction → Windowing → Features   │
└─────────────────────────────────────────────────────────────────┘
```

## Setup Instructions

### Prerequisites

- Python 3.8+
- Node.js 16+
- MongoDB 4.4+

### 1. Clone Repository

```bash
git clone <repository-url>
cd continuous-keystroke-auth
```

### 2. Download Dataset

```bash
python scripts/download_data.py
python scripts/parse_dataset.py
```

This downloads the KeyRecs free-text dataset and reconstructs ~562k keystroke events.

### 3. Backend Setup

```bash
cd backend
pip install -r requirements.txt  # Create this if needed
cp .env.example .env
# Edit .env with your MongoDB URI
```

Start MongoDB:
```bash
mongod --dbpath /path/to/data
```

Start backend server:
```bash
uvicorn backend.main:app --reload
```

### 4. Frontend Setup

```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```

Frontend runs at http://localhost:5173

### 5. Run Validation

```bash
python scripts/run_validation.py
```

This generates validation metrics and figures in `docs/figures/`.

## Running the Demo

1. **Sign Up**: Create a new account
2. **Enrollment**: Type the provided passage 2-3 times (~350+ keystrokes)
3. **Active Session**: Type freely; system monitors in real-time
4. **Test Attack**: Click "Demo: Synthetic Attack" to see detection in action
5. **Explainability**: View SHAP values showing why anomalies were flagged

## Results

### Performance Metrics (10-user validation)

- **Equal Error Rate (EER)**: 24.43%
- **False Accept Rate (FAR)** at low threshold: 29.30%
- **False Rejection Rate (FRR)** at low threshold: 20.62%
- **Detection Latency**: 2-3 windows after attack begins

### Takeover Detection Success

The system successfully detected all simulated session hijacking attempts with an average lag of 2 windows (100 keystrokes).

![ROC Curve](docs/figures/roc_curve.png)

*ROC Curve showing system performance across different thresholds*

![Takeover Detection](docs/figures/takeover_detection.png)

*Real-time anomaly scores during a simulated session takeover. Orange line marks the splice point where the attacker begins typing; purple line shows where the system triggers the lockdown.*

## Technical Details

### Feature Engineering

- **Dwell Time**: Key press duration (down to up)
- **Flight Time**: Inter-key latency (up to next down)
- **Typing Speed**: Keys per second in window
- **Statistical Aggregates**: Mean and std dev per 50-digraph window

### Model

- **Algorithm**: Isolation Forest (unsupervised anomaly detection)
- **Window Size**: 50 digraphs (optimized for EER)
- **Thresholds**: 90th percentile (medium) and 99th percentile (high)
- **Training**: 80% enrollment, 20% calibration split

### Decision Logic

Session flagged as "hijacked" after **3 consecutive medium/high risk windows** to reduce false positives from natural typing variations.

## Gap Filling

This system extends the work of Martins et al. (2025) in keystroke dynamics authentication by addressing several key gaps:

1. **Continuous vs. Initial**: Monitors entire session, not just login authentication
2. **Adaptive Learning**: Model improves from confirmed legitimate sessions
3. **Real-time Detection**: Live monitoring with <5 second latency
4. **Explainability**: SHAP values explain each decision for transparency
5. **User-facing Dashboard**: Transparent risk visualization for end users

### Dataset

This implementation uses the KeyRecs free-text dataset from [Bours & Mondal (2023)](https://link.springer.com/article/10.1007/s00521-022-07472-0) for training and validation.

## Project Structure

```
continuous-keystroke-auth/
├── backend/
│   ├── main.py           # FastAPI endpoints
│   ├── pipeline.py       # ML pipeline
│   ├── auth.py           # Authentication logic
│   └── db.py             # MongoDB interface
├── frontend/
│   └── src/
│       └── App.jsx       # React dashboard
├── scripts/
│   ├── download_data.py  # Dataset downloader
│   ├── parse_dataset.py  # Digraph reconstruction
│   ├── run_validation.py # Performance evaluation
│   └── test_e2e.py       # End-to-end test
├── data/
│   ├── free-text.csv     # Raw KeyRecs data
│   └── reconstructed_events.csv  # Processed events
└── docs/
    └── figures/          # Validation visualizations
```

## Testing

Run end-to-end system test:
```bash
python scripts/test_e2e.py
```

This tests signup → login → enrollment → training → session monitoring → hijack detection → SHAP explanation.

## License

This project uses the KeyRecs dataset from [Bours & Mondal, 2023], licensed under CC BY 4.0.

## Citation

If you use this system, please cite:

**Base Paper**:
```
Martins, J.P., Soares, S.C., Pinho, A.J. et al. Keystroke dynamics for intelligent biometric 
authentication with machine learning. Discov Appl Sci 7, 34 (2025). 
https://doi.org/10.1007/s42452-025-07449-5
```

**Dataset**:
```
Bours, P., Mondal, S. A dataset for exploring user authentication through free-text keystroke dynamics. 
Neural Comput & Applic 35, 16077–16093 (2023). https://doi.org/10.1007/s00521-022-07472-0
```

## Contributing

Pull requests welcome! Areas for improvement:

- Lower EER through deep learning models
- Multi-factor authentication integration
- Mobile device support
- Additional behavioral biometrics (mouse dynamics, etc.)

## Support

For issues or questions, please open a GitHub issue.
