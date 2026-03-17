"""
Tsukuba PSS entry point.
"""
from datetime import datetime
from typing import Optional

import pandas as pd
import streamlit as st

import db_admin
import main_page
import member
from db import game_repo, player_repo, schema


def init_session() -> None:
    """Initialize session state defaults."""
    for key, default in [
        ("all_list", []),
        ("member_df", None),
        ("current_game_id", None),
        ("page_ctg", "start"),
        ("game_start", "continue"),
        ("打撃結果", "0"),
    ]:
        if key not in st.session_state:
            st.session_state[key] = default


def ensure_db() -> None:
    """Initialize DB once and run migrations."""
    if "db_inited" in st.session_state:
        return
    schema.init_db()
    try:
        player_repo.migrate_member_remember()
    except Exception:
        pass
    st.session_state["db_inited"] = True


def load_member_df_from_db() -> Optional[pd.DataFrame]:
    """Build member_df from team/player tables in DB (single JOIN query)."""
    rows = player_repo.get_all_players_with_team()
    return pd.DataFrame( rows ) if rows else None


# --- ページ設定・スタイル ---
st.set_page_config( page_title = "Tsukuba PSS", page_icon = "assets/tsukuba_logo.png", layout = "wide" )
st.markdown("""
<style>
#MainMenu, footer, header { visibility: hidden; }
.block-container { padding-top: 0rem !important; padding-bottom: 0rem !important; }
</style>
""", unsafe_allow_html=True)

init_session()
ensure_db()

page = st.session_state.get("page_ctg", "start")

# --- メンバーデータ（DB）---
if st.session_state["member_df"] is None and page != "db_admin":
    st.session_state["member_df"] = load_member_df_from_db()

if st.session_state["member_df"] is None and page not in ("main", "db_admin"):
    st.info("チーム・選手を登録してください。")

member_df = st.session_state["member_df"]

