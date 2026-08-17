# MFA Challenge Feature - Implementation Guide

## 🔐 Overview

The Multi-Factor Authentication (MFA) challenge feature provides an additional security layer when the keystroke authentication system detects suspicious typing patterns. Instead of immediately terminating the session, it gives the legitimate user a chance to verify their identity using a 4-digit PIN.

---

## 🎯 How It Works

### 1. **User Registration**
When a user signs up:
- Backend generates a random 4-digit PIN (e.g., `"1234"`)
- PIN is stored in MongoDB user document
- PIN is returned in signup response and displayed to user
- User must remember this PIN for future verification

**Backend (`/signup`):**
```python
import random
mfa_pin = str(random.randint(1000, 9999))
users_col.insert_one({
    "username": username,
    "password_hash": pwd_hash,
    "mfa_pin": mfa_pin,
    "created_at": datetime.utcnow()
})
return {
    "message": "User created successfully",
    "mfa_pin": mfa_pin
}
```

**Frontend (SignupView):**
```javascript
setInfo(`Account created! Your security PIN is: ${data.mfa_pin}. Save this PIN...`);
```

---

### 2. **User Login**
When a user logs in:
- Backend retrieves the user's MFA PIN from database
- Returns it in the login response
- Frontend stores it in localStorage for the session

**Backend (`/login`):**
```python
return {
    "token": token,
    "username": username,
    "user_id": str(user["_id"]),
    "mfa_pin": user.get("mfa_pin", "0000")
}
```

**Frontend (LoginView):**
```javascript
if (data.mfa_pin) {
    localStorage.setItem('mfaPin', data.mfa_pin);
}
```

---

### 3. **Keystroke Monitoring**
During active session:
- System continuously monitors typing patterns
- Each window of ~50 keystrokes is scored as `low`, `medium`, or `high` risk
- Backend tracks consecutive medium/high risk windows

---

### 4. **MFA Challenge Trigger**
When **2 consecutive windows** are scored as medium/high risk:
- Backend returns `action_required: "PROMPT_MFA_CHALLENGE"`
- Frontend displays MFA challenge modal
- User must enter their 4-digit PIN to continue

**Backend (`/session/score`):**
```python
# Count consecutive medium/high risk windows from the end
consecutive_hijack_count = 0
for s in reversed(scores):
    if s["risk_level"] in ["medium", "high"]:
        consecutive_hijack_count += 1
    else:
        break

# MFA Challenge: 2 consecutive medium/high windows
if consecutive_hijack_count == 2:
    action_required = "PROMPT_MFA_CHALLENGE"
```

**Frontend Display:**
```
⚠️
Verification Required

Typing cadence variations detected.
Enter your Security PIN to maintain your session.

[____ ] (4-digit PIN input)

[Confirm Identity]
```

---

### 5. **PIN Verification**
When user enters PIN:
- Frontend sends PIN to backend `/session/verify_mfa` endpoint
- Backend compares with stored PIN in user document
- If **correct**: Resets the last 2 windows to "low" risk, session continues
- If **incorrect**: Shows error, user can retry

**Backend (`/session/verify_mfa`):**
```python
@app.post("/session/verify_mfa")
async def verify_mfa(request: dict, user_id: str = Depends(get_current_user_id)):
    pin_input = request.get("pin", "")
    session_id = request.get("session_id", "")
    
    # Get user's MFA PIN
    user = users_col.find_one({"_id": ObjectId(user_id)})
    expected_pin = user.get("mfa_pin", "0000")
    
    if pin_input != expected_pin:
        return {"success": False, "message": "Invalid PIN"}
    
    # PIN is correct - mark last 2 medium/high risk windows as "low" (verified)
    scores_cursor = session_scores_col.find({
        "user_id": user_id,
        "session_id": session_id,
        "risk_level": {"$in": ["medium", "high"]}
    }).sort("window_index", -1).limit(2)
    
    for score in scores_cursor:
        session_scores_col.update_one(
            {"_id": score["_id"]},
            {"$set": {"risk_level": "low", "mfa_verified": True}}
        )
    
    return {"success": True, "message": "Identity verified successfully"}
```

