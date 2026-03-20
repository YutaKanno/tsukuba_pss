"""投手分析 PDF 生成"""
import io
import os

import matplotlib
matplotlib.use( 'Agg' )
import matplotlib.pyplot as plt
import pandas as pd

from reportlab.lib.pagesizes import A4
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, PageBreak,
    Table, TableStyle, KeepTogether,
)
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.utils import ImageReader
from reportlab.platypus import Image as RLImage

from pitching.calc_ptList import calc_ptList
from pitching.calc_stats import (
    calc_stats, convert_stats_dict_to_df, calc_overallStats,
)
from pitching.plot_statsTable       import plot_statsTable
from pitching.plot_overallStatsTable import plot_overallStatsTable
from pitching.plot_pt_pieChart      import pt_pieChart
from pitching.plot_courceDist       import course_distPlot
from pitching.plot_courseDetail     import course_detailPlot
from pitching.plot_battedBall       import batted_ball_plot
from pitching.plot_velocityDist     import velocity_dist_plot, batted_type_plot


# ── レイアウト定数 ─────────────────────────────────────────────────
PAGE_W, PAGE_H = A4
MARGIN    = 14 * mm
CONTENT_W = PAGE_W - 2 * MARGIN

COLOR_HEADER  = colors.HexColor( '#1A3A5C' )
COLOR_SECTION = colors.HexColor( '#2C3E50' )
COLOR_LABEL   = colors.HexColor( '#1A3A5C' )
COLOR_ROW_ALT = colors.HexColor( '#EEF2F5' )


# ── フォント登録 ──────────────────────────────────────────────────
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


# ── ユーティリティ ────────────────────────────────────────────────
def _fig_to_buf( fig, dpi: int = 180 ) -> io.BytesIO:
    buf = io.BytesIO()
    fig.savefig( buf, format = 'png', dpi = dpi, bbox_inches = 'tight' )
    plt.close( fig )
    buf.seek( 0 )
    return buf


def _buf_to_rl( buf: io.BytesIO, width: float ) -> RLImage:
    ir     = ImageReader( buf )
    iw, ih = ir.getSize()
    buf.seek( 0 )
    return RLImage( buf, width = width, height = width * ih / iw )


def _para( text, font, size = 9, color = colors.black, bold = False,
           align = 0, space_before = 0, space_after = 2 * mm ) -> Paragraph:
    style = ParagraphStyle(
        'p',
        fontName   = font,
        fontSize   = size,
        textColor  = color,
        leading    = size * 1.5,
        alignment  = align,
        spaceBefore = space_before,
        spaceAfter  = space_after,
        fontWeight  = 'bold' if bold else 'normal',
    )
    return Paragraph( text, style )


def _section_heading( text, font ) -> Table:
    """左に色帯のついたセクション見出し"""
    p = _para( text, font, size = 10, color = COLOR_LABEL, bold = True,
               space_before = 0, space_after = 0 )
    t = Table(
        [ [ p ] ],
        colWidths  = [ CONTENT_W ],
        rowHeights = [ 7 * mm ],
    )
    t.setStyle( TableStyle( [
        ( 'LINEAFTER',   ( 0, 0 ), ( 0, 0 ), 0, colors.white ),
        ( 'LINEBEFORE',  ( 0, 0 ), ( 0, 0 ), 3, COLOR_LABEL  ),
        ( 'LEFTPADDING', ( 0, 0 ), ( 0, 0 ), 3 * mm ),
        ( 'VALIGN',      ( 0, 0 ), ( -1, -1 ), 'MIDDLE' ),
        ( 'TOPPADDING',  ( 0, 0 ), ( -1, -1 ), 0 ),
        ( 'BOTTOMPADDING', ( 0, 0 ), ( -1, -1 ), 0 ),
    ] ) )
    return t


