"""投手分析ページ"""
import io
import matplotlib
matplotlib.use( 'Agg' )

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import streamlit as st

from db import game_repo
from pitching.calc_ptList import calc_ptList
from pitching.calc_stats import calc_stats, convert_stats_dict_to_df
from pitching.plot_statsTable import plot_statsTable
from pitching.plot_pt_pieChart import pt_pieChart
from pitching.plot_courceDist import course_distPlot


PITCH_TYPE_COLORS = {
    'ストレート': '#FF3333',
    'ツーシーム': '#FF9933',
    'スライダー': '#6666FF',
    'カット':     '#9933FF',
    'カーブ':     '#66B2FF',
    'チェンジ':   '#00CC66',
    'フォーク':   '#009900',
    'シンカー':   '#CC00CC',
    'シュート':   '#FF66B2',
    '特殊球':     '#000000',
}

_TABLE_DPI = 300


def _add_analysis_cols( df: pd.DataFrame ) -> pd.DataFrame:
    df = df.copy()
    df[ '守備チーム' ] = np.where( df[ '表裏' ] == '表', df[ '後攻チーム' ], df[ '先攻チーム' ] )
    df[ 'コースYadj' ]   = 263 - pd.to_numeric( df[ 'コースY' ],    errors = 'coerce' )
    df[ '打球位置Yadj' ] = 263 - pd.to_numeric( df[ '打球位置Y' ], errors = 'coerce' )
    return df


@st.cache_data( ttl = 60 )
def _load_plays_df( team_id: int ) -> pd.DataFrame:
    df = game_repo.get_all_plays_df( team_id )
    if df.empty:
        return df
    for col in [ 'コースX', 'コースY', '打球位置X', '打球位置Y', 'S', 'B', '構え' ]:
        if col in df.columns:
            df[ col ] = pd.to_numeric( df[ col ], errors = 'coerce' )
    return _add_analysis_cols( df )


def _fig_to_image( fig: plt.Figure, dpi: int, tight: bool = True ) -> io.BytesIO:
    buf = io.BytesIO()
    kwargs = dict( format = 'png', dpi = dpi )
    if tight:
        kwargs[ 'bbox_inches' ] = 'tight'
    fig.savefig( buf, **kwargs )
    plt.close( fig )
    buf.seek( 0 )
    return buf


def _render_side_tab( df_p: pd.DataFrame, side: str, side_label: str ):
    pt_list = calc_ptList( df_p, batter_side = side )
    if not pt_list:
        st.info( f'vs {side_label} のデータがありません。' )
        return

    stats_dict = {}
    for pt in pt_list:
        stats_dict = calc_stats(
            df_p,
            pitch_type  = pt,
            batter_side = side,
            stats_dict  = stats_dict,
        )
    stats_df = convert_stats_dict_to_df( stats_dict )

    c_table, c_pie_all = st.columns( [ 3, 1 ] )
    with c_table:
        fig_table = plot_statsTable( stats_df )
        st.image( _fig_to_image( fig_table, dpi = _TABLE_DPI ), use_container_width = True )
    with c_pie_all:
        fig_pie = pt_pieChart( df_p, PITCH_TYPE_COLORS, batter_side = side )
        st.image( _fig_to_image( fig_pie, dpi = 200 ), use_container_width = True )

    # ── カウント別球種分布（B-S 対角グリッド） ───────────
    st.markdown( '**カウント別球種分布**' )

    # 各対角行: (S, B) タプルのリスト  ＊ラベルは "B-S" 表記
    _DIAG_ROWS = [
        [ (0, 0) ],
        [ (0, 1), (1, 0) ],
        [ (0, 2), (1, 1), (2, 0) ],
        [ (1, 2), (2, 1), (3, 0) ],
        [ (2, 2), (3, 1) ],
        [ (3, 2) ],
    ]
    # 7列グリッド内の列インデックス (0–6)
    _DIAG_COLS = [
        [ 3 ],
        [ 2, 4 ],
        [ 1, 3, 5 ],
        [ 1, 3, 5 ],
        [ 2, 4 ],
        [ 3 ],
    ]

    _COUNT_FIGSIZE = ( 3.0, 1.0 )
    for diag_items, positions in zip( _DIAG_ROWS, _DIAG_COLS ):
        row_cols = st.columns( 7 )
        for item, pos in zip( diag_items, positions ):
            with row_cols[ pos ]:
                b, s = item
                label = f'{b}-{s}'
                fig = pt_pieChart( df_p, PITCH_TYPE_COLORS, batter_side = side,
                                   S = s, B = b, show_labels = False,
                                   figsize = _COUNT_FIGSIZE, count_label = label )
                st.image( _fig_to_image( fig, dpi = 100, tight = False ), use_container_width = True )

    # ── コース分布（球種別） ──────────────────────────────
    st.markdown( '**コース分布（球種別）**' )
    n_cols     = min( len( pt_list ), 6 )
    row_chunks = [ pt_list[ i : i + n_cols ] for i in range( 0, len( pt_list ), n_cols ) ]

    for chunk in row_chunks:
        cols = st.columns( n_cols )
        for j, pt in enumerate( chunk ):
            buf = course_distPlot( df_p, pitch_type = pt, batter_side = side )
            if buf is not None:
                with cols[ j ]:
                    st.image( buf, caption = pt, use_container_width = True )


def _go_start():
    st.session_state.page_ctg = 'start'


def show():
    st.button( '← スタートに戻る', on_click = _go_start )
    st.header( '投手分析' )

    team_id = st.session_state.get( 'logged_in_team_id' )
    df = _load_plays_df( team_id )

    if df.empty:
        st.warning( 'データがありません。先に試合データを入力してください。' )
        return

    # 守備チーム・投手を並列ドロップダウンで選択
    teams = sorted( df[ '守備チーム' ].dropna().unique().tolist() )
    if not teams:
        st.warning( '投手データが見つかりません。' )
        return

    col_team, col_pitcher = st.columns( 2 )
    with col_team:
        selected_team = st.selectbox( '守備チーム', teams, key = 'pa_team' )

    df_team = df[ df[ '守備チーム' ] == selected_team ]
    pitchers = sorted( df_team[ '投手氏名' ].dropna().unique().tolist() )

    with col_pitcher:
        if not pitchers:
            st.selectbox( '投手氏名', [], key = 'pa_pitcher' )
            st.warning( f'{selected_team} の投手データが見つかりません。' )
            return
        selected_pitcher = st.selectbox( '投手氏名', pitchers, key = 'pa_pitcher' )

    # 投手でフィルタリング（打撃結果が '0' のレコードは除外）
    df_p = df_team[
        ( df_team[ '投手氏名' ] == selected_pitcher ) &
        ( df_team[ '打撃結果' ] != '0' )
    ].copy()

    if df_p.empty:
        st.warning( f'{selected_pitcher} の投球データが見つかりません。' )
        return

    # ── vs右打者 / vs左打者 タブ ──────────────────────────
    tab_r, tab_l = st.tabs( [ 'vs 右打者', 'vs 左打者' ] )
    with tab_r:
        _render_side_tab( df_p, '右', '右打者' )
    with tab_l:
        _render_side_tab( df_p, '左', '左打者' )
