# Tsukuba PSS (Pitch by Pitch Scoring System)

野球の試合における **毎球データ（Pitch by Pitch）** をリアルタイムで記録・管理する Streamlit アプリケーションです。大学野球の試合を対象に、1球ごとの投球・打撃・走塁データを入力し、試合中にリアルタイムで統計を確認できます。

---

## 画面構成

アプリは 4 つのページで構成されています。

| ページ | ファイル | 内容 |
|--------|----------|------|
| スタート | `main.py` | 試合開始・入力再開・DB管理への導線 |
| スタメン入力 | `member.py` | チーム選択、先攻・後攻のオーダー入力、試合情報の設定 |
| メイン (データ入力) | `main_page.py` | 毎球のデータ入力・統計表示・スコアボード・データ一覧 |
| DB管理 | `db_admin.py` | チーム・選手・スタメン・試合の一覧確認、CSV保存、試合削除 |

---

## 機能一覧

### 試合データ入力（メイン画面）

メイン画面は 3 つのタブで構成されています。

#### メニュータブ
- **スコアボード** — イニングごとの得点・H/E/K/B を自動集計してテーブル表示
- **投手成績（リアルタイム）**
  - 当日: 投球回・最速・平均球速・被安打・奪三振・与四球・失点
  - シーズン通算: 被打率（対右/対左別）・投球回・WHIP・FIP
  - 投球数
- **打者成績（リアルタイム）**
  - 当日打席結果一覧
  - シーズン通算: 打率（対右投/対左投別）・本塁打
  - 次打者の成績も同様に表示
- **球種分布** — 当日の投手の球種割合を Plotly 円グラフで表示

#### データ入力タブ
1球ごとに以下の情報を記録します:

| カテゴリ | 入力項目 |
|----------|----------|
| 投球 | 構え（セット/ワインドアップ等）・コース（ストライクゾーン画像クリック）・球種・球速 |
| 打撃結果 | 見逃し/空振り/ファール/ボール/三振/四球/死球/凡打/安打/本塁打/犠打/犠飛 等 |
| 打球情報 | 打球タイプ（G/L/F）・打球強度・捕球選手・打球位置（フィールド画像クリック） |
| 走者状況 | 打者状況（アウト/出塁/二進/三進/本進）・各走者の進塁状況 |
| その他 | 作戦・プレス・牽制・エラー・打撃結果2（PB/WP/ボーク等） |

**打撃結果に連動した自動状況更新:**

打撃結果を選択すると、打者状況・走者状況が自動的に設定されます（手動で上書き可能）。

| 打撃結果 | 打者 | 走者への影響 |
|----------|------|-------------|
| 見逃し三振・空振り三振・振り逃げ・K3 | アウト | — |
| 四球・死球 | 出塁 | 押し出し（一走存在時のみ順次進塁） |
| 単打・エラー・野手選択・犠打失策・凡打出塁 | 出塁 | 各走者 +1 進塁 |
| 二塁打 | 二進 | 各走者 +2 進塁 |
| 三塁打 | 三進 | 各走者 本進 |
| 本塁打 | 本進 | 各走者 本進 |
| 凡打死・ファールフライ | アウト | — |
| 犠打 | アウト | 各走者 +1 進塁 |
| 犠飛 | アウト | 三走存在時のみ本進 |

#### データ一覧タブ
- 入力済みデータを時系列テーブルで表示
- 「1つ前に戻す」ボタンで直前のプレイを取消可能

### スタメン入力画面

- **チーム選択** — DB に登録されたチームから先攻・後攻を選択
- **オーダー入力** — 背番号を入力すると DB から名前と左右を自動取得
- **ポジション設定** — 打順ごとに守備位置をドロップダウンで設定
- **スタメン記憶** — 確定時にチームごとのスタメンを DB に保存し、次回選択時に自動復元
- **選手の追加登録** — 試合中でも新しい選手を DB に登録可能
- **試合情報の入力** — 日時・主審・Season・Kind・Day・Week・GameNumber を設定

### 試合情報の選択肢

| 項目 | 選択肢 |
|------|--------|
| Season | 春季 / 夏季 / 秋季 / 冬季 |
| Kind | 全国大会 / 関東大会 / リーグ戦 / 準公式戦 / Aオープン戦 / Bオープン戦 / Cオープン戦 / A紅白戦 / B紅白戦 / C紅白戦 / 部内リーグ / その他（自由入力） |
| GameNumber | 0 / 1 / 2 / 3 / 4 |
| Week | 0〜12 |
| Day | 0 / 1 / 2 / 3 / 4 |

