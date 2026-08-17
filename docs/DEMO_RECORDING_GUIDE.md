# Demo Recording Guide

**Goal:** Create a 60-90 second screen recording showing the complete workflow from enrollment to attack detection.

---

## Prerequisites

- Both servers running:
  - Backend: `cd backend && uvicorn main:app --reload`
  - Frontend: `cd frontend && npm run dev`
- Browser window at http://localhost:5173
- Screen recording software ready:
  - **Windows:** Xbox Game Bar (Win+G), Snipping Tool, or OBS Studio
  - **Mac:** QuickTime Player or ScreenFlow
  - **Linux:** SimpleScreenRecorder or OBS Studio

---

## Recording Steps (60-90 seconds total)

### 1. Landing Page (2 seconds)
- Show the homepage with the 3-step visual
- Don't linger — just establish context

### 2. Quick Sign Up (3 seconds)
- Click "Get Started"
- Fill in username/password quickly
- **Save the 4-digit PIN shown!** You'll need it later
- Click through to login

### 3. Enrollment (10 seconds)
**Don't type the entire passage — we'll skip ahead:**
- Start typing the enrollment passage
- Type ~50 characters normally
- **Cut/jump to when progress bar is ~80%** (use video editing or just type fast)
- Show "Register Keystroke Signature" button becoming enabled
- Click it, show brief loading state
- Success message → transitions to session

### 4. Normal Session (10 seconds)
- Show the session dashboard with:
  - Text area for typing
  - "SECURE" status badge (green)
  - Live keystroke counter incrementing
  - Empty anomaly chart (or first few points)
- Type normally for a few seconds
- Emphasize the "Events: XX" counter going up

### 5. Synthetic Attack Demo (20 seconds)
**This is the key moment:**
- Hover over "Demo: Synthetic Attack" button
- Click it
- **Watch the chart and status badge:**
  - First window: Status changes to "CAUTION" (yellow/orange)
  - Second window: Another warning
  - SHAP explanation modal appears automatically
  - Show the feature breakdown (typing_speed, dwell_mean, etc.)
  - Close SHAP modal
- Third window triggers: Status → "SESSION LOCKED" (red)
- Lockout overlay appears on text area

### 6. Session Summary (5 seconds)
- Click "End Session & Save Biometric Data" (if not already locked)
- OR if locked, click "Restart Session"
- Show the session summary screen with:
  - Total windows analyzed
  - Final risk status
  - Model retrained indicator
- Don't linger — just show it exists

### 7. Optional: MFA Challenge (add 10 seconds if showing)
**If you want to demonstrate MFA:**
- After triggering attack, wait for 2 consecutive warnings
- MFA modal should appear: "⚠️ Verification Required"
- Enter the PIN you saved from signup
- Show either:
  - **Correct PIN:** Modal dismisses, session continues
  - **Wrong PIN:** Error message with attempts remaining

---

## Recording Tips

### Frame Size
- **1920x1080 or 1280x720** — full browser window
- Hide browser toolbars (F11 for fullscreen)
- Zoom browser to 90-100% for comfortable text size

### Timing
- **Don't rush the attack demo** — that's the payoff
- Speed up enrollment and normal typing (or edit them down)
- Pause briefly on the SHAP explanation so people can see it

### Audio
- **No audio needed** — let the visuals tell the story
- If you add audio, keep it professional (no music, just concise narration)

### Cursor
- Make cursor visible (enable cursor highlighting in OBS if needed)
- Point at key elements as they appear:
  - Status badge changes
  - Anomaly score spikes
  - SHAP features

---

## Post-Recording: Convert to GIF

### Option 1: ScreenToGif (Windows, easiest)
1. Download [ScreenToGif](https://www.screentogif.com/)
2. Open your video file
3. Edit → Reduce framerate to 10 fps
4. Edit → Resize to max width 800px
5. File → Save As → Optimize for size
6. Save as `docs/demo.gif`

### Option 2: FFmpeg (cross-platform)
```bash
# Install ffmpeg first
# Windows: choco install ffmpeg
# Mac: brew install ffmpeg
# Linux: apt install ffmpeg

# Convert video to GIF
ffmpeg -i demo.mp4 -vf "fps=10,scale=800:-1:flags=lanczos" -c:v gif docs/demo.gif

# If file size is too large, try lower quality:
ffmpeg -i demo.mp4 -vf "fps=8,scale=600:-1:flags=lanczos" docs/demo.gif
```

### Option 3: Keep as MP4 (if GIF is too large)
- GitHub READMEs support embedded video
- Rename to `demo.mp4` instead of `demo.gif`
- Update README.md: `![Demo](docs/demo.mp4)` → `<video src="docs/demo.mp4" autoplay loop muted></video>`

### Optimization Targets
- **GIF size:** Under 5MB (GitHub limit is 10MB, but smaller is better)
- **Duration:** 60-90 seconds max
- **Frame rate:** 8-10 fps (smooth enough for UI, small file size)
- **Dimensions:** 600-800px width

---

## Example Timeline (90 seconds)

| Time | Scene | What to Show |
|------|-------|--------------|
| 0:00-0:02 | Landing | Homepage 3-step visual |
| 0:02-0:05 | Signup | Username, password, PIN |
| 0:05-0:15 | Enrollment | Type passage, progress bar, training |
| 0:15-0:25 | Normal Session | Type normally, green status, counter |
| 0:25-0:45 | Attack Demo | Button click → warnings → SHAP → lockout |
| 0:45-0:50 | Lockout Screen | Red overlay, lock icon |
| 0:50-0:55 | Session Summary | Metrics, model status |
| 0:55-0:90 | Optional MFA | PIN challenge workflow |

---

## Checklist Before Recording

- [ ] Servers running (backend + frontend)
- [ ] Browser at http://localhost:5173 in clean state
- [ ] Screen recording software ready
- [ ] Browser fullscreen (F11) or toolbars hidden
- [ ] Cursor visible and highlighted
- [ ] Practice the flow once to get timing right
- [ ] Have a username/password ready (e.g., demouser / demo1234)
- [ ] Clear any previous user data (or use fresh MongoDB)

---

## After Recording

1. **Watch it back** — does it flow? Any awkward pauses?
2. **Trim** — cut dead time at start/end
3. **Convert to GIF** — use ScreenToGif or ffmpeg
4. **Check file size** — should be under 5MB
5. **Test in README** — does `![Demo](docs/demo.gif)` render correctly?
6. **Commit and push:**
   ```bash
   git add docs/demo.gif
   git commit -m "Add demo recording showing enrollment to attack detection"
   git push
   ```

---

## Alternative: Series of Screenshots

If screen recording is too much, create a series of static images instead:

1. `docs/screenshot-enrollment.png` — Enrollment progress
2. `docs/screenshot-session-secure.png` — Normal typing, green status
3. `docs/screenshot-attack-detected.png` — Red lockout screen
4. `docs/screenshot-shap.png` — SHAP explanation modal

Then update README:
```markdown
### Screenshots

<div align="center">
  <img src="docs/screenshot-enrollment.png" width="45%"/>
  <img src="docs/screenshot-session-secure.png" width="45%"/>
  <img src="docs/screenshot-attack-detected.png" width="45%"/>
  <img src="docs/screenshot-shap.png" width="45%"/>
</div>
```

---

**Good luck! The demo is your project's "movie trailer" — make it smooth and engaging.**