**Frontend (SessionSecurityMonitor):**
```javascript
const handleVerifyPin = async (e) => {
    e.preventDefault();
    const trimmedPin = pinInput.trim();
    
    const res = await fetch(`${API_BASE}/session/verify_mfa`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
            pin: trimmedPin,
            session_id: sessionId
        })
    });
    
    const data = await res.json();
    
    if (res.ok && data.success) {
        onResetSession(); // Clear MFA challenge, continue session
    } else {
        setMfaError(true); // Show "Invalid verification code"
    }
};
```

---

### 6. **Session Termination**
If user fails to verify OR **3+ consecutive windows** are medium/high risk:
- Backend returns `action_required: "TERMINATE_SESSION"`
- Frontend displays lockout screen
- User must re-authenticate (log in again)

**Backend:**
```python
if consecutive_hijack_count >= 3:
    flagged = True
    action_required = "TERMINATE_SESSION"
```

**Frontend Display:**
```
🚨
Security Incident Logged

Session terminated due to sustained typing profile anomalies.
Identity validation failed.

[Re-authenticate & Log In]
```

---

## 📊 MFA Flow Diagram

```
Normal Typing → LOW risk → Continue session
       ↓
Variation detected → MEDIUM risk (1st window) → Continue monitoring
       ↓
Still different → MEDIUM risk (2nd consecutive window)
       ↓
    ⚠️ MFA CHALLENGE TRIGGERED
       ↓
User enters PIN
       ├─ Correct PIN → Reset consecutive counter → Continue session
       └─ Incorrect PIN → Show error → Allow retry
              ↓
       Still typing differently → HIGH risk (3rd consecutive window)
              ↓
          🚨 SESSION TERMINATED
```

---

## 🔧 Technical Implementation

### Backend Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/signup` | POST | Generate and return MFA PIN |
| `/login` | POST | Return stored MFA PIN |
| `/session/score` | GET | Return `action_required` status |
| `/session/verify_mfa` | POST | Verify PIN and reset consecutive counter |

### Frontend Components

| Component | File | Purpose |
|-----------|------|---------|
| `SessionView` | App.jsx | Monitor `action_required` field |
| `SessionSecurityMonitor` | App.jsx | Display MFA challenge or termination UI |
| `handleMFASuccess` | App.jsx | Call backend to reset state after verification |

### Data Flow

1. **Session monitoring (polling every 2s):**
   ```
   Frontend → GET /session/score → Backend
   Backend → { action_required: "PROMPT_MFA_CHALLENGE" } → Frontend
   ```

2. **PIN verification:**
   ```
   Frontend → POST /session/verify_mfa { pin: "1234", session_id: "abc" } → Backend
   Backend → Verify PIN → Update DB (mark windows as "low") → Return success
   Frontend → Refresh session state → Hide MFA modal
   ```

---

## 🧪 Testing the MFA Feature

### Manual Test Flow

1. **Sign up a new user:**
   - Go to http://localhost:5173
   - Click "Sign Up"
   - Enter username and password
   - **Save the 4-digit PIN shown** (e.g., "1234")
   - Log in with the credentials

2. **Complete enrollment:**
   - Type the passage 2-3 times
   - Click "Register Keystroke Signature"
   - Wait for training to complete

3. **Start a session:**
   - Type normally in the text area
   - Observe "SECURE" status badge

4. **Trigger MFA challenge:**
   - Click "Demo: Synthetic Attack" button
   - System will inject anomalous typing patterns
   - After 2 consecutive warnings, MFA modal appears

5. **Verify identity:**
   - Enter the 4-digit PIN from step 1
   - Click "Confirm Identity"
   - If correct: Modal dismisses, session continues
   - If incorrect: Error message, try again

6. **Session termination:**
   - If you don't verify (or enter wrong PIN) and 3rd warning occurs
   - Session locks with "Security Incident Logged" screen

---

## 🐛 Common Issues & Solutions

### Issue 1: "Invalid verification code" even with correct PIN
**Cause:** PIN not stored in localStorage  
**Solution:** 
- Log out and log back in
- Check browser console: `localStorage.getItem('mfaPin')`
- Ensure backend returned `mfa_pin` in login response

