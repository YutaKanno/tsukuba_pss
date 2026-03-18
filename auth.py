"""
JWT token creation/verification and bcrypt password utilities.
"""
import datetime
import os
from typing import Optional

COOKIE_NAME = "tsukuba_pss_auth"
TOKEN_DAYS  = 30


def _secret() -> str:
    try:
        import streamlit as st
        s = st.secrets.get("JWT_SECRET_KEY")
        if s:
            return str(s)
    except Exception:
        pass
    return os.environ.get("JWT_SECRET_KEY", "tsukuba-pss-default-change-me")


def hash_password(password: str) -> str:
    import bcrypt
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def check_password(password: str, hashed: str) -> bool:
    import bcrypt
    try:
        return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return False


def create_token(team_id: int, team_name: str,
                 user_id: Optional[int] = None, username: Optional[str] = None) -> str:
    import jwt
    payload = {
        "team_id":   team_id,
        "team_name": team_name,
        "exp": datetime.datetime.utcnow() + datetime.timedelta(days=TOKEN_DAYS),
    }
    if user_id is not None:
        payload["user_id"] = user_id
    if username is not None:
        payload["username"] = username
    return jwt.encode(payload, _secret(), algorithm="HS256")


def verify_token(token: str) -> Optional[dict]:
    """Return payload dict if valid and not expired, else None."""
    import jwt
    try:
        return jwt.decode(token, _secret(), algorithms=["HS256"])
    except Exception:
        return None
