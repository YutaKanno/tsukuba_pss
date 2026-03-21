"""
Schema for app DB: SQLite (data/app_data.db) or Supabase PostgreSQL (when DATABASE_URL is set).
Tables: team, player, stamem, game, play_data.
"""
import os
import re
import sqlite3
from typing import Any, Optional, Union

import streamlit as st

# Load .env so DATABASE_URL is available (from project root so cwd-independent)
try:
    from dotenv import load_dotenv
    _project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    load_dotenv(os.path.join(_project_root, '.env'))
except ImportError:
    import warnings
    warnings.warn( "python-dotenv が未インストールのため DATABASE_URL が読み込まれません。pip install python-dotenv を実行してください。" )

DB_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'app_data.db')

def _resolve_database_url() -> Optional[str]:
    from urllib.parse import urlparse, urlunparse
    url = os.environ.get('DATABASE_URL')
    if not url:
        try:
            import streamlit as _st
            url = _st.secrets.get("DATABASE_URL")
        except Exception:
            pass
    if not url:
        return None
    url = url.strip()
    # Render等で誤って "DATABASE_URL=postgresql://..." と値に含めた場合の対処
    if url.upper().startswith('DATABASE_URL='):
        url = url[len('DATABASE_URL='):]
    # postgres:// → postgresql:// (Heroku/Render互換)
    if url.startswith('postgres://'):
        url = 'postgresql://' + url[len('postgres://'):]
    # URLをパースしてDB名(path)の余分なスペースを除去
    try:
        parsed = urlparse(url)
        clean_path = parsed.path.strip()
        url = urlunparse(parsed._replace(path=clean_path))
    except Exception:
        pass
    return url or None

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
    def __init__(self, conn: Any, pool: Any = None):
        self._conn = conn
        self._pool = pool

    def cursor(self) -> _PgCursorWrapper:
        return _PgCursorWrapper(self._conn, self._conn.cursor())

    def commit(self) -> None:
        self._conn.commit()

    def rollback(self) -> None:
        try:
            self._conn.rollback()
        except Exception:
            pass

    def close(self) -> None:
        if self._pool is not None:
            # プールに戻す前にロールバックして接続を清潔な状態にする
            try:
                self._conn.rollback()
            except Exception:
                pass
            try:
                self._pool.putconn(self._conn)
            except Exception:
                try:
                    self._conn.close()
                except Exception:
                    pass
        else:
            self._conn.close()


@st.cache_resource(show_spinner=False)
def _get_pg_pool():
    """PostgreSQL接続プールをキャッシュして使い回す（接続コストを削減）。"""
    import psycopg2.pool
    url = _get_database_url()
    return psycopg2.pool.SimpleConnectionPool(1, 3, url)


def get_conn() -> Union[sqlite3.Connection, _PgConnWrapper]:
    """Return a connection to the app database (SQLite or Supabase PostgreSQL)."""
    if is_postgres():
        import psycopg2

        def _get_valid_conn(pool):
            """プールから接続を取得し、生存確認（reset）する。失敗したら例外を上げる。"""
            conn = pool.getconn()
            # closed != 0 は psycopg2 レベルで既に切断済み
            if getattr(conn, 'closed', 0) != 0:
                try:
                    pool.putconn(conn, close=True)
                except Exception:
                    pass
                raise psycopg2.OperationalError("stale connection (closed)")
            try:
                # reset() はペンディング中のトランザクションをロールバックし、
                # ネットワーク切断があれば OperationalError を上げる
                conn.reset()
            except Exception:
                try:
                    pool.putconn(conn, close=True)
                except Exception:
                    pass
                raise
            conn.autocommit = False
            return _PgConnWrapper(conn, pool)

        try:
            pool = _get_pg_pool()
            return _get_valid_conn(pool)
        except Exception:
            # プールが枯渇・接続が切断された場合はキャッシュをクリアして新しいプールで再試行
            _get_pg_pool.clear()
            pool = _get_pg_pool()
            return _get_valid_conn(pool)
    return sqlite3.connect(DB_FILE)


def migrate_add_user_account() -> None:
    """Create user_account table if it doesn't exist (SQLite & PostgreSQL)."""
    conn = get_conn()
    c = conn.cursor()
    try:
        if is_postgres():
            c.execute('''
                CREATE TABLE IF NOT EXISTS user_account (
                    id SERIAL PRIMARY KEY,
                    username TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    team_id INTEGER NOT NULL REFERENCES team(id),
                    created_at TEXT
                )
            ''')
        else:
            c.execute('''
                CREATE TABLE IF NOT EXISTS user_account (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    team_id INTEGER NOT NULL REFERENCES team(id),
                    created_at TEXT
                )
            ''')
        conn.commit()
    except Exception:
        pass
    finally:
        conn.close()


