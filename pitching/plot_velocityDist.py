import io
import os
import matplotlib
matplotlib.use( 'Agg' )
import matplotlib.pyplot as plt
from matplotlib import font_manager
import pandas as pd
import numpy as np
from scipy.stats import gaussian_kde


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


# ── 被打球カテゴリ ──────────────────────────────────────────────────
_INFIELD  = { 1, 2, 3, 4, 5, 6, '1', '2', '3', '4', '5', '6' }
_OUTFIELD = { 7, 8, 9, '7', '8', '9' }

_BAR_CATEGORIES = [
    ( 'out',       '完全アウト（三振＋内野フライ）', '#5C6BC0' ),
    ( 'gb',        'ゴロ',                          '#EF8C40' ),
    ( 'fly_liner', '外野フライ＋ライナー',           '#42A5B3' ),
    ( 'bb',        '四死球',                        '#66BB6A' ),
    ( 'hr',        '本塁打',                        '#EF5350' ),
]


def _classify_pa( row ) -> str | None:
    result  = str( row.get( '打撃結果',   '' ) )
    cont    = str( row.get( '打席の継続', '' ) )
    btype   = str( row.get( '打球タイプ', '' ) )
    try:
        fielder = int( row.get( '捕球選手', '' ) )
    except ( ValueError, TypeError ):
        fielder = ''

    if result == '本塁打':
        return 'hr'
    if result in { '四球', '死球' }:
        return 'bb'
    if result in { '見逃し三振', '空振り三振', 'K3', '振り逃げ' }:
        return 'out'
    if cont == '打席完了':
        if btype == 'フライ' and fielder in _INFIELD:
            return 'out'
        if btype == 'ゴロ':
            return 'gb'
        if btype == 'ライナー':
            return 'fly_liner'
        if btype == 'フライ' and fielder in _OUTFIELD:
            return 'fly_liner'
    return None


def _calc_ratios( df: pd.DataFrame ) -> dict:
    counts = { key: 0 for key, *_ in _BAR_CATEGORIES }
    for _, row in df.iterrows():
        cat = _classify_pa( row )
        if cat is not None:
            counts[ cat ] += 1
    total = sum( counts.values() )
    if total == 0:
        return {}
    return { k: v / total for k, v in counts.items() }


def _draw_bar( ax, y: float, ratios: dict, label: str ):
    left = 0.0
    for key, _, color in _BAR_CATEGORIES:
        r = ratios.get( key, 0.0 )
        if r <= 0:
            left += r
            continue
        ax.barh( y, r, left = left, height = 0.35, color = color )
        if r >= 0.05:
            ax.text(
                left + r / 2, y,
                f'{r * 100:.0f}%',
                ha = 'center', va = 'center',
                fontsize = 7, color = 'white', fontweight = 'bold',
            )
        left += r
    ax.text(
        -0.01, y, label,
        ha = 'right', va = 'center', fontsize = 8,
    )


