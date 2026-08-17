# Continuous Keystroke Authentication

Real-time session hijacking detection using typing rhythm and unsupervised machine learning — extending published keystroke-dynamics research from login-only verification to continuous, in-session monitoring.

![Demo](docs/demo.gif)

[![Python Tests](https://img.shields.io/badge/tests-passing-brightgreen)](scripts/test_e2e.py)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

---

## The Problem

Most authentication happens once, at login. [Martins et al. (2025)](https://doi.org/10.1007/s42452-025-07449-5) demonstrate that typing rhythm — how long you hold keys, the pauses between them — can identify a user with ~80% accuracy using supervised classifiers (KNN, Random Forest, LightGBM). But their approach only verifies identity at the point of login, and requires labeled examples of "impostor" typing to train on — data that's impractical to collect for every real user.

If someone gets past login (a stolen session, an unattended unlocked machine), nothing catches them.

## The Approach

This project builds a **continuous** verification layer on top of that gap:

- **Per-user, unsupervised models** — each user gets their own Isolation Forest, trained only on *their own* enrollment typing. No impostor data required, unlike the original supervised approach.
- **Windowed monitoring** — typing is split into 50-keystroke windows, each scored against the user's personal baseline in real time throughout the session, not just at login.
- **Smoothed risk decisions** — a session is only flagged after 3 consecutive medium/high-risk windows, so a single tired or distracted moment doesn't trigger a false lockout.
- **Step-up verification (MFA)** — instead of an instant hard lockout, sustained anomalies first prompt a PIN challenge, giving a legitimate user with naturally shifting typing a chance to confirm identity before the session is terminated.
- **Adaptive learning** — a session confirmed safe on completion feeds back into the user's model, letting the baseline evolve with natural drift over time.
- **Explainability** — every flagged window comes with a SHAP-based explanation of which specific behavioral feature (typing speed, key-hold time, inter-key timing) drove the anomaly score.

## Results

Validated on the [KeyRecs](https://doi.org/10.1007/s00521-022-07472-0) free-text dataset (562K+ real keystroke events, 100 participants):

| Metric | Result |
|---|---|
| Equal Error Rate (EER) | 24.43% |
| Model comparison | IsolationForest (24.43% EER) outperformed OneClassSVM (31.86% EER) |
| Takeover detection lag | 2 windows (~100 keystrokes) after a real participant handoff |
| Window size | 50 digraphs (tuned against 30-digraph alternative: 26.05% EER) |

<div align="center">
  <img src="docs/figures/roc_curve.png" width="45%"/>
  <img src="docs/figures/takeover_detection.png" width="45%"/>
</div>

*Left: ROC curve across decision thresholds. Right: live anomaly score during a simulated takeover — two real participants' recorded typing spliced together. Orange marks where the attacker's typing begins; purple marks where the system locks the session.*

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         FRONTEND (React)                        │
│  Enrollment • Live session dashboard • History • SHAP explainer │
└────────────────────────┬────────────────────────────────────────┘
                          │ HTTP/JSON
┌─────────────────────────▼───────────────────────────────────────┐
│                      BACKEND (FastAPI)                          │
│  Auth (bcrypt + tokens) • ML pipeline • MongoDB persistence     │
└─────────────────────────┬───────────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────────────┐
│  KeyRecs Dataset → Digraph Extraction → Windowing → Per-user     │
│  Isolation Forest → Risk Scoring → SHAP Explanation              │
└─────────────────────────────────────────────────────────────────┘
```

**Stack**: React · FastAPI · MongoDB · scikit-learn (IsolationForest) · SHAP · pytest

## Setup

**Prerequisites**: Python 3.10+, Node 18+, MongoDB running locally.

```bash
git clone https://github.com/[your-username]/[your-repo]
cd [your-repo]

# 1. Get the dataset and build features
python scripts/download_data.py
python scripts/parse_dataset.py

# 2. Backend
cd backend
pip install -r requirements.txt
cp .env.example .env
# Edit .env to set MONGO_URI if needed
uvicorn main:app --reload

# 3. Frontend (new terminal)
cd frontend
npm install
cp .env.example .env
npm run dev
```

Open `http://localhost:5173` — sign up, enroll by typing the given passage, then watch the live risk dashboard as you type. Use the demo attack button to see detection trigger.

## Reproducing the Results

```bash
python scripts/run_validation.py
```

Regenerates `scripts/validation_report.txt` and the two figures above from scratch — including the window-size comparison and the IsolationForest vs. OneClassSVM comparison.

## Testing

```bash
cd backend
pytest tests/ -v          # unit tests on the ML pipeline
```

```bash
python scripts/test_e2e.py   # full live flow: signup → enroll → session → attack → detection → SHAP
```

## What This Project Deliberately Does *Not* Claim

- The **synthetic attack demo button** in the UI injects artificial extreme timing values to demonstrate the live UI reacting — it is not the accuracy evidence. The real evidence is `scripts/run_validation.py`'s splice test, which uses two real participants' actual recorded typing.
- This extends a published paper's identified limitations as a research/learning exercise; it has not been load-tested, penetration-tested, or deployed for real users.

## Project Structure

```
.
├── backend/
│   ├── main.py              # FastAPI endpoints
│   ├── pipeline.py          # ML pipeline (windowing, training, scoring)
│   ├── auth.py              # bcrypt + JWT session management
│   ├── db.py                # MongoDB collections
│   └── tests/               # pytest unit tests
├── frontend/
│   ├── src/
│   │   └── App.jsx          # React SPA (enrollment, session, history views)
│   └── package.json
├── scripts/
│   ├── download_data.py     # Fetch KeyRecs dataset
│   ├── parse_dataset.py     # Build digraph features
│   ├── run_validation.py    # Generate EER metrics and figures
│   └── test_e2e.py          # End-to-end system test
├── data/                    # Processed dataset (created by scripts)
└── docs/
    ├── figures/             # ROC curve, takeover detection charts
    ├── MFA_FEATURE_GUIDE.md
    ├── MFA_SECURITY_SUMMARY.md
    └── SECURITY_FIXES_APPLIED.md
```

## Documentation

- **[MFA Feature Guide](docs/MFA_FEATURE_GUIDE.md)** - Implementation details for the step-up verification challenge
- **[Security Fixes Applied](docs/SECURITY_FIXES_APPLIED.md)** - PIN hashing, rate limiting, and threat model
- **[MFA Security Summary](docs/MFA_SECURITY_SUMMARY.md)** - Quick reference for testing MFA security

## Citation

```bibtex
@article{martins2025keystroke,
  title={Keystroke dynamics for intelligent biometric authentication with machine learning},
  author={Martins, J.P. and Soares, S.C. and Pinho, A.J. and others},
  journal={Discover Applied Sciences},
  volume={7},
  pages={34},
  year={2025},
  doi={10.1007/s42452-025-07449-5}
}

@article{bours2023keyrecs,
  title={A dataset for exploring user authentication through free-text keystroke dynamics},
  author={Bours, P. and Mondal, S.},
  journal={Neural Computing and Applications},
  volume={35},
  pages={16077--16093},
  year={2023},
  doi={10.1007/s00521-022-07472-0}
}
```

## License

MIT — see [LICENSE](LICENSE).

---

**Built as a learning project extending published research.** Not production-hardened. Demonstrates continuous authentication concepts with real validation metrics from a publicly available dataset.
