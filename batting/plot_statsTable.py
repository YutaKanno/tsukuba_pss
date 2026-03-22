"""打者スタッツテーブル描画モジュール（pitching/plot_overallStatsTable.py と同構造）。"""
import os
import pandas as pd
import matplotlib
matplotlib.use( 'Agg' )
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.patches import Rectangle


def _register_fonts():
    font_dir = os.path.join( os.path.dirname( os.path.dirname( __file__ ) ), 'fonts' )
    for fname in [ 'ipaexg.ttf', 'ipaexm.ttf' ]:
        fpath = os.path.join( font_dir, fname )
        if os.path.exists( fpath ):
            font_manager.fontManager.addfont( fpath )
    plt.rcParams[ 'font.family' ] = 'sans-serif'
    plt.rcParams[ 'font.sans-serif' ] = [
        'IPAexGothic', 'IPAexMincho',
        'Hiragino Sans', 'Hiragino Kaku Gothic ProN',
        'Noto Sans CJK JP', 'Yu Gothic', 'Meiryo', 'MS PGothic',
    ]


_register_fonts()

_HEADER_COLOR = '#1A3A5C'

# vline を入れる列（その列の右辺）
_VLINE_AFTER = { 'index', '打数', '打点', 'OPS', 'BB%', '2S以降平均投球数', 'フライ率' }

# .333 形式（先頭の0を除く）でフォーマットする列
_RATE3_COLS = { '打率', '出塁率', '長打率' }

# 1を超えうる小数3桁列（先頭を削らない）
_RATE3_FULL_COLS = { 'OPS' }

# round0 + % 表示する列
_PCT_COLS = {
    'K%', 'BB%', 'スイング率', 'ゾーン外SW%', '空振り率',
    '1stSW率', 'ゴロ率', 'フライ率',
}


def plot_battingStatsTable( df: pd.DataFrame ) -> plt.Figure:

    cols      = df.columns.tolist()
    col_count = len( cols )

    display_cols = [ '' if c == 'index' else c for c in cols ]

    df_disp = df.copy()
    for col in _RATE3_COLS:
        if col in df_disp.columns:
            df_disp[ col ] = df_disp[ col ].apply(
                lambda v: f'{v:.3f}'[ 1: ] if isinstance( v, float ) and not pd.isna( v ) else v
            )
    for col in _RATE3_FULL_COLS:
        if col in df_disp.columns:
            df_disp[ col ] = df_disp[ col ].apply(
                lambda v: f'{v:.3f}' if isinstance( v, float ) and not pd.isna( v ) else v
            )
    for col in _PCT_COLS:
        if col in df_disp.columns:
            df_disp[ col ] = df_disp[ col ].apply(
                lambda v: f'{int( round( v ) )}%' if isinstance( v, ( int, float ) ) and not pd.isna( v ) else v
            )
    df_disp = df_disp.where( df_disp.notna(), other = '' ).astype( object )

    all_text  = [ display_cols ] + df_disp.values.tolist()
    total_row = len( all_text )

    figsize = ( col_count * 0.88, total_row * 0.42 )

    fig, ax = plt.subplots( figsize = figsize, dpi = 300 )
    ax.axis( 'off' )

    table = ax.table(
        cellText = all_text,
        cellLoc  = 'center',
        bbox     = [ 0, 0, 1, 1 ],
    )
    table.set_zorder( 2 )
    table.auto_set_font_size( False )
    table.set_fontsize( 11 )
    table.auto_set_column_width( list( range( col_count ) ) )
    table.scale( 1, 1.4 )

    # Linux/Docker CJK 文字幅補正
    for col in range( col_count ):
        for r in range( total_row ):
            if ( r, col ) in table._cells:
                w = table._cells[ r, col ].get_width()
                table._cells[ r, col ].set_width( w * 1.65 )

    # vline
    vline_indices = { i for i, c in enumerate( cols ) if c in _VLINE_AFTER }
    last_col = col_count - 1

    for r in range( total_row ):
        for col in range( col_count ):
            if ( r, col ) not in table._cells:
                continue
            edges = { 'T', 'B' }
            if col == 0:
                edges.add( 'L' )
            if col == last_col:
                edges.add( 'R' )
            if col in vline_indices:
                edges.add( 'R' )
            table._cells[ r, col ].visible_edges = ''.join(
                e for e in 'BRTL' if e in edges
            )

    for r in range( total_row ):
        for col in range( col_count ):
            if ( r, col ) in table._cells:
                table._cells[ r, col ].set_facecolor( 'none' )

    for col in range( col_count ):
        if ( 0, col ) in table._cells:
            table._cells[ 0, col ].set_text_props( color = 'white', fontweight = 'bold' )
            table._cells[ 0, col ].PAD = 0.05

    for r in range( 1, total_row ):
        for col in range( col_count ):
            if ( r, col ) in table._cells:
                table._cells[ r, col ].PAD = 0.05

    fig.canvas.draw()

    def _add_patch( row_idx, col_start, col_end, color ):
        first  = table[ row_idx, col_start ]
        last   = table[ row_idx, col_end ]
        x0, y0 = first.get_xy()
        x1     = last.get_xy()[ 0 ] + last.get_width()
        h      = first.get_height()
        ax.add_patch( Rectangle(
            ( x0, y0 ), x1 - x0, h,
            facecolor = color, edgecolor = 'none',
            transform = ax.transAxes, zorder = 1,
        ) )

    _add_patch( 0, 0, last_col, _HEADER_COLOR )
    for r in range( 1, total_row ):
        bg = '#EEF2F5' if r % 2 == 0 else 'white'
        _add_patch( r, 0, last_col, bg )

    plt.subplots_adjust( left = 0, right = 1, top = 1, bottom = 0 )
    return fig
