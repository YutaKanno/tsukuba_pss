# Tsukuba PSS

野球の試合における毎球データ（Pitch by Pitch）をリアルタイムで記録・管理する Streamlit アプリケーション。

## 機能

- **試合データ入力** — 1球ごとに球種・コース・打撃結果・打球位置・走者状況などを記録
- **リアルタイム統計表示** — 投手成績（投球回・被打率・WHIP・FIP）、打者成績（打率・対左右別）を試合中にリアルタイム表示
- **スコアボード** — イニングごとのスコア・H/E/K/B を自動集計
- **フィールド & ストライクゾーン** — 画像クリックで打球位置・投球コースを座標として記録
- **チーム・選手管理** — チーム登録、選手の一括追加、スタメン記憶（前回のスタメンを自動復元）
- **試合再開** — 途中で中断した試合を最後の入力行から再開
- **CSV エクスポート** — 試合データを CSV 形式でダウンロード
- **データベース管理** — チーム・選手・スタメン・試合の一覧確認、試合削除

## 技術構成

| 項目 | 技術 |
|------|------|
| フロントエンド | Streamlit |
| チャート | Plotly |
| 画像処理 | Pillow + streamlit-image-coordinates |
| DB（ローカル） | SQLite (`data/app_data.db`) |
| DB（本番） | PostgreSQL (Supabase) |
| デプロイ | Streamlit Community Cloud |

## ディレクトリ構成

```
.
├── main.py                 # エントリーポイント（ページルーティング・セッション管理）
├── main_page.py            # 試合メイン画面（データ入力・成績表示・データ一覧）
├── member.py               # スタメン入力・試合情報入力・選手追加登録
├── field.py                # フィールド画像の表示・打球位置クリック座標取得
├── plate.py                # ストライクゾーン画像の表示・コースクリック座標取得
├── cal_stats.py            # 投手・打者の統計計算
├── config.py               # カラム名定義・デフォルト値・初期データ
├── db_admin.py             # DB管理画面（一覧・CSV保存・試合削除）
├── requirements.txt
├── .env                    # 環境変数（DATABASE_URL）
├── assets/
│   ├── Field3.png          # フィールド背景画像
│   ├── Plate_L.png         # ストライクゾーン（左打者）
│   ├── Plate_R.png         # ストライクゾーン（右打者）
│   ├── tsukuba_logo.png    # アプリアイコン
│   └── icon.ico
├── fonts/
│   └── ipaexg.ttf          # IPAexゴシック（フィールド上の選手名描画用）
├── db/
│   ├── schema.py           # DB接続・スキーマ定義（SQLite / PostgreSQL 両対応）
│   ├── game_repo.py        # 試合・プレイデータの CRUD
│   ├── player_repo.py      # チーム・選手・スタメンの CRUD
│   └── supabase_schema.sql # Supabase 用 DDL
├── components/
│   └── plate_component/    # ストライクゾーン用カスタム React コンポーネント
├── scripts/
│   └── migrate_sqlite_to_supabase.py  # SQLite → Supabase 移行スクリプト
└── build/                  # ビルド設定（Nuitka / PyInstaller）
```

## セットアップ

### ローカル実行

```bash
pip install -r requirements.txt
streamlit run main.py
```

SQLite がデフォルトで使用され、`data/app_data.db` に自動作成されます。

### Supabase (PostgreSQL) を使用する場合

1. Supabase でプロジェクトを作成
2. `db/supabase_schema.sql` を SQL Editor で実行してテーブルを作成
3. `.env` に接続文字列を設定：
   ```
   DATABASE_URL=postgresql://...
   ```

### Streamlit Community Cloud へのデプロイ

1. リポジトリを GitHub に push
2. [Streamlit Community Cloud](https://share.streamlit.io/) でアプリを作成
3. Secrets に `DATABASE_URL` を設定

## データ構造

1球ごとのプレイデータは 88 カラムで構成されます（`config.py` の `COLUMN_NAMES` 参照）。

### DB テーブル

| テーブル | 内容 |
|----------|------|
| `team` | チーム（大学名）マスタ |
| `player` | 選手情報（チーム・背番号・名前・左右） |
| `stamem` | スタメン記憶（チーム別の前回スタメン） |
| `game` | 試合情報（日時・Season・Kind・チーム等） |
| `play_data` | 毎球データ（88列、1プレイ = 1行） |

## 試合情報の選択肢

| 項目 | 選択肢 |
|------|--------|
| Season | 春季 / 夏季 / 秋季 / 冬季 |
| Kind | 全国大会 / 関東大会 / リーグ戦 / 準公式戦 / Aオープン戦 / Bオープン戦 / Cオープン戦 / A紅白戦 / B紅白戦 / C紅白戦 / 部内リーグ / その他 |
| GameNumber | 1 / 2 / 3 / 4 |
| Week | 1〜12 |
| Day | 1 / 2 / 3 / 4 |
