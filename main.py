import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import plotly.graph_objects as go
import main_page
import member
from streamlit_drawable_canvas import st_canvas
from PIL import Image
from datetime import datetime
import ast


def safe_eval(val):
    try:
        # NaN ならそのまま返す
        if pd.isna(val):
            return val
        # リスト形式の文字列ならPythonのリストに変換
        if isinstance(val, str) and (val.startswith("[") or val.startswith("{")):
            return ast.literal_eval(val)
        return val
    except (ValueError, SyntaxError):
        return val

# --- Streamlit Page Configuration ---
st.set_page_config(
    page_title="My Streamlit App",
    page_icon="📈",
    layout="wide",  # ウィンドウサイズに合わせて広く表示
)

hide_all_style = """
    <style>
    /* 上部のメニュー・フッター */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    /* 一番上の余白を消す */
    .block-container {
        padding-top: 0rem !important;
        padding-bottom: 0rem !important;
    }
    </style>
"""
st.markdown(hide_all_style, unsafe_allow_html=True)
st.header('Input GameData App')
# --- 変数の初期化 ---
# アップロードされたファイル変数を事前にNoneで初期化
uploaded_game_data_file = None
uploaded_member_data_file = None


# --- File Uploads (Conditional Display) ---
# メインページ以外でのみファイルアップローダーを表示
if st.session_state.get('page_ctg', 'start') != 'main':
    st.header("ファイルアップロード")

    uploaded_game_data_file = st.file_uploader("試合データファイル (game_data.csv) をアップロード", type=["csv"])
    uploaded_member_data_file = st.file_uploader("メンバーデータファイル (メンバー登録用.csv) をアップロード", type=["csv"])

# --- Session State Initialization and Data Loading ---
if 'all_list' not in st.session_state:
    st.session_state['all_list'] = [] # Initialize as empty

if 'member_df' not in st.session_state:
    st.session_state['member_df'] = None

# Load game_data.csv from upload or provide initial empty list
if uploaded_game_data_file is not None:
    try:
        df = pd.read_csv(uploaded_game_data_file, encoding='cp932')
        df = df.applymap(safe_eval)
        st.session_state['all_list'] = df.values.tolist()
        st.success("試合データが正常にロードされました。")
    except Exception as e:
        st.error(f"試合データの読み込み中にエラーが発生しました: {e}")
elif not st.session_state['all_list'] and st.session_state.get('page_ctg', 'start') != 'main': # Only show info if no data is loaded yet and not on main page
    st.info("試合データをアップロードしてください。")

# Load member_df from upload or provide a placeholder
if uploaded_member_data_file is not None:
    try:
        st.session_state['member_df'] = pd.read_csv(uploaded_member_data_file, encoding='utf-8')
        st.success("メンバーデータが正常にロードされました。")
    except Exception as e:
        st.error(f"メンバーデータの読み込み中にエラーが発生しました: {e}")
elif st.session_state['member_df'] is None and st.session_state.get('page_ctg', 'start') != 'main':
    st.info("メンバーデータをアップロードしてください。")

# Ensure member_df is available before proceeding
member_df = st.session_state['member_df']


if 'page_ctg' not in st.session_state:
    st.session_state.page_ctg = 'start'
if 'game_start' not in st.session_state:
    st.session_state.game_start = 'continue'

if "打撃結果" not in st.session_state:
    st.session_state["打撃結果"] = '0'


if st.session_state.page_ctg == 'start':
    # CSS でボタンを装飾
    st.markdown("""
    <style>
    .button-container {
        display: flex;
        gap: 1rem;
        justify-content: center;
        margin-top: 2rem;
    }
    .stButton > button {
        background-color: #4CAF50;
        color: white;
        padding: 0.75rem 1.5rem;
        font-size: 1.1rem;
        border: none;
        border-radius: 8px;
        cursor: pointer;
        transition: 0.3s;
    }
    .stButton > button:hover {
        background-color: #45a049;
    }
    </style>
    """, unsafe_allow_html=True)

    # ボタンを横並びで表示
    st.markdown('<div class="button-container">', unsafe_allow_html=True)
    
    st.write('---')
    col1, col2, col0 = st.columns([1, 1, 4])
    with col1:
        # Disable button if member_df is not loaded
        if st.button('▶️ 試合開始', disabled=(member_df is None)):
            st.session_state.page_ctg = 'member'
            st.session_state.game_start = 'start'
            st.rerun()
    with col2:
        # Disable button if all_list is empty
        if st.button('📝 入力再開', disabled=(not st.session_state['all_list'])):
            st.session_state.page_ctg = 'main'
            st.session_state.game_start = 'continue'
            st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

