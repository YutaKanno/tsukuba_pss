-- PostgreSQL schema for Supabase (app_data.db equivalent).
-- Run in Supabase SQL Editor or via psql.

-- チーム（大学・チームマスタ）
CREATE TABLE IF NOT EXISTS team (
    id SERIAL PRIMARY KEY,
    "名前" TEXT UNIQUE NOT NULL
);

-- 選手（アプリで登録）
CREATE TABLE IF NOT EXISTS player (
    id SERIAL PRIMARY KEY,
    チーム_id INTEGER NOT NULL REFERENCES team(id),
    背番号 TEXT NOT NULL,
    "名前" TEXT NOT NULL,
    左右 TEXT NOT NULL,
    UNIQUE(チーム_id, 背番号)
);

-- スタメン（大学ごとのスタメン記憶）
CREATE TABLE IF NOT EXISTS stamem (
    チーム_id INTEGER PRIMARY KEY REFERENCES team(id),
    poses TEXT NOT NULL,
    names TEXT NOT NULL,
    nums TEXT NOT NULL,
    lrs TEXT NOT NULL
);

-- 試合一覧
CREATE TABLE IF NOT EXISTS game (
    id SERIAL PRIMARY KEY,
    "試合日時" TEXT NOT NULL,
    "Season" TEXT,
    "Kind" TEXT,
    "Week" TEXT,
    "Day" TEXT,
    "GameNumber" TEXT,
    主審 TEXT,
    先攻チーム_id INTEGER NOT NULL REFERENCES team(id),
    後攻チーム_id INTEGER NOT NULL REFERENCES team(id),
    開始時刻 TEXT,
    現在時刻 TEXT,
    経過時間 TEXT,
    created_at TEXT
);

-- データ（毎球 1 プレイ = 1 行）
CREATE TABLE IF NOT EXISTS play_data (
    id SERIAL PRIMARY KEY,
    試合_id INTEGER NOT NULL REFERENCES game(id),
    "試合日時" TEXT,
    "Season" TEXT,
    "Kind" TEXT,
    "Week" TEXT,
    "Day" TEXT,
    "GameNumber" TEXT,
    主審 TEXT,
    後攻チーム TEXT,
    先攻チーム TEXT,
    プレイの番号 INTEGER,
    "回" INTEGER,
    表裏 TEXT,
    先攻得点 INTEGER,
    後攻得点 INTEGER,
    "S" INTEGER,
    "B" INTEGER,
    アウト INTEGER,
    打席の継続 TEXT,
    イニング継続 TEXT,
    試合継続 TEXT,
    一走打順 INTEGER,
    一走氏名 TEXT,
    二走打順 INTEGER,
    二走氏名 TEXT,
    三走打順 INTEGER,
    三走氏名 TEXT,
    打順 INTEGER,
    打者氏名 TEXT,
    打席左右 TEXT,
    作戦 TEXT,
    作戦2 TEXT,
    作戦結果 TEXT,
    投手氏名 TEXT,
    投手左右 TEXT,
    球数 INTEGER,
    捕手 TEXT,
    一走状況 TEXT,
    二走状況 TEXT,
    三走状況 TEXT,
    打者状況 TEXT,
    プレイの種類 TEXT,
    構え TEXT,
    "コースX" REAL,
    "コースY" REAL,
    球種 TEXT,
    打撃結果 TEXT,
    打撃結果2 TEXT,
    捕球選手 TEXT,
    打球タイプ TEXT,
    打球強度 TEXT,
    打球位置X REAL,
    打球位置Y REAL,
    牽制の種類 TEXT,
    牽制詳細 TEXT,
    エラーの種類 TEXT,
    タイムの種類 TEXT,
    球速 REAL,
    プレス TEXT,
    偽走 TEXT,
    打者位置 TEXT,
    打席Id TEXT,
    打席結果 TEXT,
    "Result_col" TEXT,
    打者登録名 TEXT,
    打者番号 TEXT,
    一走登録名 TEXT,
    一走番号 TEXT,
    二走登録名 TEXT,
    二走番号 TEXT,
    三走登録名 TEXT,
    三走番号 TEXT,
    投手番号 TEXT,
    入力項目 TEXT,
    先攻打順 TEXT,
    後攻打順 TEXT,
    経過時間 TEXT,
    開始時刻 TEXT,
    現在時刻 TEXT,
    top_poses TEXT,
    top_names TEXT,
    top_nums TEXT,
    top_lrs TEXT,
    bottom_poses TEXT,
    bottom_names TEXT,
    bottom_nums TEXT,
    bottom_lrs TEXT,
    top_score TEXT,
    bottom_score TEXT
);
