"""
Schema for app DB: SQLite (data/app_data.db) or Supabase PostgreSQL (when DATABASE_URL is set).
Tables: team, player, stamem, game, play_data.
"""
import os
import re
import sqlite3
from typing import Any, Optional, Union

# Load .env so DATABASE_URL is available (from project root so cwd-independent)
try:
    from dotenv import load_dotenv
    _project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    load_dotenv(os.path.join(_project_root, '.env'))
except ImportError:
    pass

DB_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'app_data.db')

def _resolve_database_url() -> Optional[str]:
    url = os.environ.get('DATABASE_URL')
    if url:
        return url
    try:
        import streamlit as _st
        return _st.secrets.get("DATABASE_URL")
    except Exception:
        return None

def _get_database_url() -> Optional[str]:
    """毎回 DATABASE_URL を解決する（Streamlit Cloud では secrets の初期化タイミングが遅い場合があるため）"""
    return _resolve_database_url()


def is_postgres() -> bool:
    """True if using Supabase/PostgreSQL (DATABASE_URL set)."""
    url = _get_database_url()
    return url is not None and url.strip() != ''


# PostgreSQL: quote identifiers that are quoted in supabase_schema (unquoted are lowercased)
_PG_QUOTE_COLS = (
    'Season', 'Kind', 'Week', 'Day', 'GameNumber', 'Result_col', 'S', 'B',
    '試合日時', '回', 'コースX', 'コースY', '名前', 'チーム_id',
)


class _PgCursorWrapper:
    """Cursor wrapper: ? → %s, lastrowid via lastval(), quote mixed-case identifiers."""
    def __init__(self, conn: Any, real_cursor: Any):
        self._conn = conn
        self._cur = real_cursor
        self._lastrowid: Optional[int] = None

    def execute(self, sql: str, params: Optional[tuple] = None) -> None:
        if params is None:
            params = ()
        pg_sql = sql
        for col in _PG_QUOTE_COLS:
            pg_sql = re.sub(r'\b' + re.escape(col) + r'\b', '"' + col + '"', pg_sql)
        pg_sql = pg_sql.replace('?', '%s')
        self._cur.execute(pg_sql, params)
        sql_upper = sql.strip().upper()
        if sql_upper.startswith('INSERT'):
            try:
                self._cur.execute('SAVEPOINT _lastval_sp')
                self._cur.execute('SELECT lastval()')
                row = self._cur.fetchone()
                self._lastrowid = int(row[0]) if row and row[0] is not None else None
                self._cur.execute('RELEASE SAVEPOINT _lastval_sp')
            except Exception:
                self._cur.execute('ROLLBACK TO SAVEPOINT _lastval_sp')
                self._cur.execute('RELEASE SAVEPOINT _lastval_sp')
                self._lastrowid = None
        else:
            self._lastrowid = None

    def fetchone(self) -> Optional[tuple]:
        return self._cur.fetchone()

    def fetchall(self) -> list:
        return self._cur.fetchall()

    @property
    def rowcount(self) -> int:
        return self._cur.rowcount

    @property
    def lastrowid(self) -> Optional[int]:
        return self._lastrowid


class _PgConnWrapper:
    """Connection wrapper that returns cursor wrappers."""
    def __init__(self, conn: Any):
        self._conn = conn

    def cursor(self) -> _PgCursorWrapper:
        return _PgCursorWrapper(self._conn, self._conn.cursor())

    def commit(self) -> None:
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()


def get_conn() -> Union[sqlite3.Connection, _PgConnWrapper]:
    """Return a connection to the app database (SQLite or Supabase PostgreSQL)."""
    if is_postgres():
        import psycopg2
        conn = psycopg2.connect(_get_database_url())
        return _PgConnWrapper(conn)
    return sqlite3.connect(DB_FILE)


