import io
import os
import matplotlib
matplotlib.use( 'Agg' )
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.patches import FancyArrowPatch
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


_HOME = ( 130, 48 )

# ファールライン：(130,48) から指定点を通り図の端まで延長
def _extend_line( p0, p1, xlim = ( 0, 263 ), ylim = ( 0, 263 ) ):
    """p0 → p1 方向に延長し、描画範囲の端まで伸ばした (x0,y0),(x1,y1) を返す"""
    dx, dy = p1[ 0 ] - p0[ 0 ], p1[ 1 ] - p0[ 1 ]
    ts = []
    if dx != 0:
        ts.append( ( xlim[ 0 ] - p0[ 0 ] ) / dx )
        ts.append( ( xlim[ 1 ] - p0[ 0 ] ) / dx )
    if dy != 0:
        ts.append( ( ylim[ 0 ] - p0[ 1 ] ) / dy )
        ts.append( ( ylim[ 1 ] - p0[ 1 ] ) / dy )
    t_pos = [ t for t in ts if t >= 0 ]
    t_end = min( t_pos ) if t_pos else 1.0
    return p0, ( p0[ 0 ] + t_end * dx, p0[ 1 ] + t_end * dy )


_FOUL_LINES = [
    ( _HOME, ( 35,  141 ) ),
    ( _HOME, ( 225, 141 ) ),
]

_HIT_RESULTS    = { '単打', '二塁打', '三塁打', '本塁打' }
_FOUL_RESULTS   = { 'ファール', 'ファールフライ' }
_BATTED_RESULTS = _HIT_RESULTS | _FOUL_RESULTS | {
    '凡打死', '凡打出塁', 'エラー', '野手選択',
}

_COLOR_MAP = {
    'hit':   '#E53935',
    'foul':  '#FB8C00',
    'out':   '#212121',
}


def batted_ball_plot(
    df_p: pd.DataFrame,
    pitch_type: str = None,
    batter_side: str = None,
) -> io.BytesIO | None:

    df_p = df_p.copy()
    if pitch_type is not None:
        df_p = df_p[ df_p[ '球種' ] == pitch_type ]
    if batter_side is not None:
        df_p = df_p[ df_p[ '打席左右' ] == batter_side ]

    df_p = df_p[
        df_p[ '打撃結果' ].isin( _BATTED_RESULTS ) &
        df_p[ '打球位置X' ].notna() &
        df_p[ '打球位置Yadj' ].notna() &
        ( df_p[ '打球位置X' ] != 0 ) &
        ( df_p[ '打球位置Yadj' ] != 0 )
    ]

    if df_p.empty:
        return None

    fig, ax = plt.subplots( figsize = ( 2.5, 2.5 ) )
    ax.set_xlim( 0, 263 )
    ax.set_ylim( 0, 263 )
    ax.set_aspect( 'equal' )
    ax.axis( 'off' )
    ax.set_facecolor( '#F8F8F8' )

    # ── ファールライン ────────────────────────────────────────
    for p0, p1 in _FOUL_LINES:
        start, end = _extend_line( p0, p1 )
        ax.plot(
            [ start[ 0 ], end[ 0 ] ], [ start[ 1 ], end[ 1 ] ],
            color = 'black', linewidth = 0.6, zorder = 1,
        )

    # ── 内野ライン ────────────────────────────────────────────
    for seg in [ ( ( 90, 91 ), ( 130, 131 ) ), ( ( 170, 91 ), ( 130, 131 ) ) ]:
        ax.plot(
            [ seg[ 0 ][ 0 ], seg[ 1 ][ 0 ] ], [ seg[ 0 ][ 1 ], seg[ 1 ][ 1 ] ],
            color = 'black', linewidth = 0.6, zorder = 1,
        )

    # ── 外野フェンス曲線 ─────────────────────────────────────
    fence = FancyArrowPatch(
        ( 35, 141 ), ( 225, 141 ),
        connectionstyle = 'arc3,rad=-0.84',
        arrowstyle      = '-',
        color           = 'black',
        linewidth       = 0.6,
        zorder          = 1,
    )
    ax.add_patch( fence )

    # ── 打球プロット ──────────────────────────────────────────
    for _, row in df_p.iterrows():
        result = str( row.get( '打撃結果', '' ) )
        x = row[ '打球位置X' ]
        y = row[ '打球位置Yadj' ]

        if result in _HIT_RESULTS:
            color = _COLOR_MAP[ 'hit' ]
        elif result in _FOUL_RESULTS:
            color = _COLOR_MAP[ 'foul' ]
        else:
            color = _COLOR_MAP[ 'out' ]

        # ホームからの線分（打球タイプで形状変更）
        ball_type = str( row.get( '打球タイプ', '' ) )
        if ball_type == 'ゴロ':
            ax.plot(
                [ _HOME[ 0 ], x ], [ _HOME[ 1 ], y ],
                color = color, linewidth = 0.4, alpha = 0.5,
                linestyle = ( 0, ( 3, 2 ) ), zorder = 2,
            )
        elif ball_type == 'フライ':
            patch = FancyArrowPatch(
                _HOME, ( x, y ),
                connectionstyle = 'arc3,rad=0.2',
                arrowstyle      = '-',
                color           = color,
                linewidth       = 0.4,
                alpha           = 0.5,
                zorder          = 2,
            )
            ax.add_patch( patch )
        else:
            ax.plot(
                [ _HOME[ 0 ], x ], [ _HOME[ 1 ], y ],
                color = color, linewidth = 0.4, alpha = 0.5, zorder = 2,
            )
        # ポイント
        ax.scatter(
            x, y,
            c = color, s = 18, linewidths = 0,
            zorder = 3,
        )

    # ── 凡例 ──────────────────────────────────────────────────
    legend_handles = [
        Line2D( [ 0 ], [ 0 ], marker = 'o', color = 'none',
                markerfacecolor = _COLOR_MAP[ 'hit'  ], markersize = 5, label = 'ヒット' ),
        Line2D( [ 0 ], [ 0 ], marker = 'o', color = 'none',
                markerfacecolor = _COLOR_MAP[ 'out'  ], markersize = 5, label = '凡打'   ),
        Line2D( [ 0 ], [ 0 ], marker = 'o', color = 'none',
                markerfacecolor = _COLOR_MAP[ 'foul' ], markersize = 5, label = 'ファール' ),
    ]
    ax.legend(
        handles       = legend_handles,
        loc           = 'upper left',
        fontsize      = 5,
        framealpha    = 0.7,
        handlelength  = 0.8,
        handletextpad = 0.3,
        borderpad     = 0.4,
        labelspacing  = 0.2,
    )

    buf = io.BytesIO()
    fig.savefig( buf, format = 'png', dpi = 150, bbox_inches = 'tight' )
    plt.close( fig )
    buf.seek( 0 )
    return buf