def _page_header( pitcher_name, team_name, start_date, end_date, font ) -> Table:
    title = _para( '投手分析レポート', font, size = 15,
                   color = colors.white, bold = True,
                   space_before = 0, space_after = 1 * mm )
    info  = _para(
        f'{pitcher_name}　{team_name}　{start_date} 〜 {end_date}',
        font, size = 9, color = colors.HexColor( '#B0C4D8' ),
        space_before = 0, space_after = 0,
    )
    t = Table(
        [ [ title ], [ info ] ],
        colWidths  = [ CONTENT_W ],
        rowHeights = [ 10 * mm, 7 * mm ],
    )
    t.setStyle( TableStyle( [
        ( 'BACKGROUND',    ( 0, 0 ), ( -1, -1 ), COLOR_HEADER ),
        ( 'LEFTPADDING',   ( 0, 0 ), ( -1, -1 ), 5 * mm ),
        ( 'TOPPADDING',    ( 0, 0 ), ( 0,  0  ), 3 * mm ),
        ( 'BOTTOMPADDING', ( 0, 1 ), ( -1, 1  ), 3 * mm ),
        ( 'VALIGN',        ( 0, 0 ), ( -1, -1 ), 'MIDDLE' ),
    ] ) )
    return t


def _side_header( label, font ) -> Table:
    p = _para( label, font, size = 11, color = colors.white,
               bold = True, space_before = 0, space_after = 0 )
    t = Table( [ [ p ] ], colWidths = [ CONTENT_W ], rowHeights = [ 8 * mm ] )
    t.setStyle( TableStyle( [
        ( 'BACKGROUND',    ( 0, 0 ), ( -1, -1 ), COLOR_SECTION ),
        ( 'LEFTPADDING',   ( 0, 0 ), ( -1, -1 ), 4 * mm ),
        ( 'VALIGN',        ( 0, 0 ), ( -1, -1 ), 'MIDDLE' ),
        ( 'TOPPADDING',    ( 0, 0 ), ( -1, -1 ), 0 ),
        ( 'BOTTOMPADDING', ( 0, 0 ), ( -1, -1 ), 0 ),
    ] ) )
    return t


def _count_pie_grid( df_p, batter_side, pitch_type_colors, font, width = None ) -> Table:
    """カウント別球種割合 4(B) × 3(S) グリッド"""
    N_B, N_S  = 4, 3
    if width is None:
        width = CONTENT_W
    cell_w    = width / N_B
    # figsize=(3,1) → aspect=1/3
    cell_h    = cell_w / 3

    header_style = ParagraphStyle(
        'ch', fontName = font, fontSize = 7, alignment = 1,
        textColor = colors.HexColor( '#555555' ), leading = 9,
    )

    # 列ヘッダー行: B=0〜3
    col_headers = [ Paragraph( f'B={b}', header_style ) for b in range( N_B ) ]
    rows = [ col_headers ]

    for s in range( N_S ):
        row = []
        for b in range( N_B ):
            fig = pt_pieChart(
                df_p, pitch_type_colors,
                batter_side  = batter_side,
                S            = s,
                B            = b,
                show_labels  = False,
                figsize      = ( 3.0, 1.0 ),
                count_label  = f'{b}-{s}',
            )
            buf = _fig_to_buf( fig, dpi = 100 )
            row.append( _buf_to_rl( buf, cell_w ) )
        rows.append( row )

    t = Table( rows, colWidths = [ cell_w ] * N_B )
    t.setStyle( TableStyle( [
        ( 'ALIGN',          ( 0, 0 ), ( -1, -1 ), 'CENTER' ),
        ( 'VALIGN',         ( 0, 0 ), ( -1, -1 ), 'MIDDLE' ),
        ( 'TOPPADDING',     ( 0, 0 ), ( -1, -1 ), 1 ),
        ( 'BOTTOMPADDING',  ( 0, 0 ), ( -1, -1 ), 1 ),
        ( 'LEFTPADDING',    ( 0, 0 ), ( -1, -1 ), 1 ),
        ( 'RIGHTPADDING',   ( 0, 0 ), ( -1, -1 ), 1 ),
        ( 'LINEBELOW',      ( 0, 0 ), ( -1, 0  ), 0.4, colors.lightgrey ),
        ( 'ROWBACKGROUNDS', ( 0, 0 ), ( -1, -1 ),
          [ colors.HexColor( '#F0F0F0' ), colors.white, COLOR_ROW_ALT, colors.white ] ),
    ] ) )
    return t