elif st.session_state.page_ctg == 'member':
    if member_df is None:
        st.error("メンバーデータをアップロードしてください。")
        st.session_state.page_ctg = 'start' # Go back to start if member_df is missing
        st.rerun()
    # Check for member_remember.csv if starting a new game
    mr = None
    

    initial_top_poses = ['', '', '', '', '', '', '', '', '', 'P']
    initial_top_names = ["先攻1", "先攻2", "先攻3", "先攻4", "先攻5", "先攻6", "先攻7", "先攻8", "先攻9", "先攻P", "先攻C", "先攻1B", "先攻2B", "先攻3B", "先攻SS", "先攻LF", "先攻CF", "先攻RF", "先攻", "先攻"]
    initial_top_nums = ['', '', '', '', '', '', '', '', '', '']
    initial_top_lrs = ["右", "左", "右", "左", "右", "左", "右", "左", "右", "左", '右']
    initial_bottom_poses = ['', '', '', '', '', '', '', '', '', 'P']
    initial_bottom_names = ["後攻1", "後攻2", "後攻3", "後攻4", "後攻5", "後攻6", "後攻7", "後攻8", "後攻9", "後攻P", "後攻C", "後攻1B", "後攻2B", "後攻3B", "後攻SS", "後攻LF", "後攻CF", "後攻RF", "後攻", "後攻"]
    initial_bottom_nums = ['', '', '', '', '', '', '', '', '', '']
    initial_bottom_lrs = ["左", "右", "左", "右", "左", "右", "左", "右", "左", "右", '右']


    if st.session_state.game_start == 'start':
        initial_temp_list = ["2025/4/5", "", "",'', '','', "", "先攻チーム", "後攻チーム", 0, 1, "表", 0, 0, 0, 0, 0, "打席継続", "イニング継続", "試合継続", 0, 0, 0, 0, 0, 0, 1, "先攻1", "右", "", 0, 0, "後攻P", "右", 0, "後攻C", 0, 0, 0, 0, "投球", 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 17, 0, 0, 0, "0:00", 0,0, initial_top_poses, initial_top_names, initial_top_nums, initial_top_lrs, initial_bottom_poses, initial_bottom_names, initial_bottom_nums, initial_bottom_lrs, ['', '', '', '', '', '', '', '', '', '', '', '', 0, 0, 0, 0], ['', '', '', '', '', '', '', '', '', '', '', '', 0, 0, 0, 0]]
        if 'temp_list' not in st.session_state:
            st.session_state.temp_list = initial_temp_list

        先攻チーム, 後攻チーム, updated_top_poses, updated_top_names, updated_top_nums, updated_top_lrs, updated_bottom_poses, updated_bottom_names, updated_bottom_nums, updated_bottom_lrs = member.member_page(member_df, initial_top_poses, initial_top_names, initial_top_nums, initial_top_lrs, initial_bottom_poses, initial_bottom_names, initial_bottom_nums, initial_bottom_lrs, '先攻チーム', '後攻チーム', '開始前', mr)
        st.session_state.temp_list[78:86] = updated_top_poses, updated_top_names, updated_top_nums, updated_top_lrs, updated_bottom_poses, updated_bottom_names, updated_bottom_nums, updated_bottom_lrs
        st.session_state.temp_list[7:9] = 後攻チーム, 先攻チーム
        st.session_state.temp_list[27], st.session_state.temp_list[28], st.session_state.temp_list[32], st.session_state.temp_list[33], st.session_state.temp_list[35], = initial_top_names[0], initial_top_lrs[0], initial_bottom_names[9], initial_bottom_lrs[9], initial_bottom_names[10]
        st.session_state.temp_list[0] = datetime.today().strftime('%Y/%m/%d')

    elif st.session_state.game_start == 'continue':
        if not st.session_state['all_list']:
            st.error("入力再開するには、試合データ (game_data.csv) をアップロードしてください。")
            st.session_state.page_ctg = 'start'
            st.rerun()

        # Load the last entry from all_list if continuing
        initial_temp_list = st.session_state['all_list'][-1]
        if 'temp_list' not in st.session_state:
            st.session_state.temp_list = initial_temp_list

        後攻チーム, 先攻チーム, 表裏 = st.session_state.temp_list[7], st.session_state.temp_list[8], st.session_state.temp_list[11]
        initial_top_poses_from_data, initial_top_names_from_data, initial_top_nums_from_data, initial_top_lrs_from_data, initial_bottom_poses_from_data, initial_bottom_names_from_data, initial_bottom_nums_from_data, initial_bottom_lrs_from_data = st.session_state.temp_list[78:86]

        先攻チーム, 後攻チーム, updated_top_poses, updated_top_names, updated_top_nums, updated_top_lrs, updated_bottom_poses, updated_bottom_names, updated_bottom_nums, updated_bottom_lrs = member.member_page(member_df, initial_top_poses_from_data, initial_top_names_from_data, initial_top_nums_from_data, initial_top_lrs_from_data, initial_bottom_poses_from_data, initial_bottom_names_from_data, initial_bottom_nums_from_data, initial_bottom_lrs_from_data, 先攻チーム, 後攻チーム, 表裏, '')
        st.session_state.temp_list[78:86] = updated_top_poses, updated_top_names, updated_top_nums, updated_top_lrs, updated_bottom_poses, updated_bottom_names, updated_bottom_nums, updated_bottom_lrs
        st.session_state.temp_list[7:9] = 後攻チーム, 先攻チーム
        st.session_state["already_rerun"] = False

elif st.session_state.page_ctg == 'main':
    if 'all_list' in st.session_state and st.session_state['all_list']:
        initial_temp_list = st.session_state['all_list'][-1]
    else:
        st.error("メインページに移動するには、試合データが必要です。")
        st.session_state.page_ctg = 'start'
        st.rerun()

    if 'temp_list' not in st.session_state:
        st.session_state.temp_list = initial_temp_list
    st.session_state.game_start = 'continue'
    st.session_state.temp_list = main_page.main_page(
        st.session_state.get("temp_list")
        )