# --- ページルーティング ---
if st.session_state.page_ctg == "start":
    # ── 接続状態インジケータ ──
    if schema.is_postgres():
        st.success( "🌐 Supabase (PostgreSQL) に接続中" )
    else:
        st.warning( "⚠️ ローカル SQLite を使用中（Supabase に接続されていません）" )

    st.divider()

    # ── メインアクション ──
    has_teams = bool( player_repo.list_teams() )
    has_games = bool( game_repo.list_games() )

    col1, col2, col3 = st.columns( 3 )
    with col1:
        st.markdown( "#### ▶️ 試合開始" )
        st.caption( "チーム・メンバーを設定して試合を記録します" )
        if st.button( "試合開始", disabled = not has_teams, use_container_width = True, type = "primary" ):
            st.session_state.page_ctg = "member"
            st.session_state.game_start = "start"
            # 前試合のスタメンロード済みフラグをリセット（新試合でDBから再読み込みさせる）
            for _k in ["_stamem_loaded_top", "_stamem_loaded_bottom"]:
                st.session_state.pop(_k, None)
            st.rerun()
        if not has_teams:
            st.caption( "※ 先にチーム・選手登録が必要です" )
    with col2:
        st.markdown( "#### 📝 入力再開" )
        st.caption( "中断した試合の記録を続けます" )
        if st.button( "入力再開", disabled = not has_games, use_container_width = True ):
            st.session_state["pending_game_select"] = True
            st.rerun()
    with col3:
        st.markdown( "#### 🗄️ データ確認" )
        st.caption( "記録データの確認・CSV保存を行います" )
        if st.button( "データベース確認・CSV保存", use_container_width = True ):
            st.session_state.page_ctg = "db_admin"
            st.rerun()

    if st.session_state.get( "pending_game_select" ):
        games = game_repo.list_games()
        if games:
            st.divider()
            st.caption( "試合を選んで「この試合を再開」を押すと、最後の入力行から再開できます。" )
            opts = [ f"{r[1]} {r[2]} {r[3]} {r[4]} vs {r[5]}" for r in games ]
            idx = st.selectbox( "続きを行う試合を選択", range( len( opts ) ), format_func = lambda i: opts[ i ] )
            if st.button( "この試合を再開", type = "primary" ):
                gid = games[ idx ][ 0 ]
                st.session_state[ "all_list" ] = game_repo.get_play_list( gid )
                st.session_state[ "current_game_id" ] = gid
                st.session_state.page_ctg = "main"
                st.session_state.game_start = "continue"
                if "temp_list" in st.session_state:
                    del st.session_state[ "temp_list" ]
                del st.session_state[ "pending_game_select" ]
                st.rerun()
        else:
            st.session_state[ "pending_game_select" ] = False

    st.divider()

    # ── 使い方ガイド ──
    with st.expander( "📖 使い方ガイド（クリックで展開）", expanded = False ):
        g_tab1, g_tab2, g_tab3, g_tab4 = st.tabs( [ "🔰 基本操作", "📋 入力データ一覧", "⚙️ メニュー機能", "💾 データ出力" ] )

        with g_tab1:
            st.markdown( """
#### 初回セットアップ
1. 「チーム・選手登録」でチーム名を登録（例：筑波大学）
2. チームごとに選手を登録（背番号・氏名・投打の左右）
3. 9人以上登録すると「試合開始」ボタンが有効になります

#### 試合開始の手順
1. **「試合開始」**ボタンを押す → 試合情報入力画面へ
2. 試合情報（日時・シーズン・大会種別など）を入力
3. 先攻・後攻チームを選択してスタメンを入力
4. 「確定」でデータ入力画面へ移動
5. 画面上部の **メニュータブ** を開き **「▶ 試合開始（開始時刻を記録）」を必ず押す**
   - ⚠️ これを押さないと経過時間が記録されません

#### データ入力の1球の流れ
```
① 構え（打者の立ち位置）を選択
   └ コースマップをクリックして投球コースを入力（✔が表示されたら入力済み）

② 球種を選択
   FB=ストレート / CB=カーブ / SL=スライダー / CT=カット /
   ST=シンカー / 2S=ツーシーム / CH=チェンジアップ / SP=スプリット / SK=シュート

③ 打撃結果カテゴリを選択（continue/K/BB/outs/hits/miss/sacrifice）
   └ 詳細結果（見逃し・空振り・単打 etc）を選択

④ 必要に応じて追加項目を選択
   └ 打撃結果2（PB/WP/ボーク等）・プレス・捕手牽制・作戦

⑤ ランナー状況を選択（走者がいる場合）
   └ 各走者の進塁先・アウト等を選択

⑥ 打球情報を入力（ヒット・凡打時）
   └ 打球種類（G/L/F）・強度（A/B/C）・捕球選手番号
   └ フィールドマップをクリックして打球位置を入力（✔が表示されたら入力済み）

⑦ 球速を入力（十の位 + 一の位で入力）

⑧ 「記録」ボタンを押して確定
```

#### 中断・再開
- 入力を途中でやめても自動でDBに保存されています
- スタート画面の **「入力再開」** ボタンから試合を選んで続きから再開できます
""" )

        with g_tab2:
            st.markdown( "#### 毎球入力できるデータ一覧" )
            col_d1, col_d2 = st.columns( 2 )
            with col_d1:
                st.markdown( """
**🎯 投球関連**
| 項目 | 内容 |
|------|------|
| 構え | 打者の立ち位置（3高/3中/3低/中高/中中/中低/1高/1中/1低） |
| コース | マップクリックで入力（25マス） |
| 球種 | FB/CB/SL/CT/ST/2S/CH/SP/SK/OT |
| 球速 | km/h（65〜199の範囲） |

**⚾ 打撃結果**
| カテゴリ | 選択肢 |
|---------|--------|
| continue | 見逃し・空振り・ファール・ボール |
| K | 見逃し三振・空振り三振・振り逃げ・K3 |
| BB | 四球・死球 |
| outs | 凡打死・凡打出塁・ファールフライ |
| hits | 単打・二塁打・三塁打・本塁打 |
| miss | エラー・野手選択・犠打失策 |
| sacrifice | 犠打・犠飛・犠打失策 |

**➕ 打撃結果2**
- PB（パスボール）・WP（ワイルドピッチ）
- 守備妨害・打撃妨害・走塁妨害・ボーク
""" )
            with col_d2:
                st.markdown( """
**🏃 走塁関連**
| 項目 | 内容 |
|------|------|
| ランナー状況（各走者） | 継続・二進・三進・本進・封殺・投手牽制死・捕手牽制死 |
| 作戦 | 盗塁・バント・エンドラン |
| 作戦詳細 | ディレード・Wスチール / セフティ・スクイズ・バスター / HAR・RAH等 |
| 作戦結果 | 成功・失敗・盗塁成功 |

**🤜 打球関連**
| 項目 | 内容 |
|------|------|
| 打球種類 | G（ゴロ）・L（ライナー）・F（フライ） |
| 打球強度 | A（強）・B（中）・C（弱） |
| 捕球選手 | 背番号（1〜9） |
| 打球位置 | フィールドマップクリックで入力 |

**📌 その他**
| 項目 | 内容 |
|------|------|
| プレス | 3プレス・1プレス・両プレス |
| 捕手牽制 | 1塁・2塁・3塁牽制 |
| エラー選手 | 背番号で指定 |
| 偽走 | 偽投等 |
""" )
            st.info( "💡 **スコアボードは自動更新されます。** 得点・H・E・K・BBは入力内容から自動集計されます。" )

        with g_tab3:
            st.markdown( """
#### メニュータブ（データ入力中に使用）

| ボタン | 機能 |
|--------|------|
| ▶ 試合開始（開始時刻を記録） | **試合開始時に必ず押す**。開始時刻と経過時間を記録 |
| 👤 選手交代 | メンバー入力画面に戻り、スタメンを変更できます |
| ↩ 1つ削除して戻る | 直前に入力した1球を取り消してDBからも削除します |
| 💾 CSV保存 | 現在の入力内容をCSVファイルとしてダウンロード |
| 🔄 画面再表示 | 画面をリフレッシュします |
| 🔧 状況変更 | イニング・得点・走者・カウントを手動で修正できます |
| 🏁 試合終了（スタートに戻る） | セッションをリセットしてスタートページに戻ります |

#### 🔧 状況変更 の詳細
入力ミスや自動計算のズレが生じた場合に手動修正できます：
- **イニング / 表裏** ： 現在のイニング・表裏を変更
- **先攻・後攻得点** ： 得点を直接書き換え
- **S / B / O** ： カウント・アウト数を修正
- **打順 / 1走〜3走** ： 打順や走者の打順番号を修正
- 「変更確定」を押すと反映されます
""" )

        with g_tab4:
            st.markdown( """
#### データ出力方法

**1. 試合中にCSV保存**
- メニュータブ → 「💾 CSV保存」でその時点のデータをCSVダウンロード

**2. 試合後に一括確認・ダウンロード**
- スタートページ → 「データベース確認・CSV保存」
- 試合一覧から対象試合を選択して全データをCSV出力

**3. JSONバックアップ（自動）**
- 試合開始時に `data/game_{id}.json` が自動作成されます
- 1球入力するたびにJSONに追記されます（サーバー障害時のバックアップ）

#### 出力CSVに含まれる主な列
試合日時 / Season / Kind / Week / Day / GameNumber / 主審 / 先攻チーム / 後攻チーム /
回 / 表裏 / 先攻得点 / 後攻得点 / S / B / アウト /
打順 / 打者氏名 / 打席左右 / 投手氏名 / 投手左右 / 球数 /
コースX / コースY / 球種 / 球速 /
打撃結果 / 打撃結果2 / 打球タイプ / 打球強度 / 捕球選手 / 打球位置X / 打球位置Y /
一走〜三走 状況・氏名・打順 / 作戦 / 作戦2 / 作戦結果 / プレス /
先攻打順 / 後攻打順 / 経過時間 / 開始時刻 / 現在時刻 / 他
""" )

    with st.expander("チーム・選手登録"):
        bulk_ok = st.session_state.pop("bulk_add_success", None)
        if bulk_ok:
            team_name, count = bulk_ok
            st.success(f"選手を一括追加しました：{team_name} に {count} 件登録しました。")
        teams = player_repo.list_teams()
        team_names = [t[1] for t in teams]
        new_team = st.text_input("新規チーム名（大学名など）")
        if st.button("チームを追加") and new_team and new_team.strip():
            player_repo.ensure_team(new_team.strip())
            st.session_state["member_df"] = None
            st.rerun()
        st.write("**選手を登録**（チーム・背番号・名前・左右）")
        if team_names:
            dup = st.session_state.get("player_add_duplicate")
            if dup:
                sel_d, p_num_d, p_name_d, p_lr_d, existing_name = dup
                st.warning(f"背番号 {p_num_d} は既に「{existing_name}」が登録されています。元の選手を削除して登録しますか？")
                dc1, dc2 = st.columns(2)
                with dc1:
                    if st.button("削除して登録する", key="replace_confirm"):
                        tid = player_repo.get_team_id_by_name(sel_d)
                        if tid is not None:
                            player_repo.delete_player(tid, p_num_d)
                            player_repo.add_player(tid, p_num_d, p_name_d, p_lr_d)
                        del st.session_state["player_add_duplicate"]
                        st.session_state["member_df"] = None
                        st.success(f"{sel_d} に {p_name_d} を登録しました（置き換え）")
                        st.rerun()
                with dc2:
                    if st.button("キャンセル", key="replace_cancel"):
                        del st.session_state["player_add_duplicate"]
                        st.rerun()
            sel = st.selectbox("チーム", team_names)
            c1, c2, c3 = st.columns(3)
            with c1:
                p_num = st.text_input("背番号", key="reg_num")
            with c2:
                p_name = st.text_input("名前", key="reg_name")
            with c3:
                p_lr = st.selectbox("左右", ["右", "左"], key="reg_lr")
            if st.button("選手を追加") and sel and str(p_num or "").strip() and str(p_name or "").strip():
                tid = player_repo.get_team_id_by_name(sel)
                if tid is not None:
                    existing = player_repo.get_player_by_number(tid, str(p_num).strip())
                    if existing:
                        st.session_state["player_add_duplicate"] = (
                            sel, str(p_num).strip(), str(p_name).strip(), p_lr, existing[0]
                        )
                        st.rerun()
                    else:
                        player_repo.add_player(tid, str(p_num).strip(), str(p_name).strip(), p_lr)
                        st.session_state["member_df"] = None
                        st.success(f"{sel} に {p_name} を登録しました")
                        st.rerun()
            st.write("**選手を一括追加**（1行1人: 背番号,名前,左右）")
            st.caption("例: 1,山田太郎,右　または 2,鈴木一郎,左（左右省略時は右）")
            bulk_text = st.text_area("選手一覧", height=120, key="bulk_players", placeholder="1,山田,右\n2,鈴木,左")
            if st.button("一括追加") and bulk_text.strip():
                tid = player_repo.get_team_id_by_name(sel)
                if tid is not None:
                    rows = []
                    for line in bulk_text.strip().splitlines():
                        line = line.strip()
                        if not line:
                            continue
                        parts = [p.strip() for p in line.replace("\t", ",").split(",") if p.strip()]
                        if len(parts) >= 2:
                            背番号, 名前 = parts[0], parts[1]
                            左右 = parts[2] if len(parts) >= 3 and parts[2] in ("右", "左") else "右"
                            rows.append((背番号, 名前, 左右))
                    if rows:
                        n = player_repo.add_players_bulk(tid, rows)
                        st.session_state["member_df"] = None
                        st.session_state["bulk_add_success"] = (sel, n)
                        st.rerun()
                    else:
                        st.warning("有効な行がありません。背番号,名前,左右 の形式で入力してください。")
        else:
            st.info("先にチームを追加してください。")

