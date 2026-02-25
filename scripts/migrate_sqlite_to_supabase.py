#!/usr/bin/env python3
"""
Migrate data from SQLite app_data.db to Supabase (PostgreSQL).
Usage:
  1. Create Supabase project and run db/supabase_schema.sql in SQL Editor.
  2. Set DATABASE_URL in .env (Supabase connection string).
  3. Run: python scripts/migrate_sqlite_to_supabase.py

Reads from data/app_data.db (SQLite) and inserts into the database given by DATABASE_URL.
"""
import json
import os
import sqlite3
import sys

# Project root
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


def _load_dotenv(path: str) -> None:
    """Load .env file into os.environ (fallback when python-dotenv not installed)."""
    if not os.path.isfile(path):
        return
    with open(path, encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if '=' in line:
                key, _, value = line.partition('=')
                key = key.strip()
                value = value.strip()
                if value.startswith('"') and value.endswith('"'):
                    value = value[1:-1].replace('\\"', '"')
                elif value.startswith("'") and value.endswith("'"):
                    value = value[1:-1].replace("\\'", "'")
                if key and key not in os.environ:
                    os.environ[key] = value


_env_path = os.path.join(ROOT, '.env')
try:
    from dotenv import load_dotenv
    load_dotenv(_env_path)
except ImportError:
    _load_dotenv(_env_path)

DATABASE_URL = os.environ.get('DATABASE_URL')
SQLITE_PATH = os.path.join(ROOT, 'data', 'app_data.db')


def main():
    if not DATABASE_URL or not DATABASE_URL.strip():
        print('Set DATABASE_URL in .env (Supabase PostgreSQL connection string).')
        sys.exit(1)
    if not os.path.exists(SQLITE_PATH):
        print(f'SQLite DB not found: {SQLITE_PATH}')
        sys.exit(1)

    import psycopg2
    from psycopg2.extras import execute_batch

    sqlite_conn = sqlite3.connect(SQLITE_PATH)
    sqlite_conn.row_factory = sqlite3.Row
    pg_conn = psycopg2.connect(DATABASE_URL)

    def sqlite_table_exists(name):
        c = sqlite_conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (name,)
        )
        return c.fetchone() is not None

    try:
        # 1. team
        if sqlite_table_exists('team'):
            rows = sqlite_conn.execute('SELECT id, 名前 FROM team').fetchall()
            if rows:
                cur = pg_conn.cursor()
                for r in rows:
                    cur.execute('INSERT INTO team (id, "名前") VALUES (%s, %s) ON CONFLICT (id) DO NOTHING', (r['id'], r['名前']))
                pg_conn.commit()
                cur.execute("SELECT setval(pg_get_serial_sequence('team', 'id'), (SELECT COALESCE(MAX(id), 1) FROM team))")
                pg_conn.commit()
                cur.close()
                print(f'Migrated team: {len(rows)} rows')

        # 2. player
        if sqlite_table_exists('player'):
            rows = sqlite_conn.execute('SELECT id, チーム_id, 背番号, 名前, 左右 FROM player').fetchall()
            if rows:
                cur = pg_conn.cursor()
                for r in rows:
                    cur.execute(
                        'INSERT INTO player (id, チーム_id, 背番号, "名前", 左右) VALUES (%s, %s, %s, %s, %s) '
                        'ON CONFLICT (チーム_id, 背番号) DO NOTHING',
                        (r['id'], r['チーム_id'], r['背番号'], r['名前'], r['左右'])
                    )
                pg_conn.commit()
                cur.execute("SELECT setval(pg_get_serial_sequence('player', 'id'), (SELECT COALESCE(MAX(id), 1) FROM player))")
                pg_conn.commit()
                cur.close()
                print(f'Migrated player: {len(rows)} rows')

        # 3. stamem
        if sqlite_table_exists('stamem'):
            rows = sqlite_conn.execute('SELECT チーム_id, poses, names, nums, lrs FROM stamem').fetchall()
            if rows:
                cur = pg_conn.cursor()
                for r in rows:
                    cur.execute(
                        'INSERT INTO stamem (チーム_id, poses, names, nums, lrs) VALUES (%s, %s, %s, %s, %s) '
                        'ON CONFLICT (チーム_id) DO UPDATE SET poses = EXCLUDED.poses, names = EXCLUDED.names, nums = EXCLUDED.nums, lrs = EXCLUDED.lrs',
                        (r['チーム_id'], r['poses'], r['names'], r['nums'], r['lrs'])
                    )
                pg_conn.commit()
                cur.close()
                print(f'Migrated stamem: {len(rows)} rows')

        # 4. game
        if sqlite_table_exists('game'):
            rows = sqlite_conn.execute(
                'SELECT id, 試合日時, Season, Kind, Week, Day, GameNumber, 主審, 先攻チーム_id, 後攻チーム_id, 開始時刻, 現在時刻, 経過時間, created_at FROM game'
            ).fetchall()
            if rows:
                cur = pg_conn.cursor()
                for r in rows:
                    cur.execute(
                        '''INSERT INTO game (id, "試合日時", "Season", "Kind", "Week", "Day", "GameNumber", 主審, 先攻チーム_id, 後攻チーム_id, 開始時刻, 現在時刻, 経過時間, created_at)
                           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) ON CONFLICT (id) DO NOTHING''',
                        (r['id'], r['試合日時'], r['Season'], r['Kind'], r['Week'], r['Day'], r['GameNumber'],
                         r['主審'], r['先攻チーム_id'], r['後攻チーム_id'], r['開始時刻'], r['現在時刻'], r['経過時間'], r['created_at'])
                    )
                pg_conn.commit()
                cur.execute("SELECT setval(pg_get_serial_sequence('game', 'id'), (SELECT COALESCE(MAX(id), 1) FROM game))")
                pg_conn.commit()
                cur.close()
                print(f'Migrated game: {len(rows)} rows')

        # 5. play_data (many columns)
        if sqlite_table_exists('play_data'):
            cur_s = sqlite_conn.execute('SELECT * FROM play_data')
            col_names = [d[0] for d in cur_s.description]
            rows = cur_s.fetchall()
            if rows:
                # Build INSERT with quoted identifiers for reserved/mixed-case columns
                def q(s):
                    if s in ('Season', 'Kind', 'Week', 'Day', 'GameNumber', 'Result_col', 'S', 'B'):
                        return f'"{s}"'
                    return s
                cols = ', '.join(q(c) for c in col_names)
                placeholders = ', '.join(['%s'] * len(col_names))
                sql = f'INSERT INTO play_data ({cols}) VALUES ({placeholders})'
                cur = pg_conn.cursor()
                execute_batch(cur, sql, [tuple(r) for r in rows], page_size=100)
                pg_conn.commit()
                cur.execute("SELECT setval(pg_get_serial_sequence('play_data', 'id'), (SELECT COALESCE(MAX(id), 1) FROM play_data))")
                pg_conn.commit()
                cur.close()
                print(f'Migrated play_data: {len(rows)} rows')

        print('Migration done.')
    finally:
        sqlite_conn.close()
        pg_conn.close()


if __name__ == '__main__':
    main()