def _pie_count_combined( df_p, batter_side, pitch_type_colors, font ) -> Table:
    """球種割合パイ（左）とカウント別グリッド（右）を横並びにした複合テーブル"""
    pie_w   = CONTENT_W * 0.34
    count_w = CONTENT_W - pie_w

    fig_pie = pt_pieChart( df_p, pitch_type_colors, batter_side = batter_side )
    pie_img = _buf_to_rl( _fig_to_buf( fig_pie, dpi = 150 ), pie_w )

    count_grid = _count_pie_grid( df_p, batter_side, pitch_type_colors, font, width = count_w )

    t = Table(
        [ [ pie_img, count_grid ] ],
        colWidths = [ pie_w, count_w ],
    )
    t.setStyle( TableStyle( [
        ( 'VALIGN',        ( 0, 0 ), ( -1, -1 ), 'TOP' ),
        ( 'TOPPADDING',    ( 0, 0 ), ( -1, -1 ), 0 ),
        ( 'BOTTOMPADDING', ( 0, 0 ), ( -1, -1 ), 0 ),
        ( 'LEFTPADDING',   ( 0, 0 ), ( -1, -1 ), 0 ),
        ( 'RIGHTPADDING',  ( 0, 0 ), ( -1, -1 ), 2 ),
        ( 'LINEBEFORE',    ( 1, 0 ), ( 1, 0 ), 0.4, colors.lightgrey ),
    ] ) )
    return t


def _course_grid( df_p, batter_side, pt_list, font ) -> Table:
    """コース分布 / 詳細 / 打球方向 の 3 行 × 5 列グリッド"""
    N      = 5
    pts    = ( pt_list[ :N ] + [ '' ] * N )[ :N ]
    cell_w = CONTENT_W / N

    label_style = ParagraphStyle(
        'cl', fontName = font, fontSize = 7.5,
        alignment = 1, leading = 10,
    )

    rows = [ [ Paragraph( pt, label_style ) for pt in pts ] ]

    for plot_fn in ( course_distPlot, course_detailPlot, batted_ball_plot ):
        row = []
        for pt in pts:
            if pt:
                buf = plot_fn( df_p, pitch_type = pt, batter_side = batter_side )
                row.append( _buf_to_rl( buf, cell_w ) if buf else Spacer( cell_w, cell_w ) )
            else:
                row.append( Spacer( cell_w, cell_w ) )
        rows.append( row )

    t = Table( rows, colWidths = [ cell_w ] * N )
    t.setStyle( TableStyle( [
        ( 'ALIGN',         ( 0, 0 ), ( -1, -1 ), 'CENTER' ),
        ( 'VALIGN',        ( 0, 0 ), ( -1, -1 ), 'MIDDLE' ),
        ( 'TOPPADDING',    ( 0, 0 ), ( -1, -1 ), 1 ),
        ( 'BOTTOMPADDING', ( 0, 0 ), ( -1, -1 ), 1 ),
        ( 'LEFTPADDING',   ( 0, 0 ), ( -1, -1 ), 1 ),
        ( 'RIGHTPADDING',  ( 0, 0 ), ( -1, -1 ), 1 ),
        ( 'LINEBELOW',     ( 0, 0 ), ( -1, 0  ), 0.4, colors.lightgrey ),
        ( 'ROWBACKGROUNDS', ( 0, 0 ), ( -1, -1 ),
          [ colors.white, COLOR_ROW_ALT, colors.white, COLOR_ROW_ALT ] ),
    ] ) )
    return t


def _build_side_elements( df_p, batter_side, side_label, pitch_type_colors, font ):
    elements = []

    elements.append( _side_header( f'vs {side_label}', font ) )
    elements.append( Spacer( 1, 3 * mm ) )

    pt_list = calc_ptList( df_p, batter_side = batter_side )
    if not pt_list:
        elements.append( _para( f'vs {side_label} のデータがありません。', font ) )
        return elements

    # スタッツ表
    stats_dict = {}
    for pt in pt_list:
        stats_dict = calc_stats( df_p, pitch_type = pt,
                                 batter_side = batter_side, stats_dict = stats_dict )
    stats_df  = convert_stats_dict_to_df( stats_dict )
    fig_stats = plot_statsTable( stats_df )
    elements.append( KeepTogether( [
        _section_heading( 'スタッツ', font ),
        Spacer( 1, 2 * mm ),
        _buf_to_rl( _fig_to_buf( fig_stats, dpi = 200 ), CONTENT_W ),
    ] ) )
    elements.append( Spacer( 1, 4 * mm ) )

    # 球種割合（左）+ カウント別球種割合（右）横並び
    elements.append( KeepTogether( [
        _section_heading( '球種割合 / カウント別球種割合', font ),
        Spacer( 1, 2 * mm ),
        _pie_count_combined( df_p, batter_side, pitch_type_colors, font ),
    ] ) )
    elements.append( Spacer( 1, 4 * mm ) )

    # コース分布グリッド
    elements.append( _section_heading( 'コース分布 / 詳細 / 打球方向', font ) )
    elements.append( Spacer( 1, 2 * mm ) )
    elements.append( _course_grid( df_p, batter_side, pt_list, font ) )

    return elements