### Issue 2: MFA challenge never appears
**Cause:** Backend not returning `action_required` field  
**Solution:**
- Check backend logs for errors
- Verify `/session/score` returns `action_required: "PROMPT_MFA_CHALLENGE"`
- Ensure 2 consecutive medium/high windows exist

### Issue 3: Session terminates immediately without MFA
**Cause:** 3 consecutive warnings happen too fast  
**Solution:**
- This is expected behavior if user doesn't respond to MFA challenge
- Legitimate user should see MFA prompt at 2 warnings

### Issue 4: MFA modal disappears but status still shows warnings
**Cause:** Frontend state not refreshing after verification  
**Solution:**
- Backend should update window risk levels to "low"
- Frontend should call `fetchSessionScore()` after verification
- Check browser console for API errors

---

## 🔒 Security Considerations

### ✅ Security Strengths
1. **Two-factor authentication:** Combines keystroke biometrics + PIN
2. **Adaptive response:** Doesn't immediately lock out on first anomaly
3. **Backend validation:** PIN verified server-side, not client-side
4. **Audit trail:** MFA verifications logged in database

### ⚠️ Security Limitations
1. **PIN storage:** Stored in plain text in MongoDB (consider hashing)
2. **LocalStorage:** PIN accessible to JavaScript (consider httpOnly cookies)
3. **No rate limiting:** Unlimited PIN attempts (add after 3 failures)
4. **Static PIN:** Same PIN forever (consider rotation or TOTP)

### 🛡️ Recommended Improvements
1. Hash MFA PIN using bcrypt before storing
2. Add rate limiting: 3 failed attempts → lock account for 15 minutes
3. Implement PIN expiration: Force rotation every 90 days
4. Consider TOTP (Google Authenticator) instead of static PIN
5. Add email/SMS notification when MFA is triggered

---

## 📝 Configuration

### Adjusting MFA Sensitivity

**Current settings:**
- MFA trigger: 2 consecutive medium/high windows
- Session termination: 3 consecutive medium/high windows

**To make more lenient (fewer false positives):**
```python
# In /session/score endpoint
if consecutive_hijack_count == 3:  # Change from 2 to 3
    action_required = "PROMPT_MFA_CHALLENGE"

if consecutive_hijack_count >= 4:  # Change from 3 to 4
    action_required = "TERMINATE_SESSION"
```

**To make more strict (better security):**
```python
if consecutive_hijack_count == 1:  # Change from 2 to 1
    action_required = "PROMPT_MFA_CHALLENGE"

if consecutive_hijack_count >= 2:  # Change from 3 to 2
    action_required = "TERMINATE_SESSION"
```

---

## ✅ Verification Checklist

- [x] Backend generates random 4-digit PIN on signup
- [x] PIN stored in user document
- [x] PIN returned in login response
- [x] Frontend stores PIN in localStorage
- [x] Backend tracks consecutive risk windows
- [x] `/session/score` returns `action_required` field
- [x] MFA modal appears at 2 consecutive warnings
- [x] PIN verification endpoint (`/session/verify_mfa`)
- [x] Successful verification resets consecutive counter
- [x] Failed verification shows error message
- [x] Session terminates at 3+ consecutive warnings
- [x] Lockout screen displays on termination

---

## 🎯 Summary

The MFA challenge feature adds an intelligent security layer that:

1. **Doesn't immediately lock out** on first anomaly detection
2. **Gives legitimate users a chance** to verify identity with PIN
3. **Prevents false positives** from fatigue, injury, or environmental factors
4. **Still locks out attackers** who can't provide the PIN

**Perfect for:**
- Users who occasionally type differently (tired, different keyboard, etc.)
- High-security applications where both biometrics + knowledge factor are required
- Reducing user frustration from false positive lockouts

**User Experience:**
```
Normal typing → Everything works seamlessly
Typing variation → Get a second chance with PIN
Sustained anomaly → Locked out for security
```

---

**Implementation Status:** ✅ **FULLY IMPLEMENTED AND TESTED**  
**Last Updated:** January 2025  
**Compatible with:** Continuous Keystroke Authentication v1.0
