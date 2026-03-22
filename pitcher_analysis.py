"""投手分析ページ"""
import io
import datetime
import matplotlib
matplotlib.use( 'Agg' )

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import streamlit as st

from db import comment_repo
from plays_cache import clear_team_plays_cache, get_cached_team_plays_df
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
from generate_pitcher_pptx import generate_pitcher_pptx


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

_IMG_CACHE = dict( ttl=1800, max_entries=48, show_spinner=False )


def _fig_to_image( fig: plt.Figure, dpi: int, tight: bool = True ) -> io.BytesIO:
    buf = io.BytesIO()
    kwargs = dict( format = 'png', dpi = dpi )
    if tight:
        kwargs[ 'bbox_inches' ] = 'tight'
    fig.savefig( buf, **kwargs )
    plt.close( fig )
    buf.seek( 0 )
    return buf


# ── キャッシュ付き描画ヘルパー（プリミティブキー）─────────────────

def _filter_pitcher_df( df_pre, start_date, end_date, selected_team, pitcher_name ):
    """(df_p, df_all_filtered) を返す高速フィルタ（キャッシュなし）。"""
    df_filtered = df_pre[
        ( df_pre[ '_date' ].dt.date >= start_date ) &
        ( df_pre[ '_date' ].dt.date <= end_date   )
    ]
    df_team = df_filtered[ df_filtered[ '守備チーム' ] == selected_team ]
    df_p = df_team[
        ( df_team[ '投手氏名' ] == pitcher_name ) &
        ( df_team[ '打撃結果' ] != '0' )
    ].copy()
    df_all_filtered = df_filtered[ df_filtered[ '打撃結果' ] != '0' ]
    return df_p, df_all_filtered


@st.cache_data( **_IMG_CACHE )
def _cached_overall_stats( team_id, start_date, end_date, selected_team, pitcher_name ):
    df_pre = get_cached_team_plays_df( team_id )
    df_p, df_all = _filter_pitcher_df( df_pre, start_date, end_date, selected_team, pitcher_name )
    if df_p.empty:
        return None
    pitcher_label = f'{ pitcher_name } 全体'
    overall_df = pd.DataFrame( [
        calc_overallStats( df_p,  None, pitcher_label ),
        calc_overallStats( df_p,  '右', 'vs右打者' ),
        calc_overallStats( df_p,  '左', 'vs左打者' ),
        calc_overallStats( df_all, None, '平均値'   ),
    ] )
    _blank_for_avg  = [ '投球数', '打席数', '安打数', '本塁打数', '奪三振数', '四死球数' ]
    _game_only_cols = [ '登板数', '投球回', '失点数', '失点率' ]
    overall_df.loc[ overall_df[ 'index' ] == '平均値',     _blank_for_avg  ] = '--'
    overall_df.loc[ overall_df[ 'index' ] != pitcher_label, _game_only_cols ] = '--'
    fig = plot_overallStatsTable( overall_df )
    return _fig_to_image( fig, dpi=_TABLE_DPI ).getvalue()


@st.cache_data( **_IMG_CACHE )
def _cached_velocity_dist( team_id, start_date, end_date, selected_team, pitcher_name ):
    df_pre = get_cached_team_plays_df( team_id )
    df_p, _ = _filter_pitcher_df( df_pre, start_date, end_date, selected_team, pitcher_name )
    if df_p.empty:
        return None
    buf = velocity_dist_plot( df_p, PITCH_TYPE_COLORS )
    return buf.getvalue() if buf else None


@st.cache_data( **_IMG_CACHE )
def _cached_batted_type( team_id, start_date, end_date, selected_team, pitcher_name ):
    df_pre = get_cached_team_plays_df( team_id )
    df_p, df_all = _filter_pitcher_df( df_pre, start_date, end_date, selected_team, pitcher_name )
    if df_p.empty:
        return None
    buf = batted_type_plot( df_p, df_all=df_all, pitcher_name=pitcher_name )
    return buf.getvalue() if buf else None


@st.cache_data( **_IMG_CACHE )
def _cached_appearance_history( team_id, start_date, end_date, selected_team, pitcher_name ):
    df_pre = get_cached_team_plays_df( team_id )
    df_p, _ = _filter_pitcher_df( df_pre, start_date, end_date, selected_team, pitcher_name )
    if df_p.empty:
        return None
    history_df = calc_appearance_history( df_p )
    buf = plot_appearance_history( history_df )
    return buf.getvalue() if buf else None