# ── 球速分布 KDE ──────────────────────────────────────────────────
def velocity_dist_plot(
    df_p: pd.DataFrame,
    pitch_type_colors: dict,
) -> io.BytesIO | None:

    df_p = df_p.copy()
    df_p[ '球速' ] = pd.to_numeric( df_p[ '球速' ], errors = 'coerce' )
    df_v = df_p.dropna( subset = [ '球速', '球種' ] )
    df_v = df_v[ df_v[ '球速' ] > 0 ]

    if df_v.empty:
        return None

    pt_list = (
        df_v.groupby( '球種' )[ '球速' ]
        .count()
        .sort_values( ascending = False )
        .index.tolist()
    )

    fig, ax = plt.subplots( figsize = ( 7, 2.0 ) )

    x_min  = df_v[ '球速' ].min() - 5
    x_max  = df_v[ '球速' ].max() + 5
    x_grid = np.linspace( x_min, x_max, 500 )

    pt_data      = []
    y_global_max = 0.0
    for pt in pt_list:
        vals = df_v[ df_v[ '球種' ] == pt ][ '球速' ].values
        if len( vals ) <= 1:
            continue
        kde  = gaussian_kde( vals, bw_method = 'scott' )
        dens = kde( x_grid )
        pt_data.append( ( pt, vals, kde, dens ) )
        y_global_max = max( y_global_max, dens.max() )

    if not pt_data:
        return None

    arrow_offset = y_global_max * 0.18

    for pt, vals, kde, dens in pt_data:
        color = pitch_type_colors.get( pt, '#888888' )
        ax.fill_between( x_grid, dens, alpha = 0.15, color = color )
        ax.plot( x_grid, dens, color = color, linewidth = 1.8, alpha = 0.85, label = pt )

        mean_v    = vals.mean()
        mean_dens = kde( [ mean_v ] )[ 0 ]

        ax.annotate(
            '',
            xy     = ( mean_v, mean_dens ),
            xytext = ( mean_v, mean_dens + arrow_offset ),
            arrowprops = dict( arrowstyle = '-|>', color = color, lw = 1.2 ),
        )
        ax.text(
            mean_v, mean_dens + arrow_offset + y_global_max * 0.04,
            f'{ round( mean_v ) }',
            ha = 'center', va = 'bottom', fontsize = 7,
            color = color, fontweight = 'bold',
        )

    ax.set_xlim( x_min, x_max )
    ax.set_ylim( bottom = 0 )
    ax.set_xlabel( '球速 (km/h)', fontsize = 9 )
    ax.tick_params( axis = 'x', labelsize = 8 )
    ax.yaxis.set_visible( False )
    for sp in ( 'top', 'right', 'left' ):
        ax.spines[ sp ].set_visible( False )
    ax.set_facecolor( '#F8F8F8' )
    ax.legend(
        loc = 'upper left', fontsize = 7, framealpha = 0.7,
        handlelength = 1.2, handletextpad = 0.4,
        borderpad = 0.4, labelspacing = 0.3,
    )

    fig.tight_layout()
    buf = io.BytesIO()
    fig.savefig( buf, format = 'png', dpi = 150, bbox_inches = 'tight' )
    plt.close( fig )
    buf.seek( 0 )
    return buf


# ── 被打球性質 100% 積み上げ横棒 ──────────────────────────────────
def batted_type_plot(
    df_p:         pd.DataFrame,
    df_all:       pd.DataFrame = None,
    pitcher_name: str          = None,
) -> io.BytesIO | None:

    ratios_p = _calc_ratios( df_p )
    if not ratios_p:
        return None

    has_all = df_all is not None and not df_all.empty
    n_bars  = 2 if has_all else 1

    fig, ax = plt.subplots( figsize = ( 7, 0.35 * n_bars + 0.5 ) )

    _draw_bar( ax, float( n_bars - 1 ), ratios_p, pitcher_name or '投手' )

    if has_all:
        ratios_all = _calc_ratios( df_all )
        _draw_bar( ax, 0.0, ratios_all, '全体' )

    ax.set_xlim( 0, 1 )
    ax.set_ylim( -0.5, n_bars - 0.5 )
    ax.axis( 'off' )

    legend_handles = [
        plt.Rectangle( ( 0, 0 ), 1, 1, color = color, label = label )
        for _, label, color in _BAR_CATEGORIES
    ]
    ax.legend(
        handles        = legend_handles,
        loc            = 'upper left',
        bbox_to_anchor = ( 0, -0.05 ),
        ncol           = len( _BAR_CATEGORIES ),
        fontsize       = 6.5,
        framealpha     = 0,
        handlelength   = 1.0,
        handletextpad  = 0.3,
        columnspacing  = 0.8,
        borderpad      = 0,
    )

    buf = io.BytesIO()
    fig.savefig( buf, format = 'png', dpi = 150, bbox_inches = 'tight' )
    plt.close( fig )
    buf.seek( 0 )
    return buf
