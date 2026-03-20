"""投手コメント CRUD"""
from .schema import get_conn, is_postgres, migrate_add_comment_table


def _ensure_table() -> None:
    """テーブルが存在しない場合はマイグレーションを実行する。"""
    migrate_add_comment_table()


def get_comment( team_id: int, pitcher_name: str ) -> str:
    try:
        conn = get_conn()
        c    = conn.cursor()
        c.execute(
            'SELECT comment FROM pitcher_comment WHERE team_id = ? AND pitcher_name = ?',
            ( team_id, pitcher_name ),
        )
        row = c.fetchone()
        conn.close()
        return row[0] if row else ''
    except Exception:
        _ensure_table()
        return ''


def upsert_comment( team_id: int, pitcher_name: str, comment: str ) -> None:
    _ensure_table()
    conn = get_conn()
    c    = conn.cursor()
    if is_postgres():
        c.execute(
            '''
            INSERT INTO pitcher_comment (team_id, pitcher_name, comment)
            VALUES (%s, %s, %s)
            ON CONFLICT (team_id, pitcher_name)
            DO UPDATE SET comment = EXCLUDED.comment
            ''',
            ( team_id, pitcher_name, comment ),
        )
    else:
        c.execute(
            '''
            INSERT INTO pitcher_comment (team_id, pitcher_name, comment)
            VALUES (?, ?, ?)
            ON CONFLICT (team_id, pitcher_name)
            DO UPDATE SET comment = excluded.comment
            ''',
            ( team_id, pitcher_name, comment ),
        )
    conn.commit()
    conn.close()
