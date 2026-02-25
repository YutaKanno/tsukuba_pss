"""
DB operations for game and per-play data.
"""
import json
import sqlite3
from datetime import datetime
from typing import Any, List, Optional, Tuple

from . import schema


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
) -> int:
    """Create a new game and return game_id; ensure teams exist."""
    from . import player_repo
    schema.init_db()
    top_id = player_repo.ensure_team(先攻チーム名)
    bottom_id = player_repo.ensure_team(後攻チーム名)
    conn = schema.get_conn()
    c = conn.cursor()
    c.execute('''
        INSERT INTO game (試合日時, Season, Kind, Week, Day, GameNumber, 主審, 先攻チーム_id, 後攻チーム_id, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (試合日時, Season, Kind, Week, Day, GameNumber, 主審, top_id, bottom_id, datetime.now().isoformat()))
    gid = c.lastrowid
    conn.commit()
    conn.close()
    return gid


def get_game(game_id):
    """試合1件を取得。"""
    conn = schema.get_conn()
    c = conn.cursor()
    c.execute('SELECT * FROM game WHERE id = ?', (game_id,))
    row = c.fetchone()
    conn.close()
    return row


def list_games(limit: int = 100) -> List[Tuple[Any, ...]]:
    """Return list of games (newest first), each row (id, 試合日時, Season, 先攻, 後攻)."""
    schema.init_db()
    conn = schema.get_conn()
    c = conn.cursor()
    c.execute('''
        SELECT g.id, g.試合日時, g.Season, t1.名前 AS 先攻, t2.名前 AS 後攻
        FROM game g
        JOIN team t1 ON g.先攻チーム_id = t1.id
        JOIN team t2 ON g.後攻チーム_id = t2.id
        ORDER BY g.id DESC
        LIMIT ?
    ''', (limit,))
    rows = c.fetchall()
    conn.close()
    return rows


def get_play_list(game_id: int) -> List[list]:
    """Return play data for the game as all_list format (list of 88-element lists)."""
    conn = schema.get_conn()
    c = conn.cursor()
    c.execute('SELECT * FROM play_data WHERE 試合_id = ? ORDER BY プレイの番号', (game_id,))
    rows = c.fetchall()
    conn.close()
    return [_db_row_to_list(r) for r in rows]


def insert_play(game_id: int, row_list: list) -> None:
    """Insert one play; row_list is one all_list row (88 elements)."""
    schema.init_db()
    d = _row_to_db(game_id, row_list)
    conn = schema.get_conn()
    c = conn.cursor()
    cols = ', '.join(d.keys())
    placeholders = ', '.join('?' * len(d))
    c.execute(f'INSERT INTO play_data ({cols}) VALUES ({placeholders})', list(d.values()))
    conn.commit()
    conn.close()


def get_game_teams(game_id: int) -> Tuple[Optional[str], Optional[str]]:
    """Return (top_team_name, bottom_team_name) for the game."""
    conn = schema.get_conn()
    c = conn.cursor()
    c.execute('''
        SELECT t1.名前, t2.名前 FROM game g
        JOIN team t1 ON g.先攻チーム_id = t1.id
        JOIN team t2 ON g.後攻チーム_id = t2.id
        WHERE g.id = ?
    ''', (game_id,))
    row = c.fetchone()
    conn.close()
    return (row[0], row[1]) if row else (None, None)


def delete_last_play(game_id: int) -> None:
    """Delete the last play of the given game."""
    conn = schema.get_conn()
    c = conn.cursor()
    c.execute('DELETE FROM play_data WHERE 試合_id = ? AND id = (SELECT MAX(id) FROM play_data WHERE 試合_id = ?)', (game_id, game_id))
    conn.commit()
    conn.close()


def delete_game(game_id: int) -> None:
    """Delete a game and all its play_data rows."""
    conn = schema.get_conn()
    c = conn.cursor()
    c.execute('DELETE FROM play_data WHERE 試合_id = ?', (game_id,))
    c.execute('DELETE FROM game WHERE id = ?', (game_id,))
    conn.commit()
    conn.close()
