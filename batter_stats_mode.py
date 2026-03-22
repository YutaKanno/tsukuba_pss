"""打者スタッツ作成モード - 打者ごとのスタッツ一覧テーブル（全体 / 対右投手 / 対左投手）"""
import io
import os
import datetime
import matplotlib
matplotlib.use( 'Agg' )

import pandas as pd
import matplotlib.pyplot as plt
import streamlit as st

from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import SimpleDocTemplate, Spacer, KeepTogether, PageBreak
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.platypus import Paragraph, Table, TableStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.utils import ImageReader
from reportlab.platypus import Image as RLImage

from batting.calc_stats import calc_batting_stats
from batting.plot_statsTable import plot_battingStatsTable
from plays_cache import get_cached_team_plays_df


# ── PDF レイアウト定数 ──────────────────────────────────────────
PAGE_W, PAGE_H = landscape( A4 )
_MARGIN    = 14 * mm
_CONTENT_W = PAGE_W - 2 * _MARGIN
_COLOR_HEADER  = colors.HexColor( '#1A3A5C' )
_COLOR_LABEL   = colors.HexColor( '#1A3A5C' )
_COLOR_ROW_ALT = colors.HexColor( '#EEF2F5' )


# ── フォント ────────────────────────────────────────────────────
def _register_fonts() -> str:
    name = 'IPAexGothic'
    if name not in pdfmetrics.getRegisteredFontNames():
        fpath = os.path.join( os.path.dirname( __file__ ), 'fonts', 'ipaexg.ttf' )
        if os.path.exists( fpath ):
            try:
                pdfmetrics.registerFont( TTFont( name, fpath ) )
                return name
            except Exception:
                pass
    else:
        return name
    return 'Helvetica'


# ── ユーティリティ ──────────────────────────────────────────────
def _fig_to_image( fig: plt.Figure, dpi: int = 300 ) -> io.BytesIO:
    buf = io.BytesIO()
    fig.savefig( buf, format = 'png', dpi = dpi, bbox_inches = 'tight' )
    plt.close( fig )
    buf.seek( 0 )
    return buf


def _buf_to_rl( buf: io.BytesIO, width: float ) -> RLImage:
    ir = ImageReader( buf )
    iw, ih = ir.getSize()
    buf.seek( 0 )
    return RLImage( buf, width = width, height = width * ih / iw )


def _para( text, font, size = 9, color = colors.black, bold = False,
           space_before = 0, space_after = 2 * mm ) -> Paragraph:
    style = ParagraphStyle(
        'p', fontName = font, fontSize = size, textColor = color,
        leading = size * 1.5, spaceBefore = space_before, spaceAfter = space_after,
    )
    return Paragraph( text, style )


def _page_header( team_name, start_date, end_date, font ) -> Table:
    title = _para( '打者スタッツ一覧', font, size = 15, color = colors.white,
                   space_before = 0, space_after = 1 * mm )
    info  = _para( f'{ team_name }　{ start_date } 〜 { end_date }',
                   font, size = 9, color = colors.HexColor( '#B0C4D8' ),
                   space_before = 0, space_after = 0 )
    t = Table( [ [ title ], [ info ] ], colWidths = [ _CONTENT_W ],
               rowHeights = [ 10 * mm, 7 * mm ] )
    t.setStyle( TableStyle( [
        ( 'BACKGROUND',    ( 0, 0 ), ( -1, -1 ), _COLOR_HEADER ),
        ( 'LEFTPADDING',   ( 0, 0 ), ( -1, -1 ), 5 * mm ),
        ( 'TOPPADDING',    ( 0, 0 ), ( 0,  0  ), 3 * mm ),
        ( 'BOTTOMPADDING', ( 0, 1 ), ( -1, 1  ), 3 * mm ),
        ( 'VALIGN',        ( 0, 0 ), ( -1, -1 ), 'MIDDLE' ),
    ] ) )
    return t


def _section_heading( text, font ) -> Table:
    p = _para( text, font, size = 10, color = _COLOR_LABEL,
               space_before = 0, space_after = 0 )
    t = Table( [ [ p ] ], colWidths = [ _CONTENT_W ], rowHeights = [ 7 * mm ] )
    t.setStyle( TableStyle( [
        ( 'LINEBEFORE',    ( 0, 0 ), ( 0, 0 ), 3, _COLOR_LABEL ),
        ( 'LEFTPADDING',   ( 0, 0 ), ( 0, 0 ), 3 * mm ),
        ( 'VALIGN',        ( 0, 0 ), ( -1, -1 ), 'MIDDLE' ),
        ( 'TOPPADDING',    ( 0, 0 ), ( -1, -1 ), 0 ),
        ( 'BOTTOMPADDING', ( 0, 0 ), ( -1, -1 ), 0 ),
    ] ) )
    return t


