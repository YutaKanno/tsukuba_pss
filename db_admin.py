"""
DB inspection and CSV export page.
"""
import io

import pandas as pd
import streamlit as st

from config import COLUMN_NAMES
from db import game_repo, player_repo, schema


def run() -> None:
    st.title("データベース確認・CSV保存")
    st.caption("DBの内容を確認し、試合を選んで game_data.csv 形式でダウンロードできます。")

    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "チーム一覧", "選手一覧", "スタメン", "試合一覧", "試合をCSVで保存", "試合削除"
    ])

    with tab1:
        st.subheader("チーム一覧")
        teams = player_repo.list_teams()
        if not teams:
            st.info("チームがまだ登録されていません。")
        else:
            df_team = pd.DataFrame(teams, columns=["id", "名前"])
            st.dataframe(df_team, width="stretch")
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
                        st.dataframe(df, width="stretch")
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
                        st.dataframe(pd.DataFrame(table_data), width="stretch")
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
                columns=["id", "試合日時", "Season", "先攻", "後攻"]
            )
            st.dataframe(df_games, width="stretch")
            st.caption(f"直近 {len(games)} 試合（新しい順）")

    with tab5:
        st.subheader("試合を選んでCSV保存")
        games = game_repo.list_games(limit=500)
        if not games:
            st.info("試合がまだありません。試合を開始してデータを入力すると保存できます。")
        else:
            options = [f"id:{r[0]} — {r[1]} {r[2]} vs {r[3]}" for r in games]
            idx = st.selectbox(
                "CSVにしたい試合を選択",
                range(len(options)),
                format_func=lambda i: options[i],
                key="db_admin_csv_game"
            )
            if idx is not None:
                gid = games[idx][0]
                play_list = game_repo.get_play_list(gid)
                if not play_list:
                    st.warning("この試合にはまだ1球もデータがありません。")
                else:
                    df = pd.DataFrame(play_list, columns=COLUMN_NAMES)
                    csv_str = df.to_csv(index=False)
                    csv_bytes = csv_str.encode("utf-8-sig")
                    buf = io.BytesIO(csv_bytes)
                    file_name = f"game_data_{gid}_{games[idx][1].replace('/', '-')}.csv"
                    st.download_button(
                        label="この試合をCSVでダウンロード",
                        data=buf,
                        file_name=file_name,
                        mime="text/csv",
                        key="db_admin_dl_btn"
                    )
                    st.caption(f"プレイ数: {len(play_list)} 件")

    with tab6:
        st.subheader("試合削除")
        games = game_repo.list_games(limit=500)
        if not games:
            st.info("削除できる試合がまだありません。")
        else:
            options = [f"id:{r[0]} — {r[1]} {r[2]} vs {r[3]}" for r in games]
            idx = st.selectbox(
                "削除したい試合を選択",
                range(len(options)),
                format_func=lambda i: options[i],
                key="db_admin_del_game"
            )
            if idx is not None:
                gid = games[idx][0]
                st.warning("この試合と紐づく全ての毎球データが完全に削除されます。元に戻すことはできません。")
                col_del1, col_del2 = st.columns(2)
                with col_del1:
                    if st.button("本当に削除する", key="db_admin_del_confirm"):
                        game_repo.delete_game(gid)
                        st.success("選択した試合を削除しました。")
                        st.rerun()
                with col_del2:
                    if st.button("キャンセル", key="db_admin_del_cancel"):
                        st.info("削除をキャンセルしました。")

    st.write("---")
    if st.button("スタート画面に戻る"):
        st.session_state.page_ctg = "start"
        st.rerun()