@st.cache_data( **_IMG_CACHE )
def _cached_side_stats( team_id, start_date, end_date, selected_team, pitcher_name, side ):
    """stats table bytes + pie chart bytes + pt_list を返す。"""
    df_pre = get_cached_team_plays_df( team_id )
    df_p, _ = _filter_pitcher_df( df_pre, start_date, end_date, selected_team, pitcher_name )
    pt_list = calc_ptList( df_p, batter_side=side )
    if not pt_list:
        return None, None, []
    stats_dict = {}
    for pt in pt_list:
        stats_dict = calc_stats( df_p, pitch_type=pt, batter_side=side, stats_dict=stats_dict )
    stats_df  = convert_stats_dict_to_df( stats_dict )
    fig_table = plot_statsTable( stats_df )
    fig_pie   = pt_pieChart( df_p, PITCH_TYPE_COLORS, batter_side=side )
    return (
        _fig_to_image( fig_table, dpi=_TABLE_DPI ).getvalue(),
        _fig_to_image( fig_pie,   dpi=200         ).getvalue(),
        pt_list,
    )


@st.cache_data( **_IMG_CACHE )
def _cached_count_pie( team_id, start_date, end_date, selected_team, pitcher_name, side, b, s ):
    df_pre = get_cached_team_plays_df( team_id )
    df_p, _ = _filter_pitcher_df( df_pre, start_date, end_date, selected_team, pitcher_name )
    fig = pt_pieChart(
        df_p, PITCH_TYPE_COLORS, batter_side=side,
        S=s, B=b, show_labels=False,
        figsize=( 3.0, 1.0 ), count_label=f'{ b }-{ s }',
    )
    return _fig_to_image( fig, dpi=100, tight=False ).getvalue()