# ── スタッツ計算 ────────────────────────────────────────────────
def _build_stats_df( df_team: pd.DataFrame, pitcher_side ) -> pd.DataFrame:
    """チームの全打者スタッツを打席数降順でまとめた DataFrame を返す。"""
    batters = df_team[ '打者氏名' ].dropna().unique().tolist()
    rows = []
    for batter in batters:
        df_b = df_team[ df_team[ '打者氏名' ] == batter ].copy()
        if df_b[ df_b[ '打席の継続' ] == '打席完了' ].empty:
            continue
        rows.append( calc_batting_stats( df_b, pitcher_side, batter ) )
    if not rows:
        return pd.DataFrame()
    df_stats = pd.DataFrame( rows )
    df_stats = df_stats.sort_values( '打席数', ascending = False ).reset_index( drop = True )

    # チーム計行
    team_row = calc_batting_stats( df_team, pitcher_side, 'チーム計' )
    df_team_row = pd.DataFrame( [ team_row ] )
    df_stats = pd.concat( [ df_stats, df_team_row ], ignore_index = True )
    return df_stats


# ── PDF 生成 ────────────────────────────────────────────────────
def _generate_stats_pdf(
    df_team: pd.DataFrame,
    selected_team: str,
    start_date,
    end_date,
) -> io.BytesIO:
    font    = _register_fonts()
    buf_out = io.BytesIO()
    doc     = SimpleDocTemplate(
        buf_out, pagesize = landscape( A4 ),
        leftMargin = _MARGIN, rightMargin  = _MARGIN,
        topMargin  = _MARGIN, bottomMargin = _MARGIN,
    )
    story  = []
    header = _page_header( selected_team, str( start_date ), str( end_date ), font )

    for i, ( pitcher_side, label ) in enumerate( [
        ( None, '全体'    ),
        ( '右', '対右投手' ),
        ( '左', '対左投手' ),
    ] ):
        if i > 0:
            story.append( PageBreak() )

        story.append( header )
        story.append( Spacer( 1, 5 * mm ) )

        df_stats = _build_stats_df( df_team, pitcher_side )
        if df_stats.empty:
            story.append( _para( f'{ label } のデータがありません。', font ) )
            continue

        fig     = plot_battingStatsTable( df_stats )
        img_buf = _fig_to_image( fig, dpi = 400 )
        story.append( KeepTogether( [
            _section_heading( label, font ),
            Spacer( 1, 2 * mm ),
            _buf_to_rl( img_buf, _CONTENT_W ),
        ] ) )

    doc.build( story )
    buf_out.seek( 0 )
    return buf_out


# ── ページ ──────────────────────────────────────────────────────
def _go_start():
    st.session_state.page_ctg = 'start'


def show() -> None:
    st.button( '← スタートに戻る', on_click = _go_start )
    st.header( '打者スタッツ' )

    team_id = st.session_state.get( 'logged_in_team_id' )
    df = get_cached_team_plays_df( team_id )

    if df.empty:
        st.warning( 'データがありません。先に試合データを入力してください。' )
        return

    # ── 期間フィルター ────────────────────────────────────────
    valid_dates = df[ '_date' ].dropna()
    date_min = valid_dates.min().date() if not valid_dates.empty else datetime.date.today()
    date_max = valid_dates.max().date() if not valid_dates.empty else datetime.date.today()

    col_start, col_end, col_team = st.columns( 3 )
    with col_start:
        start_date = st.date_input( '開始日', value = date_min, key = 'bsm_start' )
    with col_end:
        end_date = st.date_input( '終了日', value = date_max, key = 'bsm_end' )

    df = df[
        ( df[ '_date' ].dt.date >= start_date ) &
        ( df[ '_date' ].dt.date <= end_date   )
    ]

    # ── チーム選択 ───────────────────────────────────────────
    teams = sorted( df[ '攻撃チーム' ].dropna().unique().tolist() )
    if not teams:
        st.warning( '打者データが見つかりません。' )
        return

    my_team  = st.session_state.get( 'logged_in_team_name', '' )
    team_idx = teams.index( my_team ) if my_team in teams else 0

    with col_team:
        selected_team = st.selectbox( '攻撃チーム', teams, index = team_idx, key = 'bsm_team' )

    df_team = df[ df[ '攻撃チーム' ] == selected_team ]
    if df_team.empty:
        st.warning( f'{ selected_team } のデータが見つかりません。' )
        return

    # ── 全体 / 対右投手 / 対左投手 / 出力 タブ ──────────────
    tab_all, tab_right, tab_left, tab_export = st.tabs(
        [ '全体', '対右投手', '対左投手', '出力' ]
    )

    for tab, pitcher_side, label in [
        ( tab_all,   None, '全体'    ),
        ( tab_right, '右', '対右投手' ),
        ( tab_left,  '左', '対左投手' ),
    ]:
        with tab:
            df_stats = _build_stats_df( df_team, pitcher_side )
            if df_stats.empty:
                st.info( f'{ label } のデータがありません。' )
                continue
            fig = plot_battingStatsTable( df_stats )
            st.image( _fig_to_image( fig ), use_container_width = True )

    with tab_export:
        st.markdown( '**PDF**' )
        if st.button( 'PDF 生成', key = 'bsm_gen_pdf' ):
            with st.spinner( 'PDF 生成中...' ):
                pdf_buf = _generate_stats_pdf(
                    df_team, selected_team, start_date, end_date,
                )
            st.download_button(
                label     = 'PDF ダウンロード',
                data      = pdf_buf.getvalue(),
                file_name = f'batting_stats_{ selected_team }_{ start_date }_{ end_date }.pdf',
                mime      = 'application/pdf',
                key       = 'bsm_dl_pdf',
            )