### DB 管理画面

| タブ | 機能 |
|------|------|
| チーム一覧 | 登録済みチームの一覧表示 |
| 選手一覧 | チーム別の選手一覧（背番号・名前・左右） |
| スタメン | チーム別のスタメン記憶内容の確認 |
| 試合一覧 | 全試合の一覧（ID・日時・Season・Kind・先攻・後攻） |
| 試合をCSVで保存 | 試合を選択して毎球データを CSV でダウンロード |
| 試合削除 | 試合と紐づく全プレイデータの完全削除 |

### その他の機能

- **試合再開** — 途中で中断した試合を選択し、最後の入力行から入力を継続
- **ストライクゾーン表示** — 左打者・右打者で画像を切替、クリックでコース座標を取得
- **フィールド表示** — 守備位置に選手名を描画、クリックで打球位置座標を取得
- **開始時刻バリデーション** — 開始時刻が未入力・不正な場合はエラー表示（クラッシュ防止）

---

## 技術構成

| 項目 | 技術 |
|------|------|
| フレームワーク | Streamlit |
| データ操作 | Pandas, NumPy |
| チャート | Plotly |
| 画像処理 | Pillow |
| 座標入力 | streamlit-image-coordinates |
| DB（ローカル） | SQLite (`data/app_data.db`) |
| DB（本番） | PostgreSQL (Supabase) |
| DB 接続 | psycopg2-binary, python-dotenv |
| デプロイ | Streamlit Community Cloud |

### DB 切替の仕組み

`db/schema.py` が環境変数 `DATABASE_URL` の有無を判定し、自動的に SQLite と PostgreSQL を切り替えます。PostgreSQL 使用時は `_PgCursorWrapper` がプレースホルダ変換（`?` → `%s`）とカラム名のクオートを自動処理するため、リポジトリコードは単一のまま両方の DB で動作します。

---

## ディレクトリ構成

```
.
├── main.py                 # エントリーポイント（ページルーティング・セッション管理）
├── main_page.py            # 試合メイン画面（データ入力・統計表示・データ一覧）
├── member.py               # スタメン入力・試合情報入力・選手追加登録
├── field.py                # フィールド画像の表示・打球位置クリック座標取得
├── plate.py                # ストライクゾーン画像の表示・コースクリック座標取得
├── cal_stats.py            # 投手・打者の統計計算（投球回・被打率・WHIP・FIP等）
├── config.py               # カラム名定義（88列）・デフォルト値・初期データ
├── db_admin.py             # DB管理画面（一覧・CSV保存・試合削除）
├── requirements.txt        # Python 依存パッケージ
├── .env                    # 環境変数（DATABASE_URL）※.gitignore推奨
│
├── assets/
│   ├── Field3.png          # フィールド背景画像
│   ├── Plate_L.png         # ストライクゾーン（左打者用）
│   ├── Plate_R.png         # ストライクゾーン（右打者用）
│   ├── tsukuba_logo.png    # アプリアイコン（ブラウザタブ）
│   └── icon.ico
│
├── fonts/
│   ├── ipaexg.ttf          # IPAexゴシック（フィールド上の選手名描画用）
│   └── ipaexm.ttf          # IPAex明朝
│
├── db/
│   ├── __init__.py
│   ├── schema.py           # DB接続・テーブル作成（SQLite / PostgreSQL 自動切替）
│   ├── game_repo.py        # 試合・プレイデータの CRUD
│   ├── player_repo.py      # チーム・選手・スタメンの CRUD
│   └── supabase_schema.sql # Supabase 用 DDL（PostgreSQL テーブル定義）
│
├── components/
│   └── plate_component/    # ストライクゾーン用カスタム React コンポーネント
│       └── frontend/
│           ├── src/
│           ├── package.json
│           └── vite.config.js
│
├── scripts/
│   └── migrate_sqlite_to_supabase.py  # SQLite → Supabase データ移行スクリプト
│
├── build/                  # ビルド設定（Nuitka / PyInstaller）
├── data/                   # SQLite DB ファイル格納（自動作成）
└── docs/                   # ドキュメント
    └── grammar_rules.md
```

---

## DB テーブル設計

