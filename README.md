# Continuous Keystroke Authentication

Real-time session hijacking detection using typing patterns and machine learning.

![Demo](docs/demo.gif)

## What It Does

Monitors typing rhythm to detect when someone else takes over your keyboard. Locks out attackers within ~100 keystrokes.

**Tech**: React • FastAPI • MongoDB • IsolationForest • SHAP

**Performance**: 24.43% EER | 2-window detection lag | 562K+ keystroke dataset

<div align="center">
  <img src="docs/figures/roc_curve.png" width="45%"/>
  <img src="docs/figures/takeover_detection.png" width="45%"/>
</div>

---

*Extends keystroke dynamics research ([Martins et al., 2025](https://doi.org/10.1007/s42452-025-07449-5)) with continuous authentication and adaptive learning. Dataset: [KeyRecs](https://doi.org/10.1007/s00521-022-07472-0)*
