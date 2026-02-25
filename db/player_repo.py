"""
DB operations for team, player, and stamem (lineup).
"""
import json
import sqlite3
from typing import List, Optional, Tuple

from . import schema


def ensure_team(名前: str) -> int:
    """Ensure team exists by name; return team id."""
    schema.init_db()
    conn = schema.get_conn()
    c = conn.cursor()
    c.execute('SELECT id FROM team WHERE 名前 = ?', (名前,))
    row = c.fetchone()
    if row:
        conn.close()
        return row[0]
    c.execute('INSERT INTO team (名前) VALUES (?)', (名前,))
    tid = c.lastrowid
    conn.commit()
    conn.close()
    return tid


def list_teams() -> List[Tuple[int, str]]:
    """Return all teams as list of (id, name)."""
    schema.init_db()
    conn = schema.get_conn()
    c = conn.cursor()
    c.execute('SELECT id, 名前 FROM team ORDER BY 名前')
    rows = c.fetchall()
    conn.close()
    return rows


def get_team_id_by_name(名前: str) -> Optional[int]:
    """Return team id by name, or None."""
    conn = schema.get_conn()
    c = conn.cursor()
    c.execute('SELECT id FROM team WHERE 名前 = ?', (名前,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else None


def get_player_by_number(チーム_id: int, 背番号: str) -> Optional[Tuple[str, str]]:
    """Return (name, lr) for the player with given team id and number, or None."""
    conn = schema.get_conn()
    c = conn.cursor()
    c.execute(
        'SELECT 名前, 左右 FROM player WHERE チーム_id = ? AND 背番号 = ?',
        (チーム_id, str(背番号).strip())
    )
    row = c.fetchone()
    conn.close()
    return row if row else None


def delete_player(チーム_id: int, 背番号: str) -> None:
    """Delete one player by team id and jersey number."""
    conn = schema.get_conn()
    c = conn.cursor()
    c.execute('DELETE FROM player WHERE チーム_id = ? AND 背番号 = ?', (チーム_id, str(背番号).strip()))
    conn.commit()
    conn.close()


def add_player(チーム_id: int, 背番号: str, 名前: str, 左右: str) -> None:
    """Insert one player."""
    schema.init_db()
    conn = schema.get_conn()
    c = conn.cursor()
    c.execute(
        'INSERT INTO player (チーム_id, 背番号, 名前, 左右) VALUES (?, ?, ?, ?)',
        (チーム_id, str(背番号).strip(), 名前.strip(), 左右)
    )
    conn.commit()
    conn.close()


def add_players_bulk(チーム_id: int, rows: List[Tuple[str, str, str]]) -> int:
    """Bulk insert players; (team_id, number) duplicates are ignored. Return count inserted."""
    if not rows:
        return 0
    schema.init_db()
    conn = schema.get_conn()
    c = conn.cursor()
    n = 0
    if schema.is_postgres():
        for 背番号, 名前, 左右 in rows:
            c.execute(
                'INSERT INTO player (チーム_id, 背番号, 名前, 左右) VALUES (?, ?, ?, ?) '
                'ON CONFLICT (チーム_id, 背番号) DO NOTHING',
                (チーム_id, str(背番号).strip(), 名前.strip(), 左右)
            )
            if c.rowcount and c.rowcount > 0:
                n += 1
    else:
        for 背番号, 名前, 左右 in rows:
            try:
                c.execute(
                    'INSERT OR IGNORE INTO player (チーム_id, 背番号, 名前, 左右) VALUES (?, ?, ?, ?)',
                    (チーム_id, str(背番号).strip(), 名前.strip(), 左右)
                )
                if c.rowcount > 0:
                    n += 1
            except Exception:
                pass
    conn.commit()
    conn.close()
    return n


def get_players_by_team(チーム_id: int) -> List[Tuple[str, str, str]]:
    """Return list of (number, name, lr) for the given team."""
    conn = schema.get_conn()
    c = conn.cursor()
    c.execute(
        'SELECT 背番号, 名前, 左右 FROM player WHERE チーム_id = ? ORDER BY CAST(背番号 AS INTEGER), 背番号',
        (チーム_id,)
    )
    rows = c.fetchall()
    conn.close()
    return rows


def get_member_df_equivalent(チーム名: str) -> List[dict]:
    """Return member_df-style list of dicts for the team (keys: 大学名, 背番号, 名前, 左右)."""
    tid = get_team_id_by_name(チーム名)
    if not tid:
        return []
    rows = get_players_by_team(tid)
    return [
        {'大学名': チーム名, '背番号': r[0], '名前': r[1], '左右': r[2]}
        for r in rows
    ]


def get_stamem(チーム_id: int) -> Optional[dict]:
    """Return lineup dict (poses, names, nums, lrs) for the team, or None."""
    conn = schema.get_conn()
    c = conn.cursor()
    c.execute('SELECT poses, names, nums, lrs FROM stamem WHERE チーム_id = ?', (チーム_id,))
    row = c.fetchone()
    conn.close()
    if not row:
        return None
    return {
        'poses': json.loads(row[0]),
        'names': json.loads(row[1]),
        'nums': json.loads(row[2]),
        'lrs': json.loads(row[3]),
    }


def get_stamem_by_team_name(チーム名: str) -> Optional[dict]:
    """Return lineup dict for the team by name, or None."""
    tid = get_team_id_by_name(チーム名)
    if not tid:
        return None
    return get_stamem(tid)


def save_stamem(チーム_id: int, poses: list, names: list, nums: list, lrs: list) -> None:
    """Save lineup for the team."""
    schema.init_db()
    conn = schema.get_conn()
    c = conn.cursor()
    try:
        if schema.is_postgres():
            try:
                c.execute('SELECT 1 FROM stamem LIMIT 1')
            except Exception as e:
                err = str(e).lower()
                if 'stamem' in err and ('does not exist' in err or 'not exist' in err or 'undefined_table' in err):
                    raise RuntimeError(
                        'stamem テーブルが Supabase に存在しません。'
                        ' Supabase の SQL エディタで db/supabase_schema.sql を実行してテーブルを作成してください。'
                    ) from e
            c.execute('''
                INSERT INTO stamem (チーム_id, poses, names, nums, lrs)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT (チーム_id) DO UPDATE SET
                    poses = EXCLUDED.poses,
                    names = EXCLUDED.names,
                    nums = EXCLUDED.nums,
                    lrs = EXCLUDED.lrs
            ''', (チーム_id, json.dumps(poses), json.dumps(names), json.dumps(nums), json.dumps(lrs)))
        else:
            c.execute('''
                INSERT OR REPLACE INTO stamem (チーム_id, poses, names, nums, lrs)
                VALUES (?, ?, ?, ?, ?)
            ''', (チーム_id, json.dumps(poses), json.dumps(names), json.dumps(nums), json.dumps(lrs)))
        conn.commit()
    finally:
        conn.close()


def save_stamem_by_team_name(チーム名: str, poses: list, names: list, nums: list, lrs: list) -> None:
    """Save lineup by team name; ensure team exists first."""
    チーム名 = str(チーム名 or "").strip()
    tid = ensure_team(チーム名)
    save_stamem(tid, poses, names, nums, lrs)


def migrate_member_remember(old_db_path: str = None) -> None:
    """Migrate member_remember from old DB to app_data.db team + stamem."""
    import os
    if old_db_path is None:
        old_db_path = os.path.join( os.path.dirname( os.path.dirname( __file__ ) ), 'data', 'member_data.db' )
    if not os.path.exists( old_db_path ):
        return
    old = sqlite3.connect(old_db_path)
    schema.init_db()
    conn = schema.get_conn()
    c = conn.cursor()
    for row in old.execute('SELECT 大学名, poses, names, nums, lrs FROM member_remember'):
        大学名, poses, names, nums, lrs = row[0], row[1], row[2], row[3], row[4]
        c.execute('SELECT id FROM team WHERE 名前 = ?', (大学名,))
        t = c.fetchone()
        if not t:
            c.execute('INSERT INTO team (名前) VALUES (?)', (大学名,))
            tid = c.lastrowid
        else:
            tid = t[0]
        if schema.is_postgres():
            c.execute(
                'INSERT INTO stamem (チーム_id, poses, names, nums, lrs) VALUES (?, ?, ?, ?, ?) '
                'ON CONFLICT (チーム_id) DO UPDATE SET poses = EXCLUDED.poses, names = EXCLUDED.names, '
                'nums = EXCLUDED.nums, lrs = EXCLUDED.lrs',
                (tid, poses, names, nums, lrs)
            )
        else:
            c.execute('INSERT OR REPLACE INTO stamem (チーム_id, poses, names, nums, lrs) VALUES (?, ?, ?, ?, ?)',
                      (tid, poses, names, nums, lrs))
    conn.commit()
    conn.close()
    old.close()