def migrate_add_team_password() -> None:
    """Add password_hash column to team table if missing (SQLite & PostgreSQL)."""
    conn = get_conn()
    c = conn.cursor()
    try:
        if is_postgres():
            c.execute("ALTER TABLE team ADD COLUMN IF NOT EXISTS password_hash TEXT")
        else:
            c.execute("PRAGMA table_info(team)")
            cols = [row[1] for row in c.fetchall()]
            if "password_hash" not in cols:
                c.execute("ALTER TABLE team ADD COLUMN password_hash TEXT")
        conn.commit()
    except Exception:
        pass
    finally:
        conn.close()


def migrate_add_game_owner() -> None:
    """Add owner_team_id column to game table if missing."""
    conn = get_conn()
    c = conn.cursor()
    try:
        if is_postgres():
            c.execute("ALTER TABLE game ADD COLUMN IF NOT EXISTS owner_team_id INTEGER REFERENCES team(id)")
        else:
            c.execute("PRAGMA table_info(game)")
            cols = [row[1] for row in c.fetchall()]
            if "owner_team_id" not in cols:
                c.execute("ALTER TABLE game ADD COLUMN owner_team_id INTEGER REFERENCES team(id)")
        conn.commit()
    except Exception:
        pass
    finally:
        conn.close()


def migrate_associate_existing_games(team_name: str) -> int:
    """owner_team_id が未設定の既存ゲームを指定チームに紐づける。登録件数を返す。"""
    from . import player_repo as _pr
    team_id = _pr.ensure_team(team_name)
    conn = get_conn()
    c = conn.cursor()
    c.execute("UPDATE game SET owner_team_id = ? WHERE owner_team_id IS NULL", (team_id,))
    count = c.rowcount if c.rowcount and c.rowcount > 0 else 0
    conn.commit()
    conn.close()
    return count


def migrate_reassociate_games_by_team(team_name: str) -> int:
    """先攻または後攻が team_name のゲームを、そのチームのオーナーに再紐づけする。登録件数を返す。"""
    from . import player_repo as _pr
    team_id = _pr.get_team_id_by_name(team_name)
    if team_id is None:
        return 0
    conn = get_conn()
    c = conn.cursor()
    c.execute(
        "UPDATE game SET owner_team_id = ? "
        "WHERE (先攻チーム_id = ? OR 後攻チーム_id = ?)",
        (team_id, team_id, team_id),
    )
    count = c.rowcount if c.rowcount and c.rowcount > 0 else 0
    conn.commit()
    conn.close()
    return count


def migrate_add_comment_table() -> None:
    """Create pitcher_comment table if it doesn't exist (SQLite & PostgreSQL)."""
    conn = get_conn()
    c = conn.cursor()
    try:
        if is_postgres():
            c.execute('''
                CREATE TABLE IF NOT EXISTS pitcher_comment (
                    id SERIAL PRIMARY KEY,
                    team_id INTEGER NOT NULL REFERENCES team(id),
                    pitcher_name TEXT NOT NULL,
                    comment TEXT NOT NULL DEFAULT '',
                    UNIQUE(team_id, pitcher_name)
                )
            ''')
        else:
            c.execute('''
                CREATE TABLE IF NOT EXISTS pitcher_comment (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    team_id INTEGER NOT NULL REFERENCES team(id),
                    pitcher_name TEXT NOT NULL,
                    comment TEXT NOT NULL DEFAULT '',
                    UNIQUE(team_id, pitcher_name)
                )
            ''')
        conn.commit()
    except Exception:
        pass
    finally:
        conn.close()


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
            owner_team_id INTEGER REFERENCES team(id),
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

    # ユーザーアカウント（ユーザー名・パスワード・所属チーム）
    c.execute('''
        CREATE TABLE IF NOT EXISTS user_account (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            team_id INTEGER NOT NULL REFERENCES team(id),
            created_at TEXT
        )
    ''')

    # 投手コメント
    c.execute('''
        CREATE TABLE IF NOT EXISTS pitcher_comment (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            team_id INTEGER NOT NULL REFERENCES team(id),
            pitcher_name TEXT NOT NULL,
            comment TEXT NOT NULL DEFAULT '',
            UNIQUE(team_id, pitcher_name)
        )
    ''')

    conn.commit()
    conn.close()
