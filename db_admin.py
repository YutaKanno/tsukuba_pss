"""
DB inspection and CSV export page.
"""
import io
import zipfile

import pandas as pd
import streamlit as st

from config import COLUMN_NAMES
from db import game_repo, player_repo, schema, user_repo


def _get_admin_password() -> str:
    """Return admin password from Secrets or env var (default: 'admin')."""
    import os
    try:
        pw = st.secrets.get("DB_ADMIN_PASSWORD")
        if pw:
            return str(pw)
    except Exception:
        pass
    return os.environ.get("DB_ADMIN_PASSWORD", "admin")


def run() -> None:
    st.title("データベース確認・CSV保存")

    # ── パスワード認証 ──
    if not st.session_state.get("db_admin_authenticated"):
        st.caption("このページはパスワードが必要です。")
        pw_input = st.text_input("パスワード", type="password", key="db_admin_pw_input")
        if st.button("ログイン", key="db_admin_login_btn"):
            if pw_input == _get_admin_password():
                st.session_state["db_admin_authenticated"] = True
                st.rerun()
            else:
                st.error("パスワードが正しくありません。")
        return

    col_title, col_logout = st.columns([8, 1])
    with col_title:
        st.caption("DBの内容を確認し、試合を選んで game_data.csv 形式でダウンロードできます。")
    with col_logout:
        if st.button("ログアウト", key="db_admin_logout_btn"):
            st.session_state.pop("db_admin_authenticated", None)
            st.rerun()

    tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs([
        "チーム一覧", "選手一覧", "スタメン", "試合一覧", "試合をCSVで保存", "試合削除", "選手削除", "ユーザー管理"
    ])

    with tab1:
        st.subheader("チーム一覧")
        teams = player_repo.list_teams()
        if not teams:
            st.info("チームがまだ登録されていません。")
        else:
            df_team = pd.DataFrame(teams, columns=["id", "名前"])
            st.dataframe(df_team, use_container_width=True)
            st.caption(f"計 {len(teams)} チーム")

    with tab2:
        st.subheader("選手一覧")
        teams = player_repo.list_teams()
        if not teams:
            st.info("先にチームを登録してください。")
        else:
            team_names = [t[1] for t in teams]
            sel = st.selectbox("チームを選択", team_names, key="db_admin_team_sel")
            if sel:
                tid = player_repo.get_team_id_by_name(sel)
                if tid is not None:
                    rows = player_repo.get_players_by_team(tid)
                    if not rows:
                        st.info("このチームに選手登録がありません。")
                    else:
                        df = pd.DataFrame(rows, columns=["背番号", "名前", "左右"])
                        st.dataframe(df, use_container_width=True)
                        st.caption(f"計 {len(rows)} 名")

    with tab3:
        st.subheader("スタメン記憶（チーム別）")
        teams = player_repo.list_teams()
        if not teams:
            st.info("チームがまだ登録されていません。")
        else:
            team_names = [t[1] for t in teams]
            sel = st.selectbox("チームを選択", team_names, key="db_admin_stamem_sel")
            if sel:
                stamem = player_repo.get_stamem_by_team_name(sel)
                if stamem is None:
                    st.info("このチームのスタメンは未保存です。")
                else:
                    poses = stamem["poses"]
                    names = stamem["names"]
                    nums = stamem["nums"]
                    lrs = stamem["lrs"]
                    n = max(len(poses), len(names), len(nums), len(lrs), 1)
                    table_data = [
                        {"打順": i + 1, "ポジション": poses[i] if i < len(poses) else "", "名前": names[i] if i < len(names) else "", "背番号": nums[i] if i < len(nums) else "", "左右": lrs[i] if i < len(lrs) else ""}
                        for i in range(n)
                    ]
                    if table_data:
                        st.dataframe(pd.DataFrame(table_data), use_container_width=True)
                    else:
                        st.caption("スタメンデータが空です。")

    with tab4:
        st.subheader("試合一覧")
        games = game_repo.list_games(limit=500)
        if not games:
            st.info("試合がまだありません。")
        else:
            df_games = pd.DataFrame(
                games,
                columns=["id", "試合日時", "Season", "Kind", "先攻", "後攻"]
            )
            st.dataframe(df_games, use_container_width=True)
            st.caption(f"直近 {len(games)} 試合（新しい順）")

    with tab5:
        st.subheader("試合を選んでCSV保存")
        games = game_repo.list_games(limit=500)
        if not games:
            st.info("試合がまだありません。試合を開始してデータを入力すると保存できます。")
        else:
            options_csv = [f"{r[1]} {r[2]} {r[3]} {r[4]} vs {r[5]}" for r in games]

            c_all_csv, c_none_csv = st.columns(2)
            with c_all_csv:
                if st.button("全選択", key="csv_select_all"):
                    st.session_state["csv_selected"] = list(range(len(games)))
            with c_none_csv:
                if st.button("全解除", key="csv_select_none"):
                    st.session_state["csv_selected"] = []

            selected_csv = st.multiselect(
                "CSVにしたい試合を選択（複数可）",
                options=list(range(len(games))),
                default=st.session_state.get("csv_selected", []),
                format_func=lambda i: options_csv[i],
                key="db_admin_csv_games",
            )
            st.session_state["csv_selected"] = selected_csv

            if selected_csv:
                st.caption(f"{len(selected_csv)} 試合を選択中")
                if len(selected_csv) == 1:
                    # 1試合 → 単一CSV
                    idx = selected_csv[0]
                    gid = games[idx][0]
                    play_list = game_repo.get_play_list(gid)
                    if not play_list:
                        st.warning("この試合にはまだ1球もデータがありません。")
                    else:
                        df = pd.DataFrame(play_list, columns=COLUMN_NAMES)
                        buf = io.BytesIO(df.to_csv(index=False).encode("utf-8-sig"))
                        file_name = f"game_data_{gid}_{games[idx][1].replace('/', '-')}.csv"
                        st.download_button(
                            label="CSVでダウンロード",
                            data=buf,
                            file_name=file_name,
                            mime="text/csv",
                            key="db_admin_dl_btn_single",
                        )
                        st.caption(f"プレイ数: {len(play_list)} 件")
                else:
                    # 複数試合 → ZIP
                    zip_buf = io.BytesIO()
                    total_plays = 0
                    empty_games = []
                    with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
                        for idx in selected_csv:
                            gid = games[idx][0]
                            play_list = game_repo.get_play_list(gid)
                            if not play_list:
                                empty_games.append(options_csv[idx])
                                continue
                            df = pd.DataFrame(play_list, columns=COLUMN_NAMES)
                            csv_bytes = df.to_csv(index=False).encode("utf-8-sig")
                            fname = f"game_data_{gid}_{games[idx][1].replace('/', '-')}.csv"
                            zf.writestr(fname, csv_bytes)
                            total_plays += len(play_list)
                    zip_buf.seek(0)
                    if empty_games:
                        st.warning(f"以下の試合はデータが0件のためZIPに含まれません:\n" + "\n".join(f"- {g}" for g in empty_games))
                    st.download_button(
                        label=f"選択した {len(selected_csv)} 試合をZIPでダウンロード",
                        data=zip_buf,
                        file_name="game_data_bulk.zip",
                        mime="application/zip",
                        key="db_admin_dl_btn_zip",
                    )
                    st.caption(f"合計プレイ数: {total_plays} 件")

    with tab6:
        st.subheader("試合削除")
        games = game_repo.list_games(limit=500)
        if not games:
            st.info("削除できる試合がまだありません。")
        else:
            options_del = [f"{r[1]} {r[2]} {r[3]} {r[4]} vs {r[5]}" for r in games]

            c_all_del, c_none_del = st.columns(2)
            with c_all_del:
                if st.button("全選択", key="del_select_all"):
                    st.session_state["del_selected"] = list(range(len(games)))
            with c_none_del:
                if st.button("全解除", key="del_select_none"):
                    st.session_state["del_selected"] = []

            selected_del = st.multiselect(
                "削除したい試合を選択（複数可）",
                options=list(range(len(games))),
                default=st.session_state.get("del_selected", []),
                format_func=lambda i: options_del[i],
                key="db_admin_del_games",
            )
            st.session_state["del_selected"] = selected_del

            if selected_del:
                st.caption(f"{len(selected_del)} 試合を選択中")
                st.warning(
                    f"選択した **{len(selected_del)} 試合** と紐づく全ての毎球データが完全に削除されます。"
                    "元に戻すことはできません。"
                )
                col_del1, col_del2 = st.columns(2)
                with col_del1:
                    if st.button(f"本当に {len(selected_del)} 試合を削除する", key="db_admin_del_confirm", type="primary"):
                        deleted = 0
                        for idx in selected_del:
                            game_repo.delete_game(games[idx][0])
                            deleted += 1
                        st.session_state.pop("del_selected", None)
                        st.success(f"{deleted} 試合を削除しました。")
                        st.rerun()
                with col_del2:
                    if st.button("キャンセル", key="db_admin_del_cancel"):
                        st.session_state.pop("del_selected", None)
                        st.rerun()

    with tab7:
        st.subheader("選手削除")
        teams = player_repo.list_teams()
        if not teams:
            st.info("チームがまだ登録されていません。")
        else:
            team_names = [t[1] for t in teams]
            sel_team = st.selectbox("チームを選択", team_names, key="db_admin_del_player_team")
            if sel_team:
                tid = player_repo.get_team_id_by_name(sel_team)
                if tid is not None:
                    rows = player_repo.get_players_by_team(tid)
                    if not rows:
                        st.info("このチームに選手登録がありません。")
                    else:
                        options_p = [f"{r[0]} {r[1]}（{r[2]}）" for r in rows]

                        cp_all, cp_none = st.columns(2)
                        with cp_all:
                            if st.button("全選択", key="del_player_all"):
                                st.session_state["del_player_selected"] = list(range(len(rows)))
                        with cp_none:
                            if st.button("全解除", key="del_player_none"):
                                st.session_state["del_player_selected"] = []

                        selected_players = st.multiselect(
                            "削除したい選手を選択（複数可）",
                            options=list(range(len(rows))),
                            default=st.session_state.get("del_player_selected", []),
                            format_func=lambda i: options_p[i],
                            key="db_admin_del_players",
                        )
                        st.session_state["del_player_selected"] = selected_players

                        if selected_players:
                            st.caption(f"{len(selected_players)} 名を選択中")
                            st.warning(
                                f"選択した **{len(selected_players)} 名** を削除します。元に戻すことはできません。"
                            )
                            col_dp1, col_dp2 = st.columns(2)
                            with col_dp1:
                                if st.button(f"本当に {len(selected_players)} 名を削除する", key="db_admin_del_player_confirm", type="primary"):
                                    for idx in selected_players:
                                        player_repo.delete_player(tid, rows[idx][0])
                                    st.session_state.pop("del_player_selected", None)
                                    st.session_state["member_df"] = None
                                    st.success(f"{len(selected_players)} 名を削除しました。")
                                    st.rerun()
                            with col_dp2:
                                if st.button("キャンセル", key="db_admin_del_player_cancel"):
                                    st.session_state.pop("del_player_selected", None)
                                    st.rerun()

    with tab8:
        st.subheader("ユーザー管理")
        teams = player_repo.list_teams()
        if not teams:
            st.info("チームがまだ登録されていません。")
        else:
            team_names = [t[1] for t in teams]
            sel_ut = st.selectbox("チームを選択", team_names, key="db_admin_user_team_sel")
            if sel_ut:
                tid = player_repo.get_team_id_by_name(sel_ut)
                if tid is not None:
                    users = user_repo.list_users_by_team(tid)
                    if not users:
                        st.info("このチームにユーザーが登録されていません。")
                    else:
                        df_users = pd.DataFrame(users, columns=["id", "ユーザー名", "登録日時"])
                        st.dataframe(df_users[["ユーザー名", "登録日時"]], use_container_width=True)
                        st.caption(f"計 {len(users)} ユーザー")

                        st.divider()
                        st.write("**ユーザーを削除**")
                        user_opts = [u[1] for u in users]
                        del_uname = st.selectbox("削除するユーザー", user_opts, key="db_admin_del_user_sel")
                        if st.button("このユーザーを削除", key="db_admin_del_user_btn", type="primary"):
                            target = next((u for u in users if u[1] == del_uname), None)
                            if target:
                                user_repo.delete_user(target[0])
                                st.success(f"ユーザー「{del_uname}」を削除しました。")
                                st.rerun()

    st.write("---")
    if st.button("スタート画面に戻る"):
        st.session_state.page_ctg = "start"
        st.rerun()
