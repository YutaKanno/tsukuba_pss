"""
DB operations for game and per-play data.
"""
import json
import os
import sqlite3
import time
from datetime import datetime
from typing import Any, List, Optional, Tuple

from . import schema


def _get_game_json_path( game_id: int ) -> str:
    data_dir = os.path.dirname( schema.DB_FILE )
    return os.path.join( data_dir, f'game_{game_id}.json' )


def _update_game_json_plays( game_id: int, row_list: list ) -> None:
    path = _get_game_json_path( game_id )
    if not os.path.exists( path ):
        return
    try:
        with open( path, 'r', encoding = 'utf-8' ) as f:
            data = json.load( f )
        data.setdefault( 'plays', [] ).append( row_list )
        with open( path, 'w', encoding = 'utf-8' ) as f:
            json.dump( data, f, ensure_ascii = False, indent = 2 )
    except Exception:
        pass


def _row_to_db(game_id: int, row_list: list) -> dict:
    """Convert one all_list row (88 elements) to play_data dict."""
    def v(i, default=None):
        if i >= len(row_list):
            return default
        x = row_list[i]
        return x if x is not None and x != '' else default

    def json_or_val(i):
        x = v(i)
        if x is None:
            return None
        if isinstance(x, (list, dict)):
            return json.dumps(x, ensure_ascii=False)
        return str(x) if x != '' else None

    return {
        '試合_id': game_id,
        '試合日時': v(0), 'Season': v(1), 'Kind': v(2), 'Week': v(3), 'Day': v(4), 'GameNumber': v(5),
        '主審': v(6), '後攻チーム': v(7), '先攻チーム': v(8), 'プレイの番号': v(9), '回': v(10), '表裏': v(11),
        '先攻得点': v(12), '後攻得点': v(13), 'S': v(14), 'B': v(15), 'アウト': v(16),
        '打席の継続': v(17), 'イニング継続': v(18), '試合継続': v(19),
        '一走打順': v(20), '一走氏名': v(21), '二走打順': v(22), '二走氏名': v(23), '三走打順': v(24), '三走氏名': v(25),
        '打順': v(26), '打者氏名': v(27), '打席左右': v(28), '作戦': v(29), '作戦2': v(30), '作戦結果': v(31),
        '投手氏名': v(32), '投手左右': v(33), '球数': v(34), '捕手': v(35),
        '一走状況': v(36), '二走状況': v(37), '三走状況': v(38), '打者状況': v(39), 'プレイの種類': v(40), '構え': v(41),
        'コースX': v(42), 'コースY': v(43), '球種': v(44),
        '打撃結果': v(45), '打撃結果2': v(46), '捕球選手': v(47), '打球タイプ': v(48), '打球強度': v(49),
        '打球位置X': v(50), '打球位置Y': v(51), '牽制の種類': v(52), '牽制詳細': v(53),
        'エラーの種類': v(54), 'タイムの種類': v(55), '球速': v(56), 'プレス': v(57), '偽走': v(58), '打者位置': v(59),
        '打席Id': v(60), '打席結果': v(61), 'Result_col': v(62), '打者登録名': v(63),
        '打者番号': v(64), '一走登録名': v(65), '一走番号': v(66), '二走登録名': v(67), '二走番号': v(68),
        '三走登録名': v(69), '三走番号': v(70), '投手番号': v(71), '入力項目': v(72),
        '先攻打順': v(73), '後攻打順': v(74), '経過時間': v(75), '開始時刻': v(76), '現在時刻': v(77),
        'top_poses': json_or_val(78), 'top_names': json_or_val(79), 'top_nums': json_or_val(80), 'top_lrs': json_or_val(81),
        'bottom_poses': json_or_val(82), 'bottom_names': json_or_val(83), 'bottom_nums': json_or_val(84), 'bottom_lrs': json_or_val(85),
        'top_score': json_or_val(86), 'bottom_score': json_or_val(87),
    }


