import bcrypt
import secrets
from datetime import datetime, timedelta
from backend.db import db

sessions_col = db["sessions"]

def hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')

def verify_password(password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode('utf-8'), hashed_password.encode('utf-8'))
    except Exception:
        return False

def hash_pin(pin: str) -> str:
    """Hash MFA PIN using bcrypt (same as password hashing)."""
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(pin.encode('utf-8'), salt)
    return hashed.decode('utf-8')

def verify_pin(pin: str, hashed_pin: str) -> bool:
    """Verify MFA PIN against bcrypt hash."""
    try:
        return bcrypt.checkpw(pin.encode('utf-8'), hashed_pin.encode('utf-8'))
    except Exception:
        return False

def create_session(user_id: str) -> str:
    token = secrets.token_hex(32)
    # Session expires in 24 hours
    expires_at = datetime.utcnow() + timedelta(hours=24)
    sessions_col.insert_one({
        "token": token,
        "user_id": user_id,
        "expires_at": expires_at
    })
    return token

def get_user_id_from_token(token: str) -> str:
    session = sessions_col.find_one({"token": token})
    if session:
        if session["expires_at"] > datetime.utcnow():
            return session["user_id"]
        else:
            # Clean up expired session
            sessions_col.delete_one({"token": token})
    return None

def delete_session(token: str):
    sessions_col.delete_one({"token": token})