# ── メイン関数 ────────────────────────────────────────────────────
def generate_pitcher_pdf(
    df_p:           pd.DataFrame,
    df_all:         pd.DataFrame,
    selected_pitcher: str,
    selected_team:  str,
    start_date,
    end_date,
    pitch_type_colors: dict,
    comment:        str = '',
) -> io.BytesIO:

    font = _register_fonts()

    buf_out = io.BytesIO()
    doc = SimpleDocTemplate(
        buf_out,
        pagesize     = A4,
        leftMargin   = MARGIN,
        rightMargin  = MARGIN,
        topMargin    = MARGIN,
        bottomMargin = MARGIN,
    )

    story = []

    # ════════════════════════════════════════════════════════════
    #  Page 1 : 全体サマリー
    # ════════════════════════════════════════════════════════════
    story.append( _page_header(
        selected_pitcher, selected_team,
        str( start_date ), str( end_date ), font,
    ) )
    story.append( Spacer( 1, 5 * mm ) )

    # 総合スタッツ
    pitcher_label  = f'{selected_pitcher} 全体'
    overall_df = pd.DataFrame( [
        calc_overallStats( df_p,  None, pitcher_label ),
        calc_overallStats( df_p,  '右', 'vs右打者' ),
        calc_overallStats( df_p,  '左', 'vs左打者' ),
        calc_overallStats( df_all, None, '平均値'   ),
    ] )
    _blank_for_avg  = [ '投球数', '打席数', '安打数', '本塁打数', '奪三振数', '四死球数' ]
    _game_only_cols = [ '登板数', '投球回', '失点数', '失点率' ]
    overall_df.loc[ overall_df[ 'index' ] == '平均値',      _blank_for_avg  ] = '--'
    overall_df.loc[ overall_df[ 'index' ] != pitcher_label, _game_only_cols ] = '--'

    fig_overall = plot_overallStatsTable( overall_df )
    story.append( KeepTogether( [
        _section_heading( '総合スタッツ', font ),
        Spacer( 1, 2 * mm ),
        _buf_to_rl( _fig_to_buf( fig_overall, dpi = 200 ), CONTENT_W ),
    ] ) )
    story.append( Spacer( 1, 4 * mm ) )

    # 球速分布
    buf_vel = velocity_dist_plot( df_p, pitch_type_colors )
    if buf_vel:
        story.append( KeepTogether( [
            _section_heading( '球速分布', font ),
            Spacer( 1, 2 * mm ),
            _buf_to_rl( buf_vel, CONTENT_W ),
        ] ) )
        story.append( Spacer( 1, 4 * mm ) )

    # 被打球性質
    buf_bat = batted_type_plot( df_p, df_all = df_all, pitcher_name = selected_pitcher )
    if buf_bat:
        story.append( KeepTogether( [
            _section_heading( '被打球性質', font ),
            Spacer( 1, 2 * mm ),
            _buf_to_rl( buf_bat, CONTENT_W ),
        ] ) )

    # コメント
    if comment and comment.strip():
        story.append( Spacer( 1, 4 * mm ) )
        story.append( KeepTogether( [
            _section_heading( 'コメント', font ),
            Spacer( 1, 2 * mm ),
            _para( comment.replace( '\n', '<br/>' ), font, size = 9 ),
        ] ) )

    story.append( PageBreak() )

    # ════════════════════════════════════════════════════════════
    #  Page 2 : vs右打者
    # ════════════════════════════════════════════════════════════
    story.extend( _build_side_elements(
        df_p, '右', '右打者', pitch_type_colors, font,
    ) )

    story.append( PageBreak() )

    # ════════════════════════════════════════════════════════════
    #  Page 3 : vs左打者
    # ════════════════════════════════════════════════════════════
    story.extend( _build_side_elements(
        df_p, '左', '左打者', pitch_type_colors, font,
    ) )

    doc.build( story )
    buf_out.seek( 0 )
    return buf_out