elif st.session_state.page_ctg == "member":
    if member_df is None:
        st.warning("チームに選手が登録されていません。下の「スタートへ」で戻り、チーム・選手登録で選手を追加してください。")
        if st.button("スタートへ"):
            st.session_state.page_ctg = "start"
            st.rerun()
        st.stop()

    from config import (
        DEFAULT_BOTTOM_LRS, DEFAULT_BOTTOM_NAMES, DEFAULT_BOTTOM_NUMS, DEFAULT_BOTTOM_POSES,
        DEFAULT_TOP_LRS, DEFAULT_TOP_NAMES, DEFAULT_TOP_NUMS, DEFAULT_TOP_POSES,
    )
    initial_top_poses = DEFAULT_TOP_POSES.copy()
    initial_top_names = DEFAULT_TOP_NAMES.copy()
    initial_top_nums = DEFAULT_TOP_NUMS.copy()
    initial_top_lrs = DEFAULT_TOP_LRS.copy()
    initial_bottom_poses = DEFAULT_BOTTOM_POSES.copy()
    initial_bottom_names = DEFAULT_BOTTOM_NAMES.copy()
    initial_bottom_nums = DEFAULT_BOTTOM_NUMS.copy()
    initial_bottom_lrs = DEFAULT_BOTTOM_LRS.copy()

    if st.session_state.game_start == "start":
        if "temp_list" not in st.session_state:
            from config import build_initial_temp_list
            st.session_state.temp_list = build_initial_temp_list()

        先攻チーム, 後攻チーム, updated_top_poses, updated_top_names, updated_top_nums, updated_top_lrs, updated_bottom_poses, updated_bottom_names, updated_bottom_nums, updated_bottom_lrs = member.member_page(
            member_df, initial_top_poses, initial_top_names, initial_top_nums, initial_top_lrs,
            initial_bottom_poses, initial_bottom_names, initial_bottom_nums, initial_bottom_lrs,
            "先攻チーム", "後攻チーム", "開始前", None
        )
        t = st.session_state.temp_list
        t[78:86] = updated_top_poses, updated_top_names, updated_top_nums, updated_top_lrs, updated_bottom_poses, updated_bottom_names, updated_bottom_nums, updated_bottom_lrs
        t[7:9] = 後攻チーム, 先攻チーム
        t[27], t[28], t[32], t[33], t[35] = initial_top_names[0], initial_top_lrs[0], initial_bottom_names[9], initial_bottom_lrs[9], initial_bottom_names[10]
        t[0] = datetime.today().strftime("%Y/%m/%d")
        t[1] = str(st.session_state.get("game_Season") or "")
        t[2] = str(st.session_state.get("game_Kind") or "")
        t[3] = str(st.session_state.get("game_Week") or "")
        t[4] = str(st.session_state.get("game_Day") or "")
        t[5] = str(st.session_state.get("game_GameNumber") or "")
        t[6] = str(st.session_state.get("game_主審") or "")

    elif st.session_state.game_start == "continue":
        if not st.session_state["all_list"]:
            st.session_state.page_ctg = "start"
            st.session_state["pending_game_select"] = True
            st.rerun()
        if "temp_list" not in st.session_state:
            st.session_state.temp_list = st.session_state["all_list"][-1]

        tl = st.session_state.temp_list
        後攻チーム, 先攻チーム, 表裏 = tl[7], tl[8], tl[11]
        top_poses_d, top_names_d, top_nums_d, top_lrs_d = tl[78:82]
        bottom_poses_d, bottom_names_d, bottom_nums_d, bottom_lrs_d = tl[82:86]

        先攻チーム, 後攻チーム, updated_top_poses, updated_top_names, updated_top_nums, updated_top_lrs, updated_bottom_poses, updated_bottom_names, updated_bottom_nums, updated_bottom_lrs = member.member_page(
            member_df, top_poses_d, top_names_d, top_nums_d, top_lrs_d,
            bottom_poses_d, bottom_names_d, bottom_nums_d, bottom_lrs_d,
            先攻チーム, 後攻チーム, 表裏, ""
        )
        st.session_state.temp_list[78:86] = updated_top_poses, updated_top_names, updated_top_nums, updated_top_lrs, updated_bottom_poses, updated_bottom_names, updated_bottom_nums, updated_bottom_lrs
        st.session_state.temp_list[7:9] = 後攻チーム, 先攻チーム
        st.session_state["already_rerun"] = False

elif st.session_state.page_ctg == "db_admin":
    db_admin.run()

elif st.session_state.page_ctg == "main":
    all_list = st.session_state["all_list"]
    if "temp_list" not in st.session_state:
        if all_list:
            st.session_state.temp_list = all_list[-1].copy()
        else:
            from config import build_initial_temp_list
            t = build_initial_temp_list()
            gid = st.session_state.get("current_game_id")
            if gid:
                先攻, 後攻 = game_repo.get_game_teams(gid)
                if 先攻 and 後攻:
                    t[7], t[8] = 後攻, 先攻
            st.session_state.temp_list = t
    st.session_state.game_start = "continue"
    st.session_state.temp_list = main_page.main_page(st.session_state.temp_list)