def init_db() -> None:
    """Create all tables if they do not exist (SQLite only). For PostgreSQL, run db/supabase_schema.sql once in Supabase."""
    if is_postgres():
        return
    conn = get_conn()
    assert isinstance(conn, sqlite3.Connection)
    c = conn.cursor()

    # チーム（大学・チームマスタ）
    c.execute('''
        CREATE TABLE IF NOT EXISTS team (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            名前 TEXT UNIQUE NOT NULL
        )
    ''')

    # 選手（アプリで登録）
    c.execute('''
        CREATE TABLE IF NOT EXISTS player (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            チーム_id INTEGER NOT NULL REFERENCES team(id),
            背番号 TEXT NOT NULL,
            名前 TEXT NOT NULL,
            左右 TEXT NOT NULL,
            UNIQUE(チーム_id, 背番号)
        )
    ''')

    # スタメン（大学ごとのスタメン記憶。旧 member_remember 相当）
    c.execute('''
        CREATE TABLE IF NOT EXISTS stamem (
            チーム_id INTEGER PRIMARY KEY REFERENCES team(id),
            poses TEXT NOT NULL,
            names TEXT NOT NULL,
            nums TEXT NOT NULL,
            lrs TEXT NOT NULL
        )
    ''')

    # 試合一覧
    c.execute('''
        CREATE TABLE IF NOT EXISTS game (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            試合日時 TEXT NOT NULL,
            Season TEXT,
            Kind TEXT,
            Week TEXT,
            Day TEXT,
            GameNumber TEXT,
            主審 TEXT,
            先攻チーム_id INTEGER NOT NULL REFERENCES team(id),
            後攻チーム_id INTEGER NOT NULL REFERENCES team(id),
            開始時刻 TEXT,
            現在時刻 TEXT,
            経過時間 TEXT,
            created_at TEXT
        )
    ''')

    # データ（毎球 1 プレイ = 1 行）。column_names に相当する列を保存（リスト系は JSON 文字列）
    data_columns = [
        'id INTEGER PRIMARY KEY AUTOINCREMENT',
        '試合_id INTEGER NOT NULL REFERENCES game(id)',
        '試合日時 TEXT', 'Season TEXT', 'Kind TEXT', 'Week TEXT', 'Day TEXT', 'GameNumber TEXT',
        '主審 TEXT', '後攻チーム TEXT', '先攻チーム TEXT', 'プレイの番号 INTEGER', '回 INTEGER', '表裏 TEXT',
        '先攻得点 INTEGER', '後攻得点 INTEGER', 'S INTEGER', 'B INTEGER', 'アウト INTEGER',
        '打席の継続 TEXT', 'イニング継続 TEXT', '試合継続 TEXT',
        '一走打順 INTEGER', '一走氏名 TEXT', '二走打順 INTEGER', '二走氏名 TEXT', '三走打順 INTEGER', '三走氏名 TEXT',
        '打順 INTEGER', '打者氏名 TEXT', '打席左右 TEXT', '作戦 TEXT', '作戦2 TEXT', '作戦結果 TEXT',
        '投手氏名 TEXT', '投手左右 TEXT', '球数 INTEGER', '捕手 TEXT',
        '一走状況 TEXT', '二走状況 TEXT', '三走状況 TEXT', '打者状況 TEXT', 'プレイの種類 TEXT', '構え TEXT',
        'コースX REAL', 'コースY REAL', '球種 TEXT',
        '打撃結果 TEXT', '打撃結果2 TEXT', '捕球選手 TEXT', '打球タイプ TEXT', '打球強度 TEXT',
        '打球位置X REAL', '打球位置Y REAL', '牽制の種類 TEXT', '牽制詳細 TEXT',
        'エラーの種類 TEXT', 'タイムの種類 TEXT', '球速 REAL', 'プレス TEXT', '偽走 TEXT', '打者位置 TEXT',
        '打席Id TEXT', '打席結果 TEXT', 'Result_col TEXT', '打者登録名 TEXT',
        '打者番号 TEXT', '一走登録名 TEXT', '一走番号 TEXT', '二走登録名 TEXT', '二走番号 TEXT',
        '三走登録名 TEXT', '三走番号 TEXT', '投手番号 TEXT', '入力項目 TEXT',
        '先攻打順 TEXT', '後攻打順 TEXT', '経過時間 TEXT', '開始時刻 TEXT', '現在時刻 TEXT',
        'top_poses TEXT', 'top_names TEXT', 'top_nums TEXT', 'top_lrs TEXT',
        'bottom_poses TEXT', 'bottom_names TEXT', 'bottom_nums TEXT', 'bottom_lrs TEXT',
        'top_score TEXT', 'bottom_score TEXT'
    ]
    c.execute('CREATE TABLE IF NOT EXISTS play_data (\n  ' + ',\n  '.join(data_columns) + '\n)')

    conn.commit()
    conn.close()
