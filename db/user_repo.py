"""
DB operations for user accounts.
"""
from datetime import datetime
from typing import List, Optional, Tuple

from . import schema


def create_user(username: str, password_hash: str, team_id: int) -> int:
    """Create a new user and return user id."""
    conn = schema.get_conn()
    c = conn.cursor()
    c.execute(
        'INSERT INTO user_account (username, password_hash, team_id, created_at) VALUES (?, ?, ?, ?)',
        (username.strip(), password_hash, team_id, datetime.now().isoformat())
    )
    uid = c.lastrowid
    conn.commit()
    conn.close()
    return uid


def get_user_by_username(username: str) -> Optional[Tuple]:
    """Return (id, username, password_hash, team_id) or None."""
    conn = schema.get_conn()
    c = conn.cursor()
    c.execute(
        'SELECT id, username, password_hash, team_id FROM user_account WHERE username = ?',
        (username.strip(),)
    )
    row = c.fetchone()
    conn.close()
    return row


def username_exists(username: str) -> bool:
    return get_user_by_username(username) is not None


def list_users_by_team(team_id: int) -> List[Tuple]:
    """Return list of (id, username, created_at) for the team."""
    conn = schema.get_conn()
    c = conn.cursor()
    c.execute(
        'SELECT id, username, created_at FROM user_account WHERE team_id = ? ORDER BY username',
        (team_id,)
    )
    rows = c.fetchall()
    conn.close()
    return rows


def delete_user(user_id: int) -> None:
    conn = schema.get_conn()
    c = conn.cursor()
    c.execute('DELETE FROM user_account WHERE id = ?', (user_id,))
    conn.commit()
    conn.close()


def update_password(user_id: int, password_hash: str) -> None:
    conn = schema.get_conn()
    c = conn.cursor()
    c.execute('UPDATE user_account SET password_hash = ? WHERE id = ?', (password_hash, user_id))
    conn.commit()
    conn.close()