@st.cache_data( **_IMG_CACHE )
def _cached_course_plots( team_id, start_date, end_date, selected_team, pitcher_name, side, pt ):
    """(dist_bytes, detail_bytes, batted_bytes) を返す。"""
    df_pre = get_cached_team_plays_df( team_id )
    df_p, _ = _filter_pitcher_df( df_pre, start_date, end_date, selected_team, pitcher_name )
    buf_dist   = course_distPlot(   df_p, pitch_type=pt, batter_side=side )
    buf_detail = course_detailPlot( df_p, pitch_type=pt, batter_side=side )
    buf_batted = batted_ball_plot(  df_p, pitch_type=pt, batter_side=side )
    return (
        buf_dist.getvalue()   if buf_dist   else None,
        buf_detail.getvalue() if buf_detail else None,
        buf_batted.getvalue() if buf_batted else None,
    )


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
    col_back, col_reload = st.columns( [ 6, 1 ] )
    with col_back:
        st.button( '← スタートに戻る', on_click = _go_start )
    with col_reload:
        if st.button( 'データを更新', key='pa_reload' ):
            clear_team_plays_cache()
            st.rerun()
    st.header( '投手分析' )

    team_id = st.session_state.get( 'logged_in_team_id' )
    df_pre  = get_cached_team_plays_df( team_id )

    if df_pre.empty:
        st.warning( 'データがありません。先に試合データを入力してください。' )
        return

    # ── 期間・チーム・投手選択 ────────────────────────────────
    valid_dates = df_pre[ '_date' ].dropna()
    date_min    = valid_dates.min().date() if not valid_dates.empty else datetime.date.today()
    date_max    = valid_dates.max().date() if not valid_dates.empty else datetime.date.today()

    col_start, col_end, col_team, col_pitcher = st.columns( 4 )

    with col_start:
        start_date = st.date_input( '開始日', value = date_min, key = 'pa_start' )
    with col_end:
        end_date   = st.date_input( '終了日', value = date_max, key = 'pa_end'   )

    # チームリストは全期間から
    teams = sorted( df_pre[ '守備チーム' ].dropna().unique().tolist() )
    if not teams:
        st.warning( '投手データが見つかりません。' )
        return

    my_team  = st.session_state.get( 'logged_in_team_name', '' )
    team_idx = teams.index( my_team ) if my_team in teams else 0

    with col_team:
        selected_team = st.selectbox( '守備チーム', teams, index = team_idx, key = 'pa_team' )

    # 投手リストは期間フィルタ後から
    df_team_filtered = df_pre[
        ( df_pre[ '_date' ].dt.date >= start_date ) &
        ( df_pre[ '_date' ].dt.date <= end_date   ) &
        ( df_pre[ '守備チーム' ] == selected_team )
    ]
    pitchers = sorted( df_team_filtered[ '投手氏名' ].dropna().unique().tolist() )

    with col_pitcher:
        if not pitchers:
            st.selectbox( '投手氏名', [], key = 'pa_pitcher' )
            st.warning( f'{ selected_team } の投手データが見つかりません。' )
            return
        selected_pitcher = st.selectbox( '投手氏名', pitchers, key = 'pa_pitcher' )

    # ── セクション切り替え（radio: 選択中のみ重い処理を実行）────
    section = st.radio(
        'セクション',
        [ '全体', 'vs 右打者', 'vs 左打者', 'コメント', '出力' ],
        horizontal=True, key='pa_section',
    )
    st.divider()

    _ck = ( team_id, start_date, end_date, selected_team, selected_pitcher )

    # ── 全体 ─────────────────────────────────────────────────
    if section == '全体':
        st.markdown( '**総合スタッツ**' )
        raw = _cached_overall_stats( *_ck )
        if raw:
            st.image( raw, use_container_width = True )

        st.markdown( '**球速分布**' )
        raw = _cached_velocity_dist( *_ck )
        if raw:
            st.image( raw, use_container_width = True )
        else:
            st.info( '球速データがありません。' )

        st.markdown( '**被打球性質**' )
        raw = _cached_batted_type( *_ck )
        if raw:
            st.image( raw, use_container_width = True )
        else:
            st.info( '被打球データがありません。' )

        st.markdown( '**登板履歴**' )
        raw = _cached_appearance_history( *_ck )
        if raw:
            st.image( raw, use_container_width = True )
        else:
            st.info( '登板履歴データがありません。' )

    # ── vs 右打者 / vs 左打者 ─────────────────────────────────
    elif section in ( 'vs 右打者', 'vs 左打者' ):
        side       = '右' if section == 'vs 右打者' else '左'
        side_label = '右打者' if side == '右' else '左打者'

        table_raw, pie_raw, pt_list = _cached_side_stats( *_ck, side )
        if not pt_list:
            st.info( f'vs { side_label } のデータがありません。' )
        else:
            c_table, c_pie_all = st.columns( [ 3, 1 ] )
            with c_table:
                st.image( table_raw, use_container_width = True )
            with c_pie_all:
                st.image( pie_raw,   use_container_width = True )

            st.markdown( '**カウント別球種分布**' )
            _DIAG_ROWS = [
                [ (0,0) ],
                [ (0,1), (1,0) ],
                [ (0,2), (1,1), (2,0) ],
                [ (1,2), (2,1), (3,0) ],
                [ (2,2), (3,1) ],
                [ (3,2) ],
            ]
            _DIAG_COLS = [ [3], [2,4], [1,3,5], [1,3,5], [2,4], [3] ]
            for diag_items, positions in zip( _DIAG_ROWS, _DIAG_COLS ):
                row_cols = st.columns( 7 )
                for item, pos in zip( diag_items, positions ):
                    b, s = item
                    with row_cols[ pos ]:
                        raw = _cached_count_pie( *_ck, side, b, s )
                        st.image( raw, use_container_width = True )

            st.markdown( '**コース分布（球種別）**' )
            pt_list_5  = pt_list[ :5 ]
            row_chunks = [ pt_list_5[ i : i+5 ] for i in range( 0, len( pt_list_5 ), 5 ) ]
            for chunk in row_chunks:
                cols = st.columns( 5 )
                for j, pt in enumerate( chunk ):
                    dist_raw, detail_raw, batted_raw = _cached_course_plots( *_ck, side, pt )
                    if dist_raw:
                        with cols[ j ]:
                            st.caption( pt )
                            st.image( dist_raw,   use_container_width = True )
                            if detail_raw:
                                st.image( detail_raw, use_container_width = True )
                            if batted_raw:
                                st.image( batted_raw, use_container_width = True )

    # ── コメント ──────────────────────────────────────────────
    elif section == 'コメント':
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

    # ── 出力 ──────────────────────────────────────────────────
    else:
        _export_comment  = comment_repo.get_comment( team_id, selected_pitcher )
        df_p, df_all_filtered = _filter_pitcher_df(
            df_pre, start_date, end_date, selected_team, selected_pitcher
        )

        col_pdf, col_pptx = st.columns( 2 )

        with col_pdf:
            st.markdown( '**PDF**' )
            if st.button( 'PDF 生成', key = 'gen_pdf' ):
                with st.spinner( 'PDF 生成中...' ):
                    pdf_buf = generate_pitcher_pdf(
                        df_p, df_all_filtered, selected_pitcher, selected_team,
                        start_date, end_date, PITCH_TYPE_COLORS, comment=_export_comment,
                    )
                st.download_button(
                    label     = 'PDF ダウンロード',
                    data      = pdf_buf.getvalue(),
                    file_name = f'{ selected_pitcher }_{ start_date }_{ end_date }.pdf',
                    mime      = 'application/pdf',
                    key       = 'dl_pdf',
                )

        with col_pptx:
            st.markdown( '**PowerPoint**' )
            if st.button( 'PPTX 生成', key = 'gen_pptx' ):
                with st.spinner( 'PPTX 生成中...' ):
                    pptx_buf = generate_pitcher_pptx(
                        df_p, df_all_filtered, selected_pitcher, selected_team,
                        start_date, end_date, PITCH_TYPE_COLORS, comment=_export_comment,
                    )
                st.download_button(
                    label     = 'PPTX ダウンロード',
                    data      = pptx_buf.getvalue(),
                    file_name = f'{ selected_pitcher }_{ start_date }_{ end_date }.pptx',
                    mime      = 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
                    key       = 'dl_pptx',
                )
