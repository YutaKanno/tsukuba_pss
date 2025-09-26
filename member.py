import streamlit as st
import pandas as pd
import sqlite3
import json
# import member_requests # このモジュールが利用可能で、そのまま動作することを前提としています。

# データベースファイル名
DB_FILE = 'member_data.db'

def init_db():
    """データベースを初期化し、テーブルが存在しない場合は作成します。"""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS member_remember (
            大学名 TEXT PRIMARY KEY,
            poses TEXT,
            names TEXT,
            nums TEXT,
            lrs TEXT
        )
    ''')
    conn.commit()
    conn.close()

def get_member_data(大学名):
    """指定された大学のメンバーデータをデータベースから取得します。"""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('SELECT * FROM member_remember WHERE 大学名 = ?', (大学名,))
    row = c.fetchone()
    conn.close()
    if row:
        # JSON文字列をPythonリストにデシリアライズします。
        return {
            '大学名': row[0],
            'poses': json.loads(row[1]),
            'names': json.loads(row[2]),
            'nums': json.loads(row[3]),
            'lrs': json.loads(row[4])
        }
    return None

def save_member_data(大学名, poses, names, nums, lrs):
    """メンバーデータをデータベースに保存または更新します。"""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    # リストをJSON文字列にシリアライズします。
    poses_str = json.dumps(poses)
    names_str = json.dumps(names)
    nums_str = json.dumps(nums)
    lrs_str = json.dumps(lrs)

    c.execute('''
        INSERT OR REPLACE INTO member_remember (大学名, poses, names, nums, lrs)
        VALUES (?, ?, ?, ?, ?)
    ''', (大学名, poses_str, names_str, nums_str, lrs_str))
    conn.commit()
    conn.close()

def get_all_universities():
    """データベースに保存されているすべての大学名を取得します。"""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('SELECT 大学名 FROM member_remember')
    universities = [row[0] for row in c.fetchall()]
    conn.close()
    return universities


def member_page(member_df, top_poses, top_names, top_nums, top_lrs, bottom_poses, bottom_names, bottom_nums, bottom_lrs, 先攻チーム, 後攻チーム, 表裏, mr): # member_re_file パラメータは削除されました。

    init_db() # ページ関数の開始時にデータベースを初期化します。

    # 初期選択のためにデータベースから大学のリストを取得します。
    team_list = member_df['大学名'].unique()

    if 'member_srape' not in st.session_state:
        st.session_state.member_srape = 'not success'

    if 'top_team' not in st.session_state:
        st.session_state.top_team = 先攻チーム

    if 'bottom_team' not in st.session_state:
        st.session_state.bottom_team = 後攻チーム

    if st.session_state.game_start == 'start':
        col01, col02, col03 = st.columns([3,2,2])
        with col01:
            st.write('首都リーグ公式戦の場合は一球速報のこの試合のメンバーページURLを記入してください(一応東京六大学にも対応しています)')
        with col02:
            URL = st.text_input('', label_visibility='collapsed')
        with col03:
            if st.button('実行ボタン: Wi-Fiに接続してください'):
                # member_requests.scrape_stamem が利用可能であることを前提としています。
                # top_poses, top_names, top_nums, top_lrs, bottom_poses, bottom_names, bottom_nums, bottom_lrs, st.session_state.top_team, st.session_state.bottom_team, st.session_state.member_srape = member_requests.scrape_stamem(URL)
                st.session_state.member_srape = 'success' # スクレイピング成功のプレースホルダー

    col1, col2 = st.columns(2)
    with col1:
        if st.session_state.game_start == 'start':
            if st.session_state.member_srape == 'not success':
                st.session_state.top_team = st.selectbox('先攻チーム', team_list)
                mr_top = get_member_data(st.session_state.top_team)
                if mr_top:
                    top_poses = mr_top['poses']
                    top_names = mr_top['names']
                    top_nums = mr_top['nums']
                    top_lrs = mr_top['lrs']
                else:
                    top_poses = ['', '', '', '', '', '', '', '', '', 'P']
                    top_names = ["先攻1", "先攻2", "先攻3", "先攻4", "先攻5", "先攻6", "先攻7", "先攻8", "先攻9", "先攻P", "先攻C", "先攻1B", "先攻2B", "先攻3B", "先攻SS", "先攻LF", "先攻CF", "先攻RF", "先攻", "先攻"]
                    top_nums = ['', '', '', '', '', '', '', '', '', '']
                    top_lrs = ["右", "左", "右", "左", "右", "左", "右", "左", "右", "左", '右']
            else:
                st.write(f'#### {st.session_state.top_team}')
        else:
            st.session_state.top_team = st.session_state.temp_list[8]
            st.write(f'#### {st.session_state.top_team}')

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

                top_poses[i] = st.selectbox('', pos_list, label_visibility='collapsed', key=f'top_pos_{i}')
            st.write('#### P')

        with col13:
            for i in range(10):
                top_nums[i] = st.text_input('', label_visibility='collapsed', key=f'top_num_{i}', value=top_nums[i])
                try:
                    num = str(top_nums[i])
                    matched = top_list[top_list['背番号'] == num]
                    st.write(top_list['背番号'])
                    st.write(num)
                    if not matched.empty:
                        top_names[i] = matched.iloc[0]['名前']
                        top_lrs[i] = matched.iloc[0]['左右']
                    else:
                        st.write('一致するメンバーがいません')
                        top_names[i] = ''
                        top_lrs[i] = ''
                except ValueError:
                    st.write('フィルタをかける段階でエラーが出ました')
                    top_names[i] = ''
                    top_lrs[i] = ''

        with col14:
            for i in range(10):
                top_names[i] = st.text_input('', label_visibility='collapsed', key=f'top_name_{i}', value=top_names[i])

        # top_posesが2の名前を10番目に追加
        for i in range(9): # top_posesのi番目のポジションを検索
            for j in range(8):
                if top_poses[i] == j+2:
                    top_names[j+10] = top_names[i]

    with col2:
        if st.session_state.game_start == 'start':
            if st.session_state.member_srape == 'not success':
                st.session_state.bottom_team = st.selectbox('後攻チーム', team_list)
                mr_bottom = get_member_data(st.session_state.bottom_team)
                if mr_bottom:
                    bottom_poses = mr_bottom['poses']
                    bottom_names = mr_bottom['names']
                    bottom_nums = mr_bottom['nums']
                    bottom_lrs = mr_bottom['lrs']
                else:
                    bottom_poses = ['', '', '', '', '', '', '', '', '', 'P']
                    bottom_names = ["後攻1", "後攻2", "後攻3", "後攻4", "後攻5", "後攻6", "後攻7", "後攻8", "後攻9", "後攻P", "後攻C", "後攻1B", "後攻2B", "後攻3B", "後攻SS", "後攻LF", "後攻CF", "後攻RF", "後攻", "後攻"]
                    bottom_nums = ['', '', '', '', '', '', '', '', '', '']
                    bottom_lrs = ["左", "右", "左", "右", "左", "右", "左", "右", "左", "右", '右']
            else:
                st.write(f'#### {st.session_state.bottom_team}')
        else:
            st.session_state.bottom_team = st.session_state.temp_list[7]
            st.write(f'#### {st.session_state.bottom_team}')
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
                bottom_poses[i] = st.selectbox('', pos_list2, label_visibility='collapsed', key=f'bottom_pos_{i}')
            st.write('#### P')

        with col22:
            for i in range(10):
                bottom_nums[i] = st.text_input('', label_visibility='collapsed', key=f'bottom_num_{i}', value=bottom_nums[i])
                try:
                    num2 = str(bottom_nums[i])
                    matched2 = bottom_list[bottom_list['背番号'] == num2]
                    if not matched2.empty:
                        bottom_names[i] = matched2.iloc[0]['名前']
                        bottom_lrs[i] = matched2.iloc[0]['左右']
                    else:
                        st.write('一致するメンバーがいません')
                        bottom_names[i] = ''
                        bottom_lrs[i] = ''

                except ValueError:
                    st.write('フィルタをかける段階でエラーが出ました')
                    bottom_names[i] = ''
                    bottom_lrs[i] = ''

        with col23:
            for i in range(10):
                bottom_names[i] = st.text_input('', label_visibility='collapsed', key=f'bottom_name_{i}', value=bottom_names[i])

        # bottom_posesが2の名前を10番目に追加
        for i in range(9): # top_posesのi番目のポジションを検索
            for j in range(8):
                if bottom_poses[i] == j+2:
                    bottom_names[j+10] = bottom_names[i]

        if st.button('確定'):
            if st.session_state.game_start == 'start':
                # 先攻チームのデータを保存
                save_member_data(st.session_state.top_team, top_poses, top_names, top_nums, top_lrs)
                # 後攻チームのデータを保存
                save_member_data(st.session_state.bottom_team, bottom_poses, bottom_names, bottom_nums, bottom_lrs)

            st.session_state.game_start = 'continue'
            st.success('入力完了しました')
            st.session_state.page_ctg = 'main'

        return st.session_state.top_team, st.session_state.bottom_team, top_poses, top_names, top_nums, top_lrs, bottom_poses, bottom_names, bottom_nums, bottom_lrs