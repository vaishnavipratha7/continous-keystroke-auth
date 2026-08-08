import React, { useState, useEffect, useRef } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine, ReferenceArea } from 'recharts';

const API_BASE = "http://127.0.0.1:8000";

export default function App() {
  const [page, setPage] = useState('login'); // login, signup, enrollment, session
  const [token, setToken] = useState(localStorage.getItem('token') || null);
  const [username, setUsername] = useState(localStorage.getItem('username') || null);
  const [error, setError] = useState('');
  const [info, setInfo] = useState('');
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const savedToken = localStorage.getItem('token');
    if (savedToken) {
      setPage('session');
    }
  }, []);

  // Authentication helper
  const handleLogout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('username');
    setToken(null);
    setUsername(null);
    setPage('login');
  };

  const handleLoginSuccess = (token, user) => {
    localStorage.setItem('token', token);
    localStorage.setItem('username', user);
    setToken(token);
    setUsername(user);
    setPage('enrollment');
  };

  return (
    <div>
      <Navbar username={username} handleLogout={handleLogout} page={page} setPage={setPage} token={token} />
      <main style={{ minHeight: 'calc(100vh - 70px)' }}>
        {error && (
          <div style={{
            maxWidth: '500px', margin: '20px auto', padding: '12px 20px', 
            background: 'rgba(239, 68, 68, 0.15)', border: '1px solid rgba(239, 68, 68, 0.3)', 
            borderRadius: '8px', color: '#f87171', fontSize: '0.9rem', display: 'flex', justifyContent: 'between'
          }}>
            <span>{error}</span>
            <button onClick={() => setError('')} style={{ background: 'none', border: 'none', color: '#f87171', cursor: 'pointer', marginLeft: 'auto' }}>×</button>
          </div>
        )}
        {info && (
          <div style={{
            maxWidth: '500px', margin: '20px auto', padding: '12px 20px', 
            background: 'rgba(16, 185, 129, 0.15)', border: '1px solid rgba(16, 185, 129, 0.3)', 
            borderRadius: '8px', color: '#34d399', fontSize: '0.9rem'
          }}>
            {info}
          </div>
        )}

        {page === 'login' && <LoginView handleLoginSuccess={handleLoginSuccess} setPage={setPage} setError={setError} />}
        {page === 'signup' && <SignupView setPage={setPage} setError={setError} setInfo={setInfo} />}
        {page === 'enrollment' && <EnrollmentView token={token} setPage={setPage} setError={setError} />}
        {page === 'session' && <SessionView token={token} username={username} setError={setError} />}
      </main>
    </div>
  );
}

// NAVBAR COMPONENT
function Navbar({ username, handleLogout, page, setPage, token }) {
  return (
    <nav style={{
      display: 'flex', justifyContent: 'space-between', alignItems: 'center',
      padding: '15px 30px', borderBottom: '1px solid var(--border-color)',
      background: 'rgba(11, 15, 25, 0.8)', backdropFilter: 'blur(10px)',
      position: 'sticky', top: 0, zIndex: 100
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '10px', cursor: 'pointer' }} onClick={() => token ? setPage('session') : setPage('login')}>
        <div style={{
          width: '32px', height: '32px', borderRadius: '8px',
          background: 'linear-gradient(135deg, var(--color-primary) 0%, var(--color-primary-hover) 100%)',
          display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 'bold', fontSize: '1.2rem', color: '#fff'
        }}>K</div>
        <h2 style={{ fontSize: '1.25rem', fontWeight: 700, margin: 0 }}>
          Key<span style={{ color: 'var(--color-primary)' }}>Recs</span> Continuous Auth
        </h2>
      </div>

      {token ? (
        <div style={{ display: 'flex', alignItems: 'center', gap: '20px' }}>
          <span style={{ color: 'var(--color-text-muted)', fontSize: '0.9rem' }}>
            User: <strong style={{ color: 'var(--color-text-main)' }}>{username}</strong>
          </span>
          <button onClick={() => setPage('enrollment')} style={{
            background: 'none', border: 'none', color: 'var(--color-text-muted)', 
            cursor: 'pointer', fontSize: '0.9rem', transition: 'var(--transition-smooth)'
          }} className="nav-link">
            Re-Enroll Signature
          </button>
          <button onClick={() => setPage('session')} style={{
            background: 'none', border: 'none', color: 'var(--color-text-muted)', 
            cursor: 'pointer', fontSize: '0.9rem', transition: 'var(--transition-smooth)'
          }} className="nav-link">
            Dashboard
          </button>
          <button onClick={handleLogout} className="btn-secondary" style={{ padding: '6px 12px', fontSize: '0.85rem' }}>
            Logout
          </button>
        </div>
      ) : (
        <div style={{ display: 'flex', gap: '12px' }}>
          <button onClick={() => setPage('login')} className="btn-secondary" style={{ padding: '6px 16px', fontSize: '0.85rem' }}>Login</button>
          <button onClick={() => setPage('signup')} className="btn-primary" style={{ padding: '6px 16px', fontSize: '0.85rem', width: 'auto', boxShadow: 'none' }}>Sign Up</button>
        </div>
      )}
    </nav>
  );
}

// LOGIN VIEW
function LoginView({ handleLoginSuccess, setPage, setError }) {
  const [usernameInput, setUsernameInput] = useState('');
  const [passwordInput, setPasswordInput] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    if (!usernameInput || !passwordInput) {
      setError('Please fill in all fields.');
      return;
    }
    setSubmitting(true);
    try {
      const res = await fetch(`${API_BASE}/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username: usernameInput, password: passwordInput })
      });
      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || 'Login failed.');
      }
      handleLoginSuccess(data.token, data.username);
    } catch (err) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="auth-container fade-in">
      <div className="auth-card glass-panel">
        <h2 style={{ marginBottom: '10px', fontSize: '1.75rem', textAlign: 'center' }}>Welcome Back</h2>
        <p style={{ color: 'var(--color-text-muted)', fontSize: '0.9rem', textAlign: 'center', marginBottom: '30px' }}>
          Continuous Keystroke Biometric Authentication
        </p>

        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label htmlFor="username">Username</label>
            <input
              type="text"
              id="username"
              className="form-control"
              placeholder="Enter username"
              value={usernameInput}
              onChange={(e) => setUsernameInput(e.target.value)}
            />
          </div>

          <div className="form-group">
            <label htmlFor="password">Password</label>
            <input
              type="password"
              id="password"
              className="form-control"
              placeholder="Enter password"
              value={passwordInput}
              onChange={(e) => setPasswordInput(e.target.value)}
            />
          </div>

          <button type="submit" className="btn-primary" disabled={submitting} style={{ marginTop: '10px' }}>
            {submitting ? 'Authenticating...' : 'Secure Login'}
          </button>
        </form>

        <p style={{ marginTop: '20px', textAlign: 'center', fontSize: '0.85rem', color: 'var(--color-text-muted)' }}>
          Don't have an account?{' '}
          <span onClick={() => setPage('signup')} style={{ color: 'var(--color-primary)', cursor: 'pointer', fontWeight: 600 }}>
            Sign Up
          </span>
        </p>
      </div>
    </div>
  );
}

// SIGNUP VIEW
function SignupView({ setPage, setError, setInfo }) {
  const [usernameInput, setUsernameInput] = useState('');
  const [passwordInput, setPasswordInput] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    if (!usernameInput || !passwordInput || !confirmPassword) {
      setError('Please fill in all fields.');
      return;
    }
    if (passwordInput !== confirmPassword) {
      setError('Passwords do not match.');
      return;
    }
    setSubmitting(true);
    try {
      const res = await fetch(`${API_BASE}/signup`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username: usernameInput, password: passwordInput })
      });
      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || 'Signup failed.');
      }
      setInfo('Account created successfully! You can now log in.');
      setPage('login');
    } catch (err) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="auth-container fade-in">
      <div className="auth-card glass-panel">
        <h2 style={{ marginBottom: '10px', fontSize: '1.75rem', textAlign: 'center' }}>Create Account</h2>
        <p style={{ color: 'var(--color-text-muted)', fontSize: '0.9rem', textAlign: 'center', marginBottom: '30px' }}>
          Enroll your keystroke dynamics profile
        </p>

        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label htmlFor="signup-username">Username</label>
            <input
              type="text"
              id="signup-username"
              className="form-control"
              placeholder="Choose a username"
              value={usernameInput}
              onChange={(e) => setUsernameInput(e.target.value)}
            />
          </div>

          <div className="form-group">
            <label htmlFor="signup-password">Password</label>
            <input
              type="password"
              id="signup-password"
              className="form-control"
              placeholder="Create password"
              value={passwordInput}
              onChange={(e) => setPasswordInput(e.target.value)}
            />
          </div>

          <div className="form-group">
            <label htmlFor="signup-confirm">Confirm Password</label>
            <input
              type="password"
              id="signup-confirm"
              className="form-control"
              placeholder="Confirm password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
            />
          </div>

          <button type="submit" className="btn-primary" disabled={submitting} style={{ marginTop: '10px' }}>
            {submitting ? 'Creating account...' : 'Create Account'}
          </button>
        </form>

        <p style={{ marginTop: '20px', textAlign: 'center', fontSize: '0.85rem', color: 'var(--color-text-muted)' }}>
          Already have an account?{' '}
          <span onClick={() => setPage('login')} style={{ color: 'var(--color-primary)', cursor: 'pointer', fontWeight: 600 }}>
            Login
          </span>
        </p>
      </div>
    </div>
  );
}

// ENROLLMENT VIEW
function EnrollmentView({ token, setPage, setError }) {
  const targetText = "Continuous keystroke authentication monitors typing dynamics to detect anomalies like session hijacking. It uses timing features like dwell time and flight time to build a unique biometric profile. Please type this passage carefully to enroll your signature.";
  
  const [typedText, setTypedText] = useState('');
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(false);
  const [progressMsg, setProgressMsg] = useState('');
  const [repetitionsCount, setRepetitionsCount] = useState(0);
  
  const pressedKeysRef = useRef({});

  const handleKeyDown = (e) => {
    // Avoid tracking repeated keydown events when holding a key
    if (e.repeat) return;
    
    const key = e.key;
    const time = performance.now();
    pressedKeysRef.current[key] = time;
  };

  const handleKeyUp = (e) => {
    const key = e.key;
    const time = performance.now();
    
    if (key in pressedKeysRef.current) {
      const downTime = pressedKeysRef.current[key];
      // Convert to seconds relative to page load
      const eventDoc = {
        key: key,
        down_time: downTime / 1000.0,
        up_time: time / 1000.0
      };
      
      setEvents(prev => [...prev, eventDoc]);
      delete pressedKeysRef.current[key];
    }
  };

  // Detect when target sentence is fully typed
  const handleTextChange = (e) => {
    const val = e.target.value;
    setTypedText(val);

    // If typed text is roughly the length of target text
    if (val.trim() === targetText.trim()) {
      setRepetitionsCount(prev => prev + 1);
      setTypedText(''); // reset textarea for next run
      setProgressMsg(`Repetition ${repetitionsCount + 1} completed! Keep typing.`);
    }
  };

  const handleEnrollSubmit = async () => {
    if (events.length < 350) {
      setError(`Please type more. Currently have ${events.length} events, need at least 350 for stable model calibration.`);
      return;
    }
    
    setLoading(true);
    setProgressMsg("Sending keystroke dynamics events batch to server...");
    
    try {
      // 1. Submit raw events
      const enrollRes = await fetch(`${API_BASE}/enroll/keystrokes`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ events: events })
      });
      
      const enrollData = await enrollRes.json();
      if (!enrollRes.ok) {
        throw new Error(enrollData.detail || "Failed to submit enrollment keystrokes.");
      }
      
      // 2. Train model
      setProgressMsg("Analyzing typing signature. Training Isolation Forest model...");
      const trainRes = await fetch(`${API_BASE}/enroll/train`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      
      const trainData = await trainRes.json();
      if (!trainRes.ok) {
        throw new Error(trainData.detail || "Failed to train biometric model. Please type more naturally.");
      }
      
      setProgressMsg("Biometric signature successfully enrolled!");
      setTimeout(() => {
        setPage('session');
      }, 1500);
      
    } catch (err) {
      setError(err.message);
      setLoading(false);
    }
  };

  const handleReset = () => {
    setTypedText('');
    setEvents([]);
    setRepetitionsCount(0);
    setProgressMsg('');
    setError('');
  };

  const minKeystrokes = 350;
  const progressPercent = Math.min(100, Math.round((events.length / minKeystrokes) * 100));

  return (
    <div style={{ maxWidth: '800px', margin: '40px auto', padding: '0 20px' }} className="fade-in">
      <div className="glass-panel" style={{ padding: '30px' }}>
        <h2 style={{ fontSize: '1.75rem', marginBottom: '10px' }}>Enroll Biometric Signature</h2>
        <p style={{ color: 'var(--color-text-muted)', fontSize: '0.95rem', marginBottom: '24px' }}>
          To build your custom keystroke profile, type the passage below <strong>2 to 3 times</strong>. Type at your normal, comfortable pace.
        </p>

        {/* TARGET PASSAGE */}
        <div style={{
          background: 'rgba(255,255,255,0.02)', border: '1px solid var(--border-color)',
          borderRadius: '10px', padding: '20px', marginBottom: '24px', fontSize: '1.05rem',
          lineHeight: '1.6', userSelect: 'none'
        }}>
          <span style={{ color: 'var(--color-primary)', fontWeight: 600 }}>Passage:</span><br />
          <span style={{ letterSpacing: '0.01em' }}>{targetText}</span>
        </div>

        {/* TYPING BOX */}
        <div className="form-group" style={{ marginBottom: '16px' }}>
          <label htmlFor="enroll-textarea">Type the passage here:</label>
          <textarea
            id="enroll-textarea"
            className="form-control"
            rows="5"
            placeholder="Click here and begin typing..."
            value={typedText}
            onChange={handleTextChange}
            onKeyDown={handleKeyDown}
            onKeyUp={handleKeyUp}
            disabled={loading}
            style={{ resize: 'none', fontSize: '1.05rem', fontFamily: 'inherit', letterSpacing: '0.01em' }}
          />
        </div>

        {/* PROGRESS METRICS */}
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px', fontSize: '0.85rem' }}>
          <span style={{ color: 'var(--color-text-muted)' }}>
            Total keystrokes recorded: <strong style={{ color: 'var(--color-text-main)' }}>{events.length}</strong>
          </span>
          <span style={{ color: 'var(--color-text-muted)' }}>
            Passages completed: <strong style={{ color: 'var(--color-text-main)' }}>{repetitionsCount}</strong>
          </span>
        </div>

        {/* Progress Bar */}
        <div style={{
          width: '100%', height: '8px', background: 'rgba(255,255,255,0.05)', 
          borderRadius: '4px', overflow: 'hidden', marginBottom: '24px'
        }}>
          <div style={{
            width: `${progressPercent}%`, height: '100%',
            background: 'linear-gradient(90deg, var(--color-primary) 0%, var(--color-secure) 100%)',
            transition: 'width 0.3s ease'
          }}></div>
        </div>

        {progressMsg && (
          <div style={{
            padding: '10px 15px', background: 'rgba(99, 102, 241, 0.1)', 
            border: '1px solid rgba(99, 102, 241, 0.2)', borderRadius: '8px', 
            color: 'var(--color-text-main)', marginBottom: '24px', fontSize: '0.9rem', 
            textAlign: 'center'
          }}>
            {progressMsg}
          </div>
        )}

        <div style={{ display: 'flex', gap: '15px' }}>
          <button
            onClick={handleEnrollSubmit}
            className="btn-primary"
            disabled={events.length < minKeystrokes || loading}
            style={{ flex: 2 }}
          >
            {loading ? 'Processing...' : events.length < minKeystrokes ? `Type ${minKeystrokes - events.length} more characters...` : 'Register Keystroke Signature'}
          </button>
          <button
            onClick={handleReset}
            className="btn-secondary"
            disabled={loading}
            style={{ flex: 1 }}
          >
            Reset
          </button>
        </div>
      </div>
    </div>
  );
}

// SESSION VIEW (DASHBOARD)
function SessionView({ token, username, setError }) {
  const [sessionId] = useState(() => Math.random().toString(36).substring(2, 10) + "_" + Date.now());
  const [typedText, setTypedText] = useState('');
  const [riskState, setRiskState] = useState('initializing'); // initializing, low, medium, high, flagged
  const [scoreHistory, setScoreHistory] = useState([]);
  const [totalEvents, setTotalEvents] = useState(0);
  const [explainWindowIndex, setExplainWindowIndex] = useState(null);
  const [shapData, setShapData] = useState(null);
  const [explainLoading, setExplainLoading] = useState(false);
  const [ending, setEnding] = useState(false);
  
  const localQueueRef = useRef([]);
  const pressedKeysRef = useRef({});

  // Fetch score history from backend
  const fetchSessionScore = async () => {
    try {
      const res = await fetch(`${API_BASE}/session/score?session_id=${sessionId}`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (!res.ok) throw new Error("Failed to load session score.");
      const data = await res.json();
      
      setRiskState(data.risk_level);
      setScoreHistory(data.score_history || []);
    } catch (err) {
      console.error(err);
    }
  };

  // Poll score updates every 2 seconds
  useEffect(() => {
    fetchSessionScore();
    const interval = setInterval(fetchSessionScore, 2000);
    return () => clearInterval(interval);
  }, [sessionId]);
  
  // Auto-open SHAP explanation when session becomes flagged
  useEffect(() => {
    if (riskState === 'flagged' && scoreHistory.length > 0 && explainWindowIndex === null) {
      const lastWindow = scoreHistory[scoreHistory.length - 1];
      loadExplanation(lastWindow.window_index);
    }
  }, [riskState, scoreHistory]);

  // Handle Keystroke Capture
  const handleKeyDown = (e) => {
    if (riskState === 'flagged') {
      e.preventDefault();
      return;
    }
    if (e.repeat) return;
    pressedKeysRef.current[e.key] = performance.now();
  };

  const handleKeyUp = (e) => {
    if (riskState === 'flagged') {
      e.preventDefault();
      return;
    }
    const key = e.key;
    if (key in pressedKeysRef.current) {
      const downTime = pressedKeysRef.current[key];
      const upTime = performance.now();
      
      const eventDoc = {
        key: key,
        down_time: downTime / 1000.0,
        up_time: upTime / 1000.0
      };
      
      localQueueRef.current.push(eventDoc);
      setTotalEvents(prev => prev + 1);
      delete pressedKeysRef.current[key];
      
      // Send batch to server once queue gets ~15 events
      if (localQueueRef.current.length >= 15) {
        sendBatch();
      }
    }
  };

  const sendBatch = async () => {
    const batch = [...localQueueRef.current];
    localQueueRef.current = [];
    
    try {
      const res = await fetch(`${API_BASE}/session/keystrokes`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          session_id: sessionId,
          events: batch
        })
      });
      if (!res.ok) {
        const d = await res.json();
        console.error("Batch send error:", d.detail);
      } else {
        // Trigger score update
        fetchSessionScore();
      }
    } catch (err) {
      console.error("Failed to push batch events:", err);
    }
  };

  // Triggered when user clicks End Session
  const handleEndSession = async () => {
    setEnding(true);
    // Flush remaining keys in queue
    if (localQueueRef.current.length > 0) {
      await sendBatch();
    }
    try {
      const res = await fetch(`${API_BASE}/session/end?session_id=${sessionId}`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` }
      });
      const data = await res.json();
      if (res.ok) {
        alert(data.message + (data.model_retrained ? " (Model adapted to new clean samples and retrained!)" : ""));
        window.location.reload();
      }
    } catch (err) {
      console.error(err);
    } finally {
      setEnding(false);
    }
  };

  // Load SHAP explanation for a specific window
  const loadExplanation = async (wIdx) => {
    setExplainWindowIndex(wIdx);
    setExplainLoading(true);
    setShapData(null);
    try {
      const res = await fetch(`${API_BASE}/session/explain/${wIdx}?session_id=${sessionId}`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (!res.ok) throw new Error("Failed to load explanation.");
      const data = await res.json();
      setShapData(data);
    } catch (err) {
      console.error(err);
    } finally {
      setExplainLoading(false);
    }
  };

  // Simulate Hijack Attack by sending a batch of 50 anomalous speed events
  const handleSimulateHijack = async () => {
    // Generate artificial anomalous keystroke times:
    // e.g. very long flight times (2.5s) and sluggish dwell times (1.5s)
    const attackerEvents = [];
    let curTime = performance.now() / 1000.0;
    
    // We send 55 events to ensure a full window is completed and scored
    for (let i = 0; i < 55; i++) {
      const dwell = 1.5;
      const flight = 2.5;
      attackerEvents.push({
        key: "X",
        down_time: curTime,
        up_time: curTime + dwell
      });
      curTime += dwell + flight;
    }
    
    try {
      const res = await fetch(`${API_BASE}/session/keystrokes`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          session_id: sessionId,
          events: attackerEvents
        })
      });
      
      if (res.ok) {
        // Poll scores multiple times to show state progression
        fetchSessionScore();
        setTimeout(fetchSessionScore, 1000);
        setTimeout(fetchSessionScore, 2000);
      }
    } catch (err) {
      console.error("Failed to inject hijack simulation:", err);
    }
  };

  // Map state to human-readable tag style
  const getRiskStatusLabel = () => {
    switch (riskState) {
      case 'low': return { text: 'SECURE', className: 'badge-secure' };
      case 'medium': return { text: 'WARNING: DYNAMICS SHIFT', className: 'badge-warning' };
      case 'high': return { text: 'HIGH RISK ALERT', className: 'badge-danger' };
      case 'flagged': return { text: 'CRITICAL: HIJACK DETECTED (LOCKED)', className: 'badge-danger' };
      case 'initializing': return { text: 'INITIALIZING', className: 'badge-collecting' };
      default: return { text: 'COLLECTING DATA', className: 'badge-collecting' };
    }
  };

  const statusLabel = getRiskStatusLabel();

  return (
    <div className="dashboard-grid fade-in">
      
      {/* LEFT COLUMN: ACTIVE VERIFICATION AREA */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
        <div className="glass-panel" style={{ padding: '24px', flex: 1, display: 'flex', flexDirection: 'column' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
            <h3 style={{ fontSize: '1.25rem', margin: 0 }}>Active Session Verification</h3>
            <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
              <span style={{ fontSize: '0.85rem', color: 'var(--color-text-muted)' }}>
                Session: <code>{sessionId.split('_')[0]}</code>
              </span>
              <span className={`badge-collecting`} style={{
                padding: '4px 10px', borderRadius: '12px', fontSize: '0.75rem', fontWeight: 600
              }}>
                Events: {totalEvents}
              </span>
            </div>
          </div>

          <div style={{ position: 'relative', flex: 1, display: 'flex', flexDirection: 'column' }}>
            <textarea
              className="form-control"
              placeholder="Type freely here. The system is continuously monitoring your typing patterns in the background. If someone else takes over your keyboard, the session will immediately flag an anomaly..."
              rows="12"
              value={typedText}
              onChange={(e) => setTypedText(e.target.value)}
              onKeyDown={handleKeyDown}
              onKeyUp={handleKeyUp}
              disabled={riskState === 'flagged'}
              style={{
                background: 'rgba(0,0,0,0.2)', border: '1px solid var(--border-color)',
                fontSize: '1.1rem', letterSpacing: '0.01em', lineHeight: '1.6', 
                flex: 1, minHeight: '300px', resize: 'none',
                borderColor: riskState === 'flagged' ? 'var(--color-danger)' : undefined
              }}
            />

            {/* Hijacked Lockdown Overlay */}
            {riskState === 'flagged' && (
              <div style={{
                position: 'absolute', top: 0, left: 0, right: 0, bottom: 0,
                background: 'rgba(15, 23, 42, 0.9)', backdropFilter: 'blur(4px)',
                borderRadius: '8px', display: 'flex', flexDirection: 'column',
                justifyContent: 'center', alignItems: 'center', padding: '20px',
                border: '2px solid var(--color-danger)'
              }} className="fade-in">
                <div style={{
                  width: '64px', height: '64px', borderRadius: '50%',
                  background: 'rgba(239, 68, 68, 0.2)', border: '2px solid var(--color-danger)',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  fontSize: '2rem', color: 'var(--color-danger)', marginBottom: '16px'
                }}>🔒</div>
                <h2 style={{ color: 'var(--color-danger)', fontSize: '1.5rem', marginBottom: '8px', textAlign: 'center' }}>
                  SESSION TERMINATED
                </h2>
                <p style={{ color: 'var(--color-text-muted)', fontSize: '0.95rem', textAlign: 'center', maxWidth: '380px', marginBottom: '24px' }}>
                  Anomalous typing signature detected. The session was locked out to prevent session hijacking.
                </p>
                <button onClick={() => window.location.reload()} className="btn-primary" style={{ width: 'auto', padding: '8px 24px' }}>
                  Restart Session
                </button>
              </div>
            )}
          </div>

          <div style={{ display: 'flex', gap: '15px', marginTop: '16px' }}>
            <button
              onClick={handleEndSession}
              className="btn-primary"
              disabled={ending || totalEvents < 10 || riskState === 'flagged'}
              style={{ flex: 2, background: 'linear-gradient(135deg, #10b981 0%, #059669 100%)', boxShadow: '0 4px 12px rgba(16, 185, 129, 0.3)' }}
            >
              {ending ? 'Syncing...' : 'End Session & Save Biometric Data'}
            </button>
            
            <button
              onClick={handleSimulateHijack}
              className="btn-secondary"
              disabled={riskState === 'flagged'}
              style={{ flex: 1, border: '1px solid rgba(239, 68, 68, 0.3)', color: '#f87171' }}
              title="Injects synthetic extreme timing values for UI demonstration. This is NOT the validated detection shown in offline validation results, which uses real participant data."
            >
              ⚡ Demo: Synthetic Attack
            </button>
          </div>
        </div>
      </div>

      {/* RIGHT COLUMN: RISKS & SCORE METRICS */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
        
        {/* RISK STATUS CARD */}
        <div className="glass-panel" style={{
          padding: '24px', textAlign: 'center',
          borderColor: riskState === 'flagged' ? 'var(--color-danger)' : 
                       riskState === 'low' ? 'var(--color-secure)' : 
                       riskState === 'medium' ? 'var(--color-warning)' : 'var(--border-color)'
        }}>
          <h4 style={{ color: 'var(--color-text-muted)', fontSize: '0.85rem', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '10px' }}>
            Active Security Level
          </h4>
          <div className={`${statusLabel.className}`} style={{
            display: 'inline-block', padding: '10px 24px', borderRadius: '30px',
            fontSize: '1.1rem', fontWeight: 800, letterSpacing: '0.02em', marginBottom: '10px'
          }}>
            {statusLabel.text}
          </div>
          <p style={{ fontSize: '0.85rem', color: 'var(--color-text-muted)' }}>
            {riskState === 'initializing' && "Type at least 50 keys to authenticate session dynamics..."}
            {riskState === 'low' && "Secure keystroke profile matched."}
            {riskState === 'medium' && "Typing rhythm variance detected. Verifying profile..."}
            {riskState === 'flagged' && "Lockdown triggered. 3 consecutive abnormal windows scored."}
          </p>
        </div>

        {/* SCORE HISTORY LIVE CHART */}
        <div className="glass-panel" style={{ padding: '24px', flex: 1, display: 'flex', flexDirection: 'column' }}>
          <h3 style={{ fontSize: '1.1rem', marginBottom: '16px' }}>Window Verification Chart</h3>
          
          {scoreHistory.length === 0 ? (
            <div style={{
              flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center',
              color: 'var(--color-text-muted)', fontSize: '0.9rem', textAlign: 'center', minHeight: '250px'
            }}>
              No windows evaluated yet.<br />Keep typing to generate the first window.
            </div>
          ) : (
            <>
              <ResponsiveContainer width="100%" height={300}>
                <LineChart data={scoreHistory.map(win => ({ 
                  windowIndex: win.window_index, 
                  score: win.anomaly_score,
                  risk: win.risk_level
                }))}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" />
                  <XAxis 
                    dataKey="windowIndex" 
                    stroke="var(--color-text-muted)"
                    label={{ value: 'Window Index', position: 'insideBottom', offset: -5, fill: 'var(--color-text-muted)' }}
                  />
                  <YAxis 
                    stroke="var(--color-text-muted)"
                    label={{ value: 'Anomaly Score', angle: -90, position: 'insideLeft', fill: 'var(--color-text-muted)' }}
                  />
                  <Tooltip 
                    contentStyle={{ 
                      background: 'rgba(11, 15, 25, 0.95)', 
                      border: '1px solid var(--border-color)', 
                      borderRadius: '8px',
                      color: 'var(--color-text-main)'
                    }}
                    formatter={(value, name, props) => [
                      `${value.toFixed(4)} (${props.payload.risk})`,
                      'Anomaly Score'
                    ]}
                  />
                  
                  {/* Background bands for risk thresholds - approximate visualization */}
                  <ReferenceArea y1={-1} y2={-0.5} fill="#10b981" fillOpacity={0.05} />
                  <ReferenceArea y1={-0.5} y2={0} fill="#f59e0b" fillOpacity={0.05} />
                  <ReferenceArea y1={0} y2={3} fill="#ef4444" fillOpacity={0.05} />
                  
                  {/* Mark flagged point if exists */}
                  {scoreHistory.filter(w => w.risk_level === 'high' || w.risk_level === 'flagged').length > 0 && (
                    <ReferenceLine 
                      x={scoreHistory.find(w => w.risk_level === 'high' || w.risk_level === 'flagged')?.window_index} 
                      stroke="#ef4444" 
                      strokeDasharray="5 5"
                      label={{ value: '⚠ Flagged', position: 'top', fill: '#ef4444' }}
                    />
                  )}
                  
                  <Line 
                    type="monotone" 
                    dataKey="score" 
                    stroke="#6366f1" 
                    strokeWidth={2}
                    dot={{ fill: '#6366f1', r: 4 }}
                    activeDot={{ r: 6 }}
                  />
                </LineChart>
              </ResponsiveContainer>
              
              <div style={{ marginTop: '16px', fontSize: '0.85rem', color: 'var(--color-text-muted)', textAlign: 'center' }}>
                Click on windows below to see SHAP explanations
              </div>
              
              {/* Compact window list below chart */}
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px', marginTop: '12px', maxHeight: '80px', overflowY: 'auto' }}>
                {scoreHistory.map((win) => (
                  <button
                    key={win.window_index}
                    onClick={() => loadExplanation(win.window_index)}
                    style={{
                      padding: '6px 12px',
                      background: win.risk_level === 'low' ? 'rgba(16, 185, 129, 0.1)' : 
                                  win.risk_level === 'medium' ? 'rgba(245, 158, 11, 0.1)' : 'rgba(239, 68, 68, 0.1)',
                      border: `1px solid ${win.risk_level === 'low' ? 'rgba(16, 185, 129, 0.3)' : 
                                          win.risk_level === 'medium' ? 'rgba(245, 158, 11, 0.3)' : 'rgba(239, 68, 68, 0.3)'}`,
                      borderRadius: '6px',
                      color: 'var(--color-text-main)',
                      cursor: 'pointer',
                      fontSize: '0.75rem',
                      fontWeight: 600
                    }}
                  >
                    W{win.window_index + 1}
                  </button>
                ))}
              </div>
            </>
          )}
        </div>

      </div>

      {/* SHAP EXPLAINABILITY DIALOG/MODAL */}
      {explainWindowIndex !== null && (
        <div style={{
          position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
          background: 'rgba(0,0,0,0.6)', backdropFilter: 'blur(4px)',
          display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000,
          padding: '20px'
        }} className="fade-in">
          <div className="glass-panel" style={{ width: '100%', maxWidth: '500px', padding: '30px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
              <h3 style={{ fontSize: '1.25rem', margin: 0 }}>SHAP Explainability View</h3>
              <button
                onClick={() => setExplainWindowIndex(null)}
                style={{ background: 'none', border: 'none', fontSize: '1.5rem', color: 'var(--color-text-muted)', cursor: 'pointer' }}
              >×</button>
            </div>

            {explainLoading && (
              <div style={{ textAlign: 'center', padding: '30px 0', color: 'var(--color-text-muted)' }}>
                Generating SHAP tree-attribution scores...
              </div>
            )}

            {shapData && (
              <div>
                <h4 style={{ fontSize: '0.95rem', color: 'var(--color-text-muted)', marginBottom: '15px' }}>
                  Window index: {shapData.window_index + 1} | Attributions contributing to anomaly:
                </h4>
                
                <div style={{ display: 'flex', flexDirection: 'column', gap: '15px' }}>
                  {Object.keys(shapData.shap_values).map(feat => {
                    const val = shapData.shap_values[feat];
                    // Normalize for visual scale bar (e.g. max SHAP absolute value might be around 2.0)
                    const absoluteVal = Math.abs(val);
                    const barWidth = Math.min(100, Math.round(absoluteVal * 60));
                    const isPositive = val > 0;
                    
                    return (
                      <div key={feat}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.85rem', marginBottom: '4px' }}>
                          <span style={{ fontWeight: 600 }}>{feat}</span>
                          <span style={{ color: 'var(--color-text-muted)' }}>
                            Value: <code>{shapData.feature_values[feat].toFixed(4)}</code> | SHAP: <code>{val.toFixed(3)}</code>
                          </span>
                        </div>
                        <div style={{ width: '100%', height: '8px', background: 'rgba(255,255,255,0.05)', borderRadius: '4px', overflow: 'hidden', display: 'flex' }}>
                          {/* If positive (attributing to anomaly), show red bar, else green bar */}
                          <div style={{
                            width: `${barWidth}%`, height: '100%',
                            background: isPositive ? 'var(--color-danger)' : 'var(--color-secure)',
                            borderRadius: '4px'
                          }}></div>
                        </div>
                      </div>
                    );
                  })}
                </div>

                <div style={{ marginTop: '24px', fontSize: '0.8rem', color: 'var(--color-text-muted)', background: 'rgba(255,255,255,0.01)', padding: '12px', border: '1px solid var(--border-color)', borderRadius: '6px' }}>
                  💡 <strong>Interpretation</strong>: Red bars represent feature values that pushed the score towards being classified as anomalous (impostor typing). Green bars represent features matching your genuine enrollment dynamics.
                </div>
              </div>
            )}
          </div>
        </div>
      )}

    </div>
  );
}