# play_data の SELECT * の列順（id, 試合_id の次がこれ）
_PLAY_DATA_COLS = [
    '試合日時', 'Season', 'Kind', 'Week', 'Day', 'GameNumber', '主審', '後攻チーム', '先攻チーム',
    'プレイの番号', '回', '表裏', '先攻得点', '後攻得点', 'S', 'B', 'アウト',
    '打席の継続', 'イニング継続', '試合継続',
    '一走打順', '一走氏名', '二走打順', '二走氏名', '三走打順', '三走氏名',
    '打順', '打者氏名', '打席左右', '作戦', '作戦2', '作戦結果', '投手氏名', '投手左右', '球数', '捕手',
    '一走状況', '二走状況', '三走状況', '打者状況', 'プレイの種類', '構え', 'コースX', 'コースY', '球種',
    '打撃結果', '打撃結果2', '捕球選手', '打球タイプ', '打球強度', '打球位置X', '打球位置Y', '牽制の種類', '牽制詳細',
    'エラーの種類', 'タイムの種類', '球速', 'プレス', '偽走', '打者位置', '打席Id', '打席結果', 'Result_col', '打者登録名',
    '打者番号', '一走登録名', '一走番号', '二走登録名', '二走番号', '三走登録名', '三走番号', '投手番号', '入力項目',
    '先攻打順', '後攻打順', '経過時間', '開始時刻', '現在時刻',
    'top_poses', 'top_names', 'top_nums', 'top_lrs', 'bottom_poses', 'bottom_names', 'bottom_nums', 'bottom_lrs',
    'top_score', 'bottom_score'
]
_JSON_COLS = frozenset(['top_poses', 'top_names', 'top_nums', 'top_lrs', 'bottom_poses', 'bottom_names', 'bottom_nums', 'bottom_lrs', 'top_score', 'bottom_score'])


def get_all_plays_df(team_id: int):
    """Return all play data for games owned by team_id as a pandas DataFrame."""
    import pandas as pd
    conn = schema.get_conn()
    c = conn.cursor()
    c.execute(
        'SELECT * FROM play_data WHERE 試合_id IN '
        '(SELECT id FROM game WHERE owner_team_id = ?) '
        'ORDER BY 試合_id, プレイの番号',
        (team_id,),
    )
    rows = c.fetchall()
    conn.close()
    if not rows:
        return pd.DataFrame( columns = _PLAY_DATA_COLS )
    data = [ _db_row_to_list( r ) for r in rows ]
    return pd.DataFrame( data, columns = _PLAY_DATA_COLS )


def _db_row_to_list(r: tuple) -> list:
    """Restore one play_data row to all_list row (88 elements)."""
    def load_json(s):
        if s is None or s == '':
            return None
        try:
            return json.loads(s)
        except (json.JSONDecodeError, TypeError):
            return s

    out = []
    for i, col in enumerate(_PLAY_DATA_COLS):
        idx = 2 + i
        if idx >= len(r):
            out.append(None)
            continue
        val = r[idx]
        if col in _JSON_COLS:
            out.append(load_json(val))
        else:
            out.append(val)
    return out


