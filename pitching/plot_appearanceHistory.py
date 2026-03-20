import io
import os
import matplotlib
matplotlib.use( 'Agg' )
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.patches import Rectangle
import pandas as pd


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

_COLS = [ '試合日時', '先攻チーム', '後攻チーム', '投球回', '投球数', '打者数', '被安打数', '四死球数', '失点数' ]


def plot_appearance_history( df: pd.DataFrame ) -> io.BytesIO | None:
    if df.empty:
        return None

    df_disp = df[ _COLS ].copy()

    col_count = len( _COLS )
    row_count = len( df_disp ) + 1  # +1 for header

    all_text = [ _COLS ] + df_disp.values.tolist()

    figsize = ( col_count * 0.85, row_count * 0.24 )
    fig, ax = plt.subplots( figsize = figsize, dpi = 150 )
    ax.axis( 'off' )

    table = ax.table(
        cellText = all_text,
        cellLoc  = 'center',
        bbox     = [ 0, 0, 1, 1 ],
    )
    table.set_zorder( 2 )
    table.auto_set_font_size( False )
    table.set_fontsize( 8 )
    table.auto_set_column_width( list( range( col_count ) ) )
    table.scale( 1, 1.0 )

    for col in range( col_count ):
        for r in range( row_count ):
            if ( r, col ) in table._cells:
                w = table._cells[ r, col ].get_width()
                table._cells[ r, col ].set_width( w * 1.25 )

    last_col = col_count - 1
    for r in range( row_count ):
        for col in range( col_count ):
            if ( r, col ) not in table._cells:
                continue
            edges = { 'T', 'B' }
            if col == 0:
                edges.add( 'L' )
            if col == last_col:
                edges.add( 'R' )
            table._cells[ r, col ].visible_edges = ''.join(
                e for e in 'BRTL' if e in edges
            )

    for r in range( row_count ):
        for col in range( col_count ):
            if ( r, col ) in table._cells:
                table._cells[ r, col ].set_facecolor( 'none' )
                table._cells[ r, col ].PAD = 0.05

    for col in range( col_count ):
        if ( 0, col ) in table._cells:
            table._cells[ 0, col ].set_text_props( color = 'white', fontweight = 'bold' )

    fig.canvas.draw()

    def _add_patch( row_idx, color ):
        first = table[ row_idx, 0 ]
        last  = table[ row_idx, last_col ]
        x0, y0 = first.get_xy()
        x1      = last.get_xy()[ 0 ] + last.get_width()
        h       = first.get_height()
        ax.add_patch( Rectangle(
            ( x0, y0 ), x1 - x0, h,
            facecolor = color, edgecolor = 'none',
            transform = ax.transAxes, zorder = 1,
        ) )

    _add_patch( 0, _HEADER_COLOR )
    for r in range( 1, row_count ):
        _add_patch( r, '#EEF2F5' if r % 2 == 0 else 'white' )

    plt.subplots_adjust( left = 0, right = 1, top = 1, bottom = 0 )
    buf = io.BytesIO()
    fig.savefig( buf, format = 'png', dpi = 150, bbox_inches = 'tight' )
    plt.close( fig )
    buf.seek( 0 )
    return buf
