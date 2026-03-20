import io
import os
import matplotlib
matplotlib.use( 'Agg' )
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.lines import Line2D
import pandas as pd
import numpy as np


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


# ── 構え値 → カテゴリ ───────────────────────────────────────────
def _aim_category( val ) -> str:
    if pd.isna( val ):
        return 'unknown'
    v = int( val )
    if v <= 10:
        return 'high'
    if v in ( 11, 12, 16, 17, 21, 22 ):
        return '3rd'
    if v in ( 13, 18, 23 ):
        return 'mid'
    if v in ( 14, 15, 19, 20, 24, 25 ):
        return '1st'
    return 'unknown'


_AIM_COLOR = {
    '3rd':     '#3498DB',
    'mid':     '#27AE60',
    '1st':     '#E74C3C',
    'high':    '#F39C12',
    'unknown': '#AAAAAA',
}

_AIM_LABEL = {
    '3rd':  '3塁側',
    'mid':  '真ん中',
    '1st':  '1塁側',
    'high': '高め',
}

# ── 打撃結果 → (marker, filled) ────────────────────────────────
_RESULT_STYLE = {
    '見逃し':       ( 'o', False ),
    '見逃し三振':   ( 'o', False ),
    '空振り':       ( 'x', True  ),
    '空振り三振':   ( 'x', True  ),
    'ファール':     ( '^', False ),
    '単打':         ( '*', True  ),
    '二塁打':       ( '*', True  ),
    '三塁打':       ( '*', True  ),
    '本塁打':       ( '*', True  ),
    '凡打死':       ( 'v', True  ),
    '凡打出塁':     ( 'v', True  ),
    'エラー':       ( 'v', True  ),
    '野手選択':     ( 'v', True  ),
    'ファールフライ': ( 'v', True ),
    'ボール':       ( 's', False ),
    '死球':         ( 's', False ),
    '四球':         ( 's', False ),
}

_DEFAULT_STYLE = ( 'o', True )

_MARKER_LABEL = {
    ( 'o', False ): '見逃し',
    ( 'x', True  ): '空振り',
    ( '^', False ): 'ファール',
    ( '*', True  ): 'ヒット',
    ( 'v', True  ): '凡打',
    ( 's', False ): 'ボール',
}


def course_detailPlot(
    df_p: pd.DataFrame,
    pitch_type: str = None,
    batter_side: str = None,
) -> io.BytesIO | None:

    df_p = df_p.copy()
    if pitch_type is not None:
        df_p = df_p[ df_p[ '球種' ] == pitch_type ]
    if batter_side is not None:
        df_p = df_p[ df_p[ '打席左右' ] == batter_side ]

    df_p = df_p.dropna( subset = [ 'コースX', 'コースYadj' ] )
    if df_p.empty:
        return None

    df_p = df_p.copy()
    df_p[ '_aim_cat' ] = df_p[ '構え' ].apply( _aim_category )

    # figsize は course_distPlot と同じ
    fig, ax = plt.subplots( figsize = ( 2.5, 2.5 ) )
    ax.set_xlim( 0, 263 )
    ax.set_ylim( -20, 263 )
    ax.set_aspect( 'equal' )
    ax.axis( 'off' )

    # ── ストライクゾーン ──────────────────────────────────────
    from matplotlib.patches import Rectangle, Polygon
    ax.add_patch( Rectangle(
        ( 53, 53 ), 157, 157,
        fill      = False,
        edgecolor = 'black',
        linewidth = 0.6,
        zorder    = 2,
    ) )

    # ── ホームベース（五角形） ────────────────────────────────
    home_plate = Polygon(
        [ ( 53, 0 ), ( 53, -10 ), ( 131.5, -20 ), ( 210, -10 ), ( 210, 0 ) ],
        closed    = True,
        fill      = True,
        facecolor = 'white',
        edgecolor = 'black',
        linewidth = 0.6,
        zorder    = 2,
    )
    ax.add_patch( home_plate )

    # ── 散布 ──────────────────────────────────────────────────
    for _, row in df_p.iterrows():
        x   = row[ 'コースX' ]
        y   = row[ 'コースYadj' ]
        aim = row[ '_aim_cat' ]
        res = str( row.get( '打撃結果', '' ) )

        color              = _AIM_COLOR.get( aim, '#AAAAAA' )
        marker, filled     = _RESULT_STYLE.get( res, _DEFAULT_STYLE )

        kw = dict( marker = marker, s = 28, linewidths = 0.9, zorder = 3 )
        if marker == 'x':
            ax.scatter( x, y, c = color, **kw )
        elif filled:
            ax.scatter( x, y, c = color, **kw )
        else:
            ax.scatter( x, y, facecolors = 'none', edgecolors = color, **kw )

    # ── 凡例（コンパクト） ────────────────────────────────────
    aim_handles = [
        Line2D( [ 0 ], [ 0 ], marker = 'o', color = 'none',
                markerfacecolor = c, markeredgecolor = c,
                markersize = 4, label = _AIM_LABEL[ k ] )
        for k, c in _AIM_COLOR.items() if k != 'unknown'
    ]
    marker_handles = [
        Line2D( [ 0 ], [ 0 ],
                marker          = mk,
                color           = 'none' if mk == 'x' else 'none',
                markerfacecolor = '#555555' if filled else 'none',
                markeredgecolor = '#555555',
                markeredgewidth = 0.8,
                markersize      = 4,
                label           = lbl )
        for ( mk, filled ), lbl in _MARKER_LABEL.items()
    ]

    leg1 = ax.legend(
        handles   = aim_handles,
        loc       = 'upper left',
        fontsize  = 4.5,
        framealpha = 0.7,
        handlelength = 0.8,
        handletextpad = 0.3,
        borderpad  = 0.4,
        labelspacing = 0.2,
    )
    ax.add_artist( leg1 )
    ax.legend(
        handles   = marker_handles,
        loc       = 'lower left',
        fontsize  = 4.5,
        framealpha = 0.7,
        handlelength = 0.8,
        handletextpad = 0.3,
        borderpad  = 0.4,
        labelspacing = 0.2,
    )

    buf = io.BytesIO()
    fig.savefig( buf, format = 'png', dpi = 150, bbox_inches = 'tight' )
    plt.close( fig )
    buf.seek( 0 )
    return buf