def create_game(
    試合日時: str,
    先攻チーム名: str,
    後攻チーム名: str,
    主審: str = '',
    Season: str = '',
    Kind: str = '',
    Week: str = '',
    Day: str = '',
    GameNumber: str = '',
    owner_team_id: Optional[int] = None,
) -> int:
    """Create a new game and return game_id; ensure teams exist."""
    from . import player_repo
    top_id = player_repo.ensure_team(先攻チーム名)
    bottom_id = player_repo.ensure_team(後攻チーム名)
    conn = schema.get_conn()
    c = conn.cursor()
    c.execute('''
        INSERT INTO game (試合日時, Season, Kind, Week, Day, GameNumber, 主審, 先攻チーム_id, 後攻チーム_id, owner_team_id, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (試合日時, Season, Kind, Week, Day, GameNumber, 主審, top_id, bottom_id, owner_team_id, datetime.now().isoformat()))
    gid = c.lastrowid
    conn.commit()
    conn.close()
    try:
        path = _get_game_json_path( gid )
        game_data = {
            'game_id'    : gid,
            '試合日時'   : 試合日時,
            '先攻チーム' : 先攻チーム名,
            '後攻チーム' : 後攻チーム名,
            '主審'       : 主審,
            'Season'     : Season,
            'Kind'       : Kind,
            'Week'       : Week,
            'Day'        : Day,
            'GameNumber' : GameNumber,
            'created_at' : datetime.now().isoformat(),
            'plays'      : [],
        }
        with open( path, 'w', encoding = 'utf-8' ) as f:
            json.dump( game_data, f, ensure_ascii = False, indent = 2 )
    except Exception:
        pass
    return gid


def get_game(game_id):
    """試合1件を取得。"""
    conn = schema.get_conn()
    c = conn.cursor()
    c.execute('SELECT * FROM game WHERE id = ?', (game_id,))
    row = c.fetchone()
    conn.close()
    return row


def list_games(limit: int = 100, team_id: Optional[int] = None) -> List[Tuple[Any, ...]]:
    """Return list of games (newest first). If team_id given, only games owned by that team."""
    conn = schema.get_conn()
    c = conn.cursor()
    if team_id is not None:
        c.execute('''
            SELECT g.id, g.試合日時, g.Season, g.Kind, t1.名前 AS 先攻, t2.名前 AS 後攻
            FROM game g
            JOIN team t1 ON g.先攻チーム_id = t1.id
            JOIN team t2 ON g.後攻チーム_id = t2.id
            WHERE g.owner_team_id = ?
            ORDER BY g.id DESC
            LIMIT ?
        ''', (team_id, limit))
    else:
        c.execute('''
            SELECT g.id, g.試合日時, g.Season, g.Kind, t1.名前 AS 先攻, t2.名前 AS 後攻
            FROM game g
            JOIN team t1 ON g.先攻チーム_id = t1.id
            JOIN team t2 ON g.後攻チーム_id = t2.id
            ORDER BY g.id DESC
            LIMIT ?
        ''', (limit,))
    rows = c.fetchall()
    conn.close()
    return rows


def _assert_owner(c: Any, game_id: int, owner_team_id: int) -> None:
    """Raise PermissionError if game does not belong to owner_team_id (SQL-level check)."""
    c.execute('SELECT 1 FROM game WHERE id = ? AND owner_team_id = ?', (game_id, owner_team_id))
    if not c.fetchone():
        raise PermissionError(f"game {game_id} does not belong to team {owner_team_id}")


def get_play_list(game_id: int, owner_team_id: Optional[int] = None) -> List[list]:
    """Return play data for the game. Raises PermissionError if owner_team_id is given and does not match."""
    conn = schema.get_conn()
    c = conn.cursor()
    if owner_team_id is not None:
        # ownership と play_data 取得を同一クエリで行う（TOCTOU 防止）
        c.execute(
            'SELECT * FROM play_data WHERE 試合_id = ? '
            'AND 試合_id IN (SELECT id FROM game WHERE owner_team_id = ?) '
            'ORDER BY プレイの番号',
            (game_id, owner_team_id)
        )
    else:
        c.execute('SELECT * FROM play_data WHERE 試合_id = ? ORDER BY プレイの番号', (game_id,))
    rows = c.fetchall()
    conn.close()
    return [_db_row_to_list(r) for r in rows]


def insert_play(game_id: int, row_list: list, owner_team_id: Optional[int] = None) -> None:
    """Insert one play. Raises PermissionError if owner_team_id is given and does not match.

    PostgreSQL では接続切れ等に対し OperationalError / InterfaceError を短いバックオフで再試行する。
    """
    d = _row_to_db(game_id, row_list)
    max_attempts = 3 if schema.is_postgres() else 1
    for attempt in range(max_attempts):
        conn = schema.get_conn()
        try:
            c = conn.cursor()
            if owner_team_id is not None:
                _assert_owner(c, game_id, owner_team_id)
            cols = ', '.join(d.keys())
            placeholders = ', '.join('?' * len(d))
            c.execute(f'INSERT INTO play_data ({cols}) VALUES ({placeholders})', list(d.values()))
            conn.commit()
            schema.release_connection(conn, discard=False)
            _update_game_json_plays(game_id, row_list)
            return
        except Exception as e:
            discard = False
            if schema.is_postgres():
                import psycopg2
                if isinstance(e, (psycopg2.OperationalError, psycopg2.InterfaceError)):
                    discard = True
            try:
                conn.rollback()
            except Exception:
                pass
            schema.release_connection(conn, discard=discard)
            if discard and attempt < max_attempts - 1:
                # 接続プールをリセットして次のリトライで完全に新しい接続を使う
                schema.reset_pg_pool()
                time.sleep(0.3 * (2**attempt))
                continue
            raise


def sync_missing_plays(
    game_id: int, mem_rows: list, owner_team_id: Optional[int] = None
) -> int:
    """mem_rows にあって DB に無いプレイ（プレイの番号）を INSERT する。補完した件数を返す。

    1 件の INSERT 失敗は記録して続行し、最後にまとめて例外を送出する。
    これにより途中で止まらず全欠損プレイの再送を試みる。
    """
    if not mem_rows:
        return 0
    db_plays = get_play_list(game_id, owner_team_id=owner_team_id)
    db_nums = {row[9] for row in db_plays if row[9] is not None}
    missing = [row for row in mem_rows if row[9] not in db_nums]
    errors = []
    inserted = 0
    for row in missing:
        try:
            insert_play(game_id, row, owner_team_id=owner_team_id)
            inserted += 1
        except Exception as e:
            errors.append(e)
    if errors:
        raise errors[-1]  # 最後のエラーを呼び出し元に伝える
    return inserted


def get_game_teams(game_id: int, owner_team_id: Optional[int] = None) -> Tuple[Optional[str], Optional[str]]:
    """Return (top_team_name, bottom_team_name) for the game. Returns (None, None) if ownership fails."""
    conn = schema.get_conn()
    c = conn.cursor()
    if owner_team_id is not None:
        c.execute('''
            SELECT t1.名前, t2.名前 FROM game g
            JOIN team t1 ON g.先攻チーム_id = t1.id
            JOIN team t2 ON g.後攻チーム_id = t2.id
            WHERE g.id = ? AND g.owner_team_id = ?
        ''', (game_id, owner_team_id))
    else:
        c.execute('''
            SELECT t1.名前, t2.名前 FROM game g
            JOIN team t1 ON g.先攻チーム_id = t1.id
            JOIN team t2 ON g.後攻チーム_id = t2.id
            WHERE g.id = ?
        ''', (game_id,))
    row = c.fetchone()
    conn.close()
    return (row[0], row[1]) if row else (None, None)


def delete_last_play(game_id: int, owner_team_id: Optional[int] = None) -> None:
    """Delete the last play of the given game.

    対象行が無い（所有権不一致・DB未同期など）のときは RuntimeError を送出する。
    """
    max_attempts = 3 if schema.is_postgres() else 1
    for attempt in range(max_attempts):
        conn = schema.get_conn()
        try:
            c = conn.cursor()
            if owner_team_id is not None:
                c.execute(
                    'DELETE FROM play_data WHERE 試合_id = ? '
                    'AND 試合_id IN (SELECT id FROM game WHERE owner_team_id = ?) '
                    'AND id = (SELECT MAX(id) FROM play_data WHERE 試合_id = ?)',
                    (game_id, owner_team_id, game_id)
                )
            else:
                c.execute(
                    'DELETE FROM play_data WHERE 試合_id = ? AND id = (SELECT MAX(id) FROM play_data WHERE 試合_id = ?)',
                    (game_id, game_id)
                )
            rc = c.rowcount
            conn.commit()
            schema.release_connection(conn, discard=False)
            if not rc:
                raise RuntimeError(
                    'DB上に削除対象のプレイがありません（所有権・同期ずれの可能性があります）。'
                )
            return
        except Exception as e:
            discard = False
            if schema.is_postgres():
                import psycopg2
                if isinstance(e, (psycopg2.OperationalError, psycopg2.InterfaceError)):
                    discard = True
            try:
                conn.rollback()
            except Exception:
                pass
            schema.release_connection(conn, discard=discard)
            if discard and attempt < max_attempts - 1:
                schema.reset_pg_pool()
                time.sleep(0.3 * (2**attempt))
                continue
            raise


def get_plays_df_for_game(game_id: int, owner_team_id: Optional[int] = None):
    """Return play data for a specific game as a pandas DataFrame."""
    import pandas as pd
    rows = get_play_list(game_id, owner_team_id=owner_team_id)
    if not rows:
        return pd.DataFrame(columns=_PLAY_DATA_COLS)
    df = pd.DataFrame(rows, columns=_PLAY_DATA_COLS)
    for col in ('回', '打順', '先攻得点', '後攻得点'):
        df[col] = pd.to_numeric(df[col], errors='coerce')
    return df


def delete_game(game_id: int, owner_team_id: Optional[int] = None) -> None:
    """Delete a game and all its play_data rows. No-op if ownership fails."""
    conn = schema.get_conn()
    c = conn.cursor()
    if owner_team_id is not None:
        # play_data は owner_team_id で絞った game の分のみ削除
        c.execute(
            'DELETE FROM play_data WHERE 試合_id = ? '
            'AND 試合_id IN (SELECT id FROM game WHERE owner_team_id = ?)',
            (game_id, owner_team_id)
        )
        c.execute('DELETE FROM game WHERE id = ? AND owner_team_id = ?', (game_id, owner_team_id))
    else:
        c.execute('DELETE FROM play_data WHERE 試合_id = ?', (game_id,))
        c.execute('DELETE FROM game WHERE id = ?', (game_id,))
    conn.commit()
    conn.close()
