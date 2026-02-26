"""
Member and lineup input page. Uses db.player_repo / db.schema (app_data.db).
"""
import json
import os

import pandas as pd
import streamlit as st

from config import (
    DEFAULT_BOTTOM_LRS, DEFAULT_BOTTOM_NAMES, DEFAULT_BOTTOM_NUMS, DEFAULT_BOTTOM_POSES,
    DEFAULT_TOP_LRS, DEFAULT_TOP_NAMES, DEFAULT_TOP_NUMS, DEFAULT_TOP_POSES,
)


def get_member_data( 大学名 ):
    """指定された大学のスタメンデータを取得。app_data.db の stamem を使用。"""
    try:
        from db import player_repo
        m = player_repo.get_stamem_by_team_name( 大学名 )
        if m:
            return {'大学名': 大学名, **m}
    except Exception:
        pass
    return None


def member_page( member_df, top_poses, top_names, top_nums, top_lrs, bottom_poses, bottom_names, bottom_nums, bottom_lrs, 先攻チーム, 後攻チーム, 表裏, mr ): # member_re_file パラメータは削除されました。
    # 初期選択のためにデータベースから大学のリストを取得します。
    team_list = member_df["大学名"].unique()

    from db import player_repo as _player_repo

    # 試合情報の入力（試合開始時のみ）
    if st.session_state.game_start == "start":
        _SEASON_OPTIONS = ["春季", "夏季", "秋季", "冬季"]
        _KIND_OPTIONS = [
            "全国大会", "関東大会", "リーグ戦", "準公式戦",
            "Aオープン戦", "Bオープン戦", "Cオープン戦",
            "A紅白戦", "B紅白戦", "C紅白戦",
            "部内リーグ", "その他",
        ]
        _GAME_NUMBER_OPTIONS = [0, 1, 2, 3, 4]
        _WEEK_OPTIONS = list(range(0, 13))
        _DAY_OPTIONS = [0, 1, 2, 3, 4]

        default_date = (st.session_state.get("temp_list") or [None])[0] or ""
        if "game_試合日時" not in st.session_state:
            st.session_state.game_試合日時 = default_date
        if "game_主審" not in st.session_state:
            st.session_state.game_主審 = ""

        with st.expander("試合情報", expanded=True):
            c1, c2, c3, c4, c5, c6, c7 = st.columns(7)
            with c1:
                st.text_input("日時", value=st.session_state.game_試合日時, key="game_試合日時", placeholder="2025/03/15")
            with c2:
                st.text_input("主審", value=st.session_state.game_主審, key="game_主審")
            with c3:
                st.selectbox("Season", _SEASON_OPTIONS, key="game_Season")
            with c4:
                kind_sel = st.selectbox("Kind", _KIND_OPTIONS, key="game_Kind_sel")
                if kind_sel == "その他":
                    st.text_input("Kind入力", key="game_Kind")
                else:
                    st.session_state["game_Kind"] = kind_sel
            with c5:
                st.selectbox("Day", _DAY_OPTIONS, key="game_Day")
            with c6:
                st.selectbox("Week", _WEEK_OPTIONS, key="game_Week")
            with c7:
                st.selectbox("GN", _GAME_NUMBER_OPTIONS, key="game_GameNumber")

    with st.expander("選手を追加登録"):
        dup = st.session_state.get("member_add_duplicate")
        if dup:
            sel_d, p_num_d, p_name_d, p_lr_d, existing_name = dup
            st.warning(f"背番号 {p_num_d} は既に「{existing_name}」が登録されています。元の選手を削除して登録しますか？")
            mc1, mc2 = st.columns(2)
            with mc1:
                if st.button("削除して登録する", key="member_replace_confirm"):
                    tid = _player_repo.get_team_id_by_name(sel_d)
                    if tid is not None:
                        _player_repo.delete_player(tid, p_num_d)
                        _player_repo.add_player(tid, p_num_d, p_name_d, p_lr_d)
                    del st.session_state["member_add_duplicate"]
                    st.session_state["member_df"] = None
                    st.success(f"{sel_d} に {p_name_d} を登録しました（置き換え）")
                    st.rerun()
            with mc2:
                if st.button("キャンセル", key="member_replace_cancel"):
                    del st.session_state["member_add_duplicate"]
                    st.rerun()
        add_sel = st.selectbox("チーム", list(team_list), key="member_add_team")
        add_num = st.text_input("背番号", key="member_add_num")
        add_name = st.text_input("名前", key="member_add_name")
        add_lr = st.selectbox("左右", ["右", "左"], key="member_add_lr")
        if st.button("追加", key="member_add_btn") and add_sel and str(add_num or "").strip() and str(add_name or "").strip():
            tid = _player_repo.get_team_id_by_name(add_sel)
            if tid is not None:
                existing = _player_repo.get_player_by_number(tid, str(add_num).strip())
                if existing:
                    st.session_state["member_add_duplicate"] = (
                        add_sel, str(add_num).strip(), str(add_name).strip(), add_lr, existing[0]
                    )
                    st.rerun()
                else:
                    _player_repo.add_player(tid, str(add_num).strip(), str(add_name).strip(), add_lr)
                    st.session_state["member_df"] = None
                    st.success(f"{add_sel} に {add_name} を登録しました")
                    st.rerun()

    if "top_team" not in st.session_state:
        st.session_state.top_team = 先攻チーム
    if "bottom_team" not in st.session_state:
        st.session_state.bottom_team = 後攻チーム

    def _clear_lineup_widget_keys(prefix: str):
        """チーム変更時に固定keyウィジェットのキャッシュを削除し、新チームのDB値で再初期化させる"""
        for i in range(10):
            st.session_state.pop(f"{prefix}_num_{i}", None)
        for i in range(9):
            st.session_state.pop(f"{prefix}_pos_{i}", None)

    col1, col2 = st.columns(2)
    with col1:
        if st.session_state.game_start == "start":
            top_default_idx = 0
            if "top_team" in st.session_state and st.session_state.top_team in list(team_list):
                top_default_idx = list(team_list).index(st.session_state.top_team)
            prev_top = st.session_state.get("_prev_top_team")
            st.session_state.top_team = st.selectbox("先攻チーム", team_list, index=top_default_idx, key="select_top_team")
            if prev_top is not None and prev_top != st.session_state.top_team:
                _clear_lineup_widget_keys("top")
                st.session_state["_prev_top_team"] = st.session_state.top_team
                st.rerun()
            st.session_state["_prev_top_team"] = st.session_state.top_team
            mr_top = get_member_data(st.session_state.top_team)
            if mr_top:
                top_poses, top_names, top_nums, top_lrs = mr_top["poses"], mr_top["names"], mr_top["nums"], mr_top["lrs"]
            else:
                top_poses, top_names, top_nums, top_lrs = DEFAULT_TOP_POSES.copy(), DEFAULT_TOP_NAMES.copy(), DEFAULT_TOP_NUMS.copy(), DEFAULT_TOP_LRS.copy()
        else:
            st.session_state.top_team = st.session_state.temp_list[8]
            st.write(f"#### {st.session_state.top_team}")

        top_list = member_df[member_df['大学名'] == st.session_state.top_team].reset_index(drop=True)

        col11, col12, col13, col14 = st.columns([6, 2, 2, 5])

        with col11:
            st.dataframe(top_list[['背番号', '名前', '左右']], height=550)

        with col12:
            for i in range(9):
                if 表裏 == '表':
                    pos_list = [top_poses[i], 'H', 'R']
                else:
                    pos_list = [top_poses[i], 2, 3, 4, 5, 6, 7, 8, 9, 'D', 'P']

                top_poses[i] = st.selectbox(' ', pos_list, label_visibility='collapsed', key=f'top_pos_{i}')
            st.write('#### P')

        with col13:
            for i in range(10):
                top_nums[i] = st.text_input(' ', label_visibility='collapsed', key=f'top_num_{i}', value=top_nums[i])
                try:
                    num = str(top_nums[i])
                    matched = top_list[top_list['背番号'] == num]
                    if not matched.empty:
                        top_names[i] = matched.iloc[0]['名前']
                        top_lrs[i] = matched.iloc[0]['左右']
                    else:
                        top_names[i] = ''
                        top_lrs[i] = ''
                except ValueError:
                    top_names[i] = ''
                    top_lrs[i] = ''

        with col14:
            for i in range(10):
                # ユニーク key（チーム名＋背番号＋インデックス）
                key_name = f"top_{st.session_state.top_team}_{top_nums[i]}_{i}"
                
                # session_state に存在しなければ初期化
                if key_name not in st.session_state:
                    st.session_state[key_name] = top_names[i]

                # 背番号から名前を取得して更新
                num = str(top_nums[i])
                matched = top_list[top_list['背番号'] == num]
                if not matched.empty:
                    st.session_state[key_name] = matched.iloc[0]['名前']
                    top_lrs[i] = matched.iloc[0]['左右']
                else:
                    st.session_state[key_name] = ''
                    top_lrs[i] = ''

                # text_input には value を渡さず key だけ
                st.text_input(' ', label_visibility='collapsed', key=key_name)
                
                # 表示用の top_names に反映（必要なら）
                top_names[i] = st.session_state[key_name]

        # top_posesが2の名前を10番目に追加（names が 18 要素以上であること保証）
        while len(top_names) < 20:
            top_names.append("")
        for i in range(9):
            for j in range(8):
                if top_poses[i] == j+2:
                    top_names[j+10] = top_names[i]

    with col2:
        if st.session_state.game_start == "start":
            bottom_default_idx = min(1, len(team_list) - 1) if len(team_list) > 1 else 0
            if "bottom_team" in st.session_state and st.session_state.bottom_team in list(team_list):
                bottom_default_idx = list(team_list).index(st.session_state.bottom_team)
            prev_bottom = st.session_state.get("_prev_bottom_team")
            st.session_state.bottom_team = st.selectbox("後攻チーム", team_list, index=bottom_default_idx, key="select_bottom_team")
            if prev_bottom is not None and prev_bottom != st.session_state.bottom_team:
                _clear_lineup_widget_keys("bottom")
                st.session_state["_prev_bottom_team"] = st.session_state.bottom_team
                st.rerun()
            st.session_state["_prev_bottom_team"] = st.session_state.bottom_team
            mr_bottom = get_member_data(st.session_state.bottom_team)
            if mr_bottom:
                bottom_poses, bottom_names, bottom_nums, bottom_lrs = mr_bottom["poses"], mr_bottom["names"], mr_bottom["nums"], mr_bottom["lrs"]
            else:
                bottom_poses, bottom_names, bottom_nums, bottom_lrs = DEFAULT_BOTTOM_POSES.copy(), DEFAULT_BOTTOM_NAMES.copy(), DEFAULT_BOTTOM_NUMS.copy(), DEFAULT_BOTTOM_LRS.copy()
        else:
            st.session_state.bottom_team = st.session_state.temp_list[7]
            st.write(f"#### {st.session_state.bottom_team}")
        bottom_list = member_df[member_df['大学名'] == st.session_state.bottom_team].reset_index(drop=True)

        col21, col22, col23, col24 = st.columns([2, 2, 5, 6])

        with col24:
            st.dataframe(bottom_list[['背番号', '名前', '左右']], height=550)

        with col21:
            for i in range(9):
                if 表裏 == '裏':
                    pos_list2 = [bottom_poses[i], 'H', 'R']
                else:
                    pos_list2 = [bottom_poses[i], 2, 3, 4, 5, 6, 7, 8, 9, 'D', 'P']
                bottom_poses[i] = st.selectbox(' ', pos_list2, label_visibility='collapsed', key=f'bottom_pos_{i}')
            st.write('#### P')

        with col22:
            for i in range(10):
                bottom_nums[i] = st.text_input(' ', label_visibility='collapsed', key=f'bottom_num_{i}', value=bottom_nums[i])
                try:
                    num2 = str(bottom_nums[i])
                    matched2 = bottom_list[bottom_list['背番号'] == num2]
                    if not matched2.empty:
                        bottom_names[i] = matched2.iloc[0]['名前']
                        bottom_lrs[i] = matched2.iloc[0]['左右']
                    else:
                        bottom_names[i] = ''
                        bottom_lrs[i] = ''

                except ValueError:
                    bottom_names[i] = ''
                    bottom_lrs[i] = ''

        with col23:
            for i in range(10):
                # ユニーク key（チーム名＋背番号＋インデックス）
                key_name2 = f"bottom_{st.session_state.bottom_team}_{bottom_nums[i]}_{i}"
                
                # session_state に存在しなければ初期化
                if key_name2 not in st.session_state:
                    st.session_state[key_name2] = bottom_names[i]

                # 背番号から名前を取得して更新
                num = str(bottom_nums[i])
                matched = bottom_list[bottom_list['背番号'] == num]
                if not matched.empty:
                    st.session_state[key_name2] = matched.iloc[0]['名前']
                    bottom_lrs[i] = matched.iloc[0]['左右']
                else:
                    st.session_state[key_name2] = ''
                    bottom_lrs[i] = ''

                # text_input には value を渡さず key だけ
                st.text_input(' ', label_visibility='collapsed', key=key_name2)
                
                # 表示用の top_names に反映（必要なら）
                bottom_names[i] = st.session_state[key_name2]

        # bottom_posesが2の名前を10番目に追加（names が 18 要素以上であること保証）
        while len(bottom_names) < 20:
            bottom_names.append("")
        for i in range(9):
            for j in range(8):
                if bottom_poses[i] == j+2:
                    bottom_names[j+10] = bottom_names[i]

        if st.button("確定", key="member_confirm_btn"):
            from db import game_repo, player_repo
            # 確定押下時点のフォーム値を session_state から必ず取得して stamem に保存
            def _build_from_session(is_top: bool):
                prefix = "top" if is_top else "bottom"
                team_raw = (st.session_state.top_team if is_top else st.session_state.bottom_team) or ""
                team_raw = str(team_raw)
                team = team_raw.strip()
                poses = [st.session_state.get(f"{prefix}_pos_{i}") for i in range(9)]
                nums = [str(st.session_state.get(f"{prefix}_num_{i}", "") or "") for i in range(10)]
                names = []
                for i in range(10):
                    k = f"{prefix}_{team}_{nums[i]}_{i}"
                    val = str(st.session_state.get(k, "") or "")
                    if not val and team != team_raw:
                        k2 = f"{prefix}_{team_raw}_{nums[i]}_{i}"
                        val = str(st.session_state.get(k2, "") or "")
                    names.append(val)
                team_df = member_df[member_df["大学名"] == team].reset_index(drop=True)
                lrs = []
                for i in range(10):
                    n = nums[i]
                    if n and not team_df.empty:
                        m = team_df[team_df["背番号"].astype(str) == str(n)]
                        lrs.append(m.iloc[0]["左右"] if len(m) > 0 else "")
                    else:
                        lrs.append("")
                return poses, names, nums, lrs

            def _to_save_lists(poses, names, nums, lrs):
                p = [(x if x is not None else 2) for x in (poses[:9] if len(poses) >= 9 else list(poses) + [2] * (9 - len(poses)))]
                n = [str(x) if x is not None else "" for x in (names[:10] if len(names) >= 10 else list(names) + [""] * (10 - len(names)))]
                num = [str(x) if x is not None else "" for x in (nums[:10] if len(nums) >= 10 else list(nums) + [""] * (10 - len(nums)))]
                l = [str(x) if x is not None else "" for x in (lrs[:10] if len(lrs) >= 10 else list(lrs) + [""] * (10 - len(lrs)))]
                return p, n, num, l

            try:
                top_poses_raw, top_names_raw, top_nums_raw, top_lrs_raw = _build_from_session(is_top=True)
                bottom_poses_raw, bottom_names_raw, bottom_nums_raw, bottom_lrs_raw = _build_from_session(is_top=False)
                top_p, top_n, top_num, top_l = _to_save_lists(top_poses_raw, top_names_raw, top_nums_raw, top_lrs_raw)
                bottom_p, bottom_n, bottom_num, bottom_l = _to_save_lists(bottom_poses_raw, bottom_names_raw, bottom_nums_raw, bottom_lrs_raw)
                top_team_s = str(st.session_state.top_team or "").strip()
                bottom_team_s = str(st.session_state.bottom_team or "").strip()
                player_repo.save_stamem_by_team_name(
                    top_team_s, top_p, top_n, top_num, top_l
                )
                player_repo.save_stamem_by_team_name(
                    bottom_team_s, bottom_p, bottom_n, bottom_num, bottom_l
                )
                # 保存直後に読戻しで確認
                ok_top = player_repo.get_stamem_by_team_name(top_team_s)
                ok_bottom = player_repo.get_stamem_by_team_name(bottom_team_s)
                if ok_top and ok_bottom:
                    st.success("スタメン（先攻・後攻）を stamem テーブルに保存しました。")
                else:
                    st.warning("スタメンを保存しましたが、読み取り確認で取得できませんでした。DB接続先を確認してください。")
            except Exception as e:
                import traceback
                st.error(f"スタメン（stamemテーブル）の保存に失敗しました: {e}")
                st.code(traceback.format_exc())
                return st.session_state.top_team, st.session_state.bottom_team, top_poses, top_names, top_nums, top_lrs, bottom_poses, bottom_names, bottom_nums, bottom_lrs
            if st.session_state.game_start == "start":
                試合日時 = (st.session_state.get("game_試合日時") or "").strip()
                if not 試合日時:
                    st.error("試合日時を入力してください。")
                    return st.session_state.top_team, st.session_state.bottom_team, top_poses, top_names, top_nums, top_lrs, bottom_poses, bottom_names, bottom_nums, bottom_lrs
                try:
                    gid = game_repo.create_game(
                        試合日時,
                        st.session_state.top_team,
                        st.session_state.bottom_team,
                        主審=str(st.session_state.get("game_主審") or ""),
                        Season=str(st.session_state.get("game_Season") or ""),
                        Kind=str(st.session_state.get("game_Kind") or ""),
                        Week=str(st.session_state.get("game_Week") or ""),
                        Day=str(st.session_state.get("game_Day") or ""),
                        GameNumber=str(st.session_state.get("game_GameNumber") or ""),
                    )
                    st.session_state["current_game_id"] = gid
                    st.session_state["all_list"] = []
                except Exception as e:
                    st.warning(f"試合のDB登録に失敗: {e}")
                    st.session_state["current_game_id"] = None
            st.session_state.game_start = "continue"
            st.success("入力完了しました")
            st.session_state.page_ctg = "main"
            st.rerun()

        return st.session_state.top_team, st.session_state.bottom_team, top_poses, top_names, top_nums, top_lrs, bottom_poses, bottom_names, bottom_nums, bottom_lrs