| テーブル | 主キー | 内容 |
|----------|--------|------|
| `team` | `id` (AUTO) | チーム（大学名）マスタ。`名前` は UNIQUE |
| `player` | `id` (AUTO) | 選手情報。`(チーム_id, 背番号)` で UNIQUE |
| `stamem` | `チーム_id` | チーム別のスタメン記憶（poses/names/nums/lrs を JSON 文字列で保存） |
| `game` | `id` (AUTO) | 試合情報（日時・Season・Kind・Week・Day・GameNumber・主審・先攻/後攻チーム） |
| `play_data` | `id` (AUTO) | 毎球データ。`試合_id` で `game` に紐づく。1プレイ = 1行、88列 |

### プレイデータの 88 カラム（`config.py` の `COLUMN_NAMES`）

```
試合日時, Season, Kind, Week, Day, GameNumber, 主審,
後攻チーム, 先攻チーム, プレイの番号, 回, 表.裏,
先攻得点, 後攻得点, S, B, アウト, 打席の継続, イニング継続, 試合継続,
一走打順, 一走氏名, 二走打順, 二走氏名, 三走打順, 三走氏名,
打順, 打者氏名, 打席左右, 作戦, 作戦2, 作戦結果,
投手氏名, 投手左右, 球数, 捕手,
一走状況, 二走状況, 三走状況, 打者状況, プレイの種類, 構え,
コースX, コースY, 球種, 打撃結果, 打撃結果2, 捕球選手,
打球タイプ, 打球強度, 打球位置X, 打球位置Y,
牽制の種類, 牽制詳細, エラーの種類, タイムの種類,
球速, プレス, 偽走, 打者位置, 打席Id, 打席結果, Result_col,
打者登録名, 打者番号, 一走登録名, 一走番号,
二走登録名, 二走番号, 三走登録名, 三走番号, 投手番号,
入力項目, 先攻打順, 後攻打順, 経過時間, 開始時刻, 現在時刻,
top_poses, top_names, top_nums, top_lrs,
bottom_poses, bottom_names, bottom_nums, bottom_lrs,
top_score, bottom_score
```

---

## セットアップ

### 前提条件

- Python 3.9 以上
- pip

### ローカル実行

```bash
# 依存パッケージのインストール
pip install -r requirements.txt

# アプリの起動
streamlit run main.py
```

SQLite がデフォルトで使用され、`data/app_data.db` に自動作成されます。初回起動時にテーブルも自動で作成されます。

### Supabase (PostgreSQL) を使用する場合

1. [Supabase](https://supabase.com/) でプロジェクトを作成
2. SQL Editor で `db/supabase_schema.sql` を実行してテーブルを作成
3. プロジェクトルートに `.env` ファイルを作成し、接続文字列を設定:

```
DATABASE_URL=postgresql://postgres:[PASSWORD]@[HOST]:5432/postgres
```

4. 既存の SQLite データを移行する場合:

```bash
python scripts/migrate_sqlite_to_supabase.py
```

### Streamlit Community Cloud へのデプロイ

1. リポジトリを GitHub に push（`.env` は push しないこと）
2. [Streamlit Community Cloud](https://share.streamlit.io/) でアプリを作成
3. アプリの Settings → Secrets に以下を追加:

```toml
DATABASE_URL = "postgresql://postgres:[PASSWORD]@[HOST]:5432/postgres"
```

4. リポジトリのメインブランチと `main.py` を指定してデプロイ

---

## 依存パッケージ

| パッケージ | 用途 |
|-----------|------|
| `streamlit` | Web UI フレームワーク |
| `pandas` | データフレーム操作 |
| `numpy` | 数値計算 |
| `plotly` | 球種分布の円グラフ |
| `Pillow` | フィールド・ストライクゾーン画像の処理 |
| `streamlit-image-coordinates` | 画像クリックによる座標取得 |
| `streamlit-drawable-canvas` | 描画キャンバス |
| `matplotlib` | グラフ描画（補助） |
| `psycopg2-binary` | PostgreSQL 接続 |
| `python-dotenv` | `.env` ファイルからの環境変数読み込み |
| `requests` | HTTP リクエスト |
| `beautifulsoup4` | HTML パース |

---

## 運用上の注意

- **ブラウザのリロード**: Streamlit はブラウザをリロードするとセッション状態が失われます。入力途中のデータは確定ボタンを押すまで DB に保存されません。
- **同時アクセス**: 同じ試合を複数ブラウザで同時に入力することは想定されていません。
- **データのバックアップ**: SQLite 使用時は `data/app_data.db` を定期的にバックアップしてください。Supabase 使用時は Supabase のバックアップ機能を利用できます。
- **フォント**: フィールド上の選手名描画には `fonts/ipaexg.ttf`（IPAexゴシック）が必要です。
