"""打者コメント CRUD"""
from .schema import get_conn, is_postgres


def _ensure_table() -> None:
    from .schema import migrate_add_batter_comment_table
    migrate_add_batter_comment_table()


def get_comment( team_id: int, batter_name: str ) -> str:
    try:
        conn = get_conn()
        c    = conn.cursor()
        c.execute(
            'SELECT comment FROM batter_comment WHERE team_id = ? AND batter_name = ?',
            ( team_id, batter_name ),
        )
        row = c.fetchone()
        conn.close()
        return row[0] if row else ''
    except Exception:
        _ensure_table()
        return ''


def upsert_comment( team_id: int, batter_name: str, comment: str ) -> None:
    _ensure_table()
    conn = get_conn()
    c    = conn.cursor()
    if is_postgres():
        c.execute(
            '''
            INSERT INTO batter_comment (team_id, batter_name, comment)
            VALUES (%s, %s, %s)
            ON CONFLICT (team_id, batter_name)
            DO UPDATE SET comment = EXCLUDED.comment
            ''',
            ( team_id, batter_name, comment ),
        )
    else:
        c.execute(
            '''
            INSERT INTO batter_comment (team_id, batter_name, comment)
            VALUES (?, ?, ?)
            ON CONFLICT (team_id, batter_name)
            DO UPDATE SET comment = excluded.comment
            ''',
            ( team_id, batter_name, comment ),
        )
    conn.commit()
    conn.close()
