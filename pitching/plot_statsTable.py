import os
import pandas as pd
import matplotlib
matplotlib.use( 'Agg' )
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.patches import Rectangle


STATS_COLS = [ '投球数', 'ストライク率', 'ゾーン率', 'スイング率', '空振り率', 'ゾーン外\nスイング率', 'PutAway\n率', 'ゴロ率', 'フライ率', '被打率', '出塁率', '長打率', 'OPS' ]
AIM_COLS   = [ '3塁側構え', '真ん中構え', '1塁側構え', '高め構え' ]

COLOR_STATS = '#1A3A5C'
COLOR_AIM   = '#1A4A3C'
COLOR_INFO  = '#3D3D3D'


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


def plot_statsTable(
    df: pd.DataFrame,
    figsize: tuple = None,
) -> plt.Figure:
    col_count = len( df.columns )
    row_count = len( df )
    cols      = df.columns.tolist()

    def _strip_nl( s: str ) -> str:
        return s.replace( '\n', '' )

    _stats_set = { _strip_nl( c ) for c in STATS_COLS }
    _aim_set   = { _strip_nl( c ) for c in AIM_COLS   }

    info_cols  = [ c for c in cols if _strip_nl( c ) not in _stats_set and _strip_nl( c ) not in _aim_set ]
    stats_cols = [ c for c in cols if _strip_nl( c ) in _stats_set ]
    aim_cols   = [ c for c in cols if _strip_nl( c ) in _aim_set   ]

    stats_indices = [ cols.index( c ) for c in stats_cols ]
    aim_indices   = [ cols.index( c ) for c in aim_cols ]
    info_indices  = [ cols.index( c ) for c in info_cols ]

    _display_map = { _strip_nl( s ): s for s in STATS_COLS + AIM_COLS }
    display_cols = [ _display_map.get( _strip_nl( c ), c ) for c in cols ]

    cat_row = [ '' ] * col_count

    df_disp = df.where( df.notna(), other = '' ).astype( object )
    for col_idx in aim_indices:
        col_name = cols[ col_idx ]
        df_disp[ col_name ] = df_disp[ col_name ].apply(
            lambda v: f'{ int( v ) }%' if v != '' else ''
        )
    data_rows = df_disp.values.tolist()
    all_text  = [ cat_row, display_cols ] + data_rows
    total_row = len( all_text )

    # col×1.1 + font=16 → 表示フォント ≈ 11px（読みやすい最低ライン）
    # col×1.3 だと 7px になり小さすぎる
    # col×0.9 以下だと列が重なる（font=16 の文字幅が列幅を超える）
    if figsize is None:
        figsize = ( col_count * 1.1, total_row * 0.45 )

    fig, ax = plt.subplots( figsize = figsize, dpi = 300 )
    ax.axis( 'off' )

    table = ax.table(
        cellText = all_text,
        cellLoc  = 'center',
        bbox     = [ 0, 0, 1, 1 ],
    )
    table.set_zorder( 2 )

    table.auto_set_font_size( False )
    table.set_fontsize( 16 )
    table.auto_set_column_width( list( range( col_count ) ) )
    table.scale( 1, 1.4 )

    has_multiline = any( '\n' in str( c ) for c in display_cols )
    if has_multiline:
        for col in range( col_count ):
            if ( 1, col ) in table._cells:
                h = table._cells[ ( 1, col ) ].get_height()
                table._cells[ ( 1, col ) ].set_height( h * 1.8 )

    def _uniform_width( indices: list ):
        max_w = max( table[ 0, i ].get_width() for i in indices )
        for i in indices:
            for r in range( total_row ):
                if ( r, i ) in table._cells:
                    table._cells[ ( r, i ) ].set_width( max_w )

    if stats_indices:
        _uniform_width( stats_indices )
    if aim_indices:
        _uniform_width( aim_indices )

    # Linux/Docker でフォントメトリクスが異なるため列幅に余白を追加
    for col in range( col_count ):
        for r in range( total_row ):
            if ( r, col ) in table._cells:
                w = table._cells[ ( r, col ) ].get_width()
                table._cells[ ( r, col ) ].set_width( w * 1.3 )

    for r in range( total_row ):
        for col in range( col_count ):
            table[ r, col ].set_facecolor( 'none' )

    for hrow in ( 0, 1 ):
        for col in range( col_count ):
            cell = table[ hrow, col ]
            cell.set_text_props( color = 'white', fontweight = 'bold' )
            cell.PAD = 0.05

    for row in range( 2, total_row ):
        for col in range( col_count ):
            table[ row, col ].PAD = 0.05

    def _remove_inner_verticals( indices: list ):
        n = len( indices )
        for j, col_idx in enumerate( indices ):
            for r in range( total_row ):
                if ( r, col_idx ) in table._cells:
                    c     = table._cells[ ( r, col_idx ) ]
                    edges = set( 'BRTL' )
                    if j > 0:
                        edges.discard( 'L' )
                    if j < n - 1:
                        edges.discard( 'R' )
                    c.visible_edges = ''.join( e for e in 'BRTL' if e in edges )

    _remove_inner_verticals( stats_indices )
    _remove_inner_verticals( aim_indices )

    fig.canvas.draw()

    groups = [
        ( info_indices,  COLOR_INFO  ),
        ( stats_indices, COLOR_STATS ),
        ( aim_indices,   COLOR_AIM   ),
    ]

    def _add_patch( row_idx: int, col_start: int, col_end: int, color: str ):
        first  = table[ row_idx, col_start ]
        last   = table[ row_idx, col_end   ]
        x0, y0 = first.get_xy()
        x1     = last.get_xy()[ 0 ] + last.get_width()
        h      = first.get_height()
        ax.add_patch( Rectangle(
            ( x0, y0 ), x1 - x0, h,
            facecolor = color,
            edgecolor = 'none',
            transform = ax.transAxes,
            zorder    = 1,
        ) )

    for hrow in ( 0, 1 ):
        for group_indices, color in groups:
            if not group_indices:
                continue
            _add_patch( hrow, group_indices[ 0 ], group_indices[ -1 ], color )

    for row_idx in range( 2, total_row ):
        bg = '#EEF2F5' if row_idx % 2 == 0 else 'white'
        _add_patch( row_idx, 0, col_count - 1, bg )

    cat_labels = [
        ( stats_indices, 'スタッツ' ),
        ( aim_indices,   '構え位置' ),
    ]
    for group_indices, label in cat_labels:
        if not group_indices:
            continue
        first  = table[ 0, group_indices[ 0 ]  ]
        last   = table[ 0, group_indices[ -1 ] ]
        x0, y0 = first.get_xy()
        x1     = last.get_xy()[ 0 ] + last.get_width()
        h      = first.get_height()
        cx     = ( x0 + x1 ) / 2
        cy     = y0 + h / 2
        ax.text(
            cx, cy, label,
            ha         = 'center',
            va         = 'center',
            color      = 'white',
            fontsize   = 13,
            fontweight = 'bold',
            transform  = ax.transAxes,
            zorder     = 3,
        )

    plt.subplots_adjust( left = 0, right = 1, top = 1, bottom = 0 )
    return fig
