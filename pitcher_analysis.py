"""投手分析ページ"""
import io
import datetime
import matplotlib
matplotlib.use( 'Agg' )

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import streamlit as st

from db import game_repo
from db import comment_repo
from pitching.calc_ptList import calc_ptList
from pitching.calc_stats import calc_stats, convert_stats_dict_to_df, calc_overallStats, calc_appearance_history
from pitching.plot_statsTable import plot_statsTable
from pitching.plot_overallStatsTable import plot_overallStatsTable
from pitching.plot_pt_pieChart import pt_pieChart
from pitching.plot_courceDist import course_distPlot
from pitching.plot_courseDetail import course_detailPlot
from pitching.plot_battedBall import batted_ball_plot
from pitching.plot_velocityDist import velocity_dist_plot, batted_type_plot
from pitching.plot_appearanceHistory import plot_appearance_history
from generate_pitcher_pdf import generate_pitcher_pdf


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
    df = df[ df[ '球種' ] != '特殊球' ]
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
    _N_COLS    = 5
    pt_list_5  = pt_list[ : _N_COLS ]
    row_chunks = [ pt_list_5[ i : i + _N_COLS ] for i in range( 0, len( pt_list_5 ), _N_COLS ) ]

    for chunk in row_chunks:
        cols = st.columns( _N_COLS )
        for j, pt in enumerate( chunk ):
            buf_dist   = course_distPlot(   df_p, pitch_type = pt, batter_side = side )
            buf_detail = course_detailPlot( df_p, pitch_type = pt, batter_side = side )
            buf_batted = batted_ball_plot(  df_p, pitch_type = pt, batter_side = side )
            if buf_dist is not None:
                with cols[ j ]:
                    st.caption( pt )
                    st.image( buf_dist,   use_container_width = True )
                    if buf_detail is not None:
                        st.image( buf_detail, use_container_width = True )
                    if buf_batted is not None:
                        st.image( buf_batted, use_container_width = True )


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

    # ── 期間フィルター ────────────────────────────────────────
    df[ '_date' ] = pd.to_datetime( df[ '試合日時' ], errors = 'coerce' )
    valid_dates   = df[ '_date' ].dropna()
    date_min      = valid_dates.min().date() if not valid_dates.empty else datetime.date.today()
    date_max      = valid_dates.max().date() if not valid_dates.empty else datetime.date.today()

    col_start, col_end, col_team, col_pitcher = st.columns( 4 )

    with col_start:
        start_date = st.date_input( '開始日', value = date_min, key = 'pa_start' )
    with col_end:
        end_date   = st.date_input( '終了日', value = date_max, key = 'pa_end'   )

    df = df[
        ( df[ '_date' ].dt.date >= start_date ) &
        ( df[ '_date' ].dt.date <= end_date   )
    ]

    # ── 守備チーム・投手を並列ドロップダウンで選択 ───────────
    teams = sorted( df[ '守備チーム' ].dropna().unique().tolist() )
    if not teams:
        st.warning( '投手データが見つかりません。' )
        return

    my_team   = st.session_state.get( 'logged_in_team_name', '' )
    team_idx  = teams.index( my_team ) if my_team in teams else 0

    with col_team:
        selected_team = st.selectbox( '守備チーム', teams, index = team_idx, key = 'pa_team' )

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

    # ── 全体 / vs右打者 / vs左打者 / 出力 タブ ─────────────
    tab_all, tab_r, tab_l, tab_comment, tab_export = st.tabs( [ '全体', 'vs 右打者', 'vs 左打者', 'コメント', '出力' ] )
    with tab_all:
        st.markdown( '**総合スタッツ**' )
        overall_df = pd.DataFrame( [
            calc_overallStats( df_p, None,  f'{ selected_pitcher } 全体' ),
            calc_overallStats( df_p, '右',  'vs右打者' ),
            calc_overallStats( df_p, '左',  'vs左打者' ),
            calc_overallStats( df,   None,  '平均値' ),
        ] )
        _blank_for_avg  = [ '投球数', '打席数', '安打数', '本塁打数', '奪三振数', '四死球数' ]
        _game_only_cols = [ '登板数', '投球回', '失点数', '失点率' ]
        pitcher_label   = f'{ selected_pitcher } 全体'
        overall_df.loc[ overall_df[ 'index' ] == '平均値', _blank_for_avg ] = '--'
        overall_df.loc[ overall_df[ 'index' ] != pitcher_label, _game_only_cols ] = '--'
        fig_overall = plot_overallStatsTable( overall_df )
        st.image( _fig_to_image( fig_overall, dpi = _TABLE_DPI ), use_container_width = True )

        st.markdown( '**球速分布**' )
        buf_vel = velocity_dist_plot( df_p, PITCH_TYPE_COLORS )
        if buf_vel is not None:
            st.image( buf_vel, use_container_width = True )
        else:
            st.info( '球速データがありません。' )

        st.markdown( '**被打球性質**' )
        buf_bat = batted_type_plot(
            df_p,
            df_all        = df[ df[ '打撃結果' ] != '0' ],
            pitcher_name  = selected_pitcher,
        )
        if buf_bat is not None:
            st.image( buf_bat, use_container_width = True )
        else:
            st.info( '被打球データがありません。' )

        st.markdown( '**登板履歴**' )
        history_df = calc_appearance_history( df_p )
        buf_hist = plot_appearance_history( history_df )
        if buf_hist is not None:
            st.image( buf_hist, use_container_width = True )
        else:
            st.info( '登板履歴データがありません。' )
    with tab_r:
        _render_side_tab( df_p, '右', '右打者' )
    with tab_l:
        _render_side_tab( df_p, '左', '左打者' )
    with tab_comment:
        st.markdown( f'**{selected_pitcher} へのコメント**' )
        saved_comment = comment_repo.get_comment( team_id, selected_pitcher )

        if 'pa_comment_editing' not in st.session_state:
            st.session_state.pa_comment_editing = False

        if st.session_state.pa_comment_editing:
            new_text = st.text_area(
                'コメント', value = saved_comment,
                height = 200, key = 'pa_comment_input',
            )
            c_save, c_cancel = st.columns( [ 1, 1 ] )
            with c_save:
                if st.button( '保存', key = 'pa_comment_save' ):
                    comment_repo.upsert_comment( team_id, selected_pitcher, new_text )
                    st.session_state.pa_comment_editing = False
                    st.rerun()
            with c_cancel:
                if st.button( 'キャンセル', key = 'pa_comment_cancel' ):
                    st.session_state.pa_comment_editing = False
                    st.rerun()
        else:
            if saved_comment:
                st.text( saved_comment )
            else:
                st.info( 'コメントはまだ登録されていません。' )
            if st.button( 'Edit', key = 'pa_comment_edit' ):
                st.session_state.pa_comment_editing = True
                st.rerun()

    with tab_export:
        st.markdown( '投手分析レポートを PDF として出力します。' )
        if st.button( 'PDF 生成', key = 'gen_pdf' ):
            with st.spinner( 'PDF 生成中...' ):
                _comment_for_pdf = comment_repo.get_comment( team_id, selected_pitcher )
                pdf_buf = generate_pitcher_pdf(
                    df_p,
                    df[ df[ '打撃結果' ] != '0' ],
                    selected_pitcher,
                    selected_team,
                    start_date,
                    end_date,
                    PITCH_TYPE_COLORS,
                    comment = _comment_for_pdf,
                )
            fname = f'{ selected_pitcher }_{ start_date }_{ end_date }.pdf'
            st.download_button(
                label     = 'PDF ダウンロード',
                data      = pdf_buf.getvalue(),
                file_name = fname,
                mime      = 'application/pdf',
                key       = 'dl_pdf',
            )
