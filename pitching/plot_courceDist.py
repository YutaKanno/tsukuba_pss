import io
import os
import warnings
import matplotlib
matplotlib.use( 'Agg' )
import matplotlib.pyplot as plt
from matplotlib import font_manager
import pandas as pd
from plotnine import (
    ggplot, aes, stat_density_2d, geom_rect, scale_fill_gradientn,
    coord_fixed, lims, theme_minimal, theme, element_text, element_line,
    element_blank, element_rect, labs,
)
from plotnine.exceptions import PlotnineWarning


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

_JP_FONT = next(
    ( f for f in [
        'IPAexGothic', 'IPAexMincho',
        'Hiragino Sans', 'Hiragino Kaku Gothic ProN',
        'Noto Sans CJK JP', 'Yu Gothic', 'Meiryo', 'MS PGothic',
    ] if f in { f_.name for f_ in font_manager.fontManager.ttflist } ),
    'sans-serif',
)


def course_distPlot(
    df_p: pd.DataFrame,
    pitch_type: str = None,
    batter_side: str = None,
) -> io.BytesIO:

    df_p = df_p.copy()
    if pitch_type is not None:
        df_p = df_p[ df_p[ '球種' ] == pitch_type ]
    if batter_side is not None:
        df_p = df_p[ df_p[ '打席左右' ] == batter_side ]

    buf = io.BytesIO()

    if df_p.empty or len( df_p ) < 3:
        return None

    sz_rect = ( 53, 210, 53, 210 )

    p = (
        ggplot( df_p, aes( x = 'コースX', y = 'コースYadj' ) )
        + stat_density_2d(
            aes( fill = 'stat(level)' ),
            geom = 'polygon', alpha = 0.7, contour = True, levels = 20,
        )
        + scale_fill_gradientn(
            colors = [ '#FFFFFF', '#FFE5E5', '#FFB3B3', '#FF6B6B', '#FF0000' ],
            guide  = None,
        )
        + geom_rect(
            aes( xmin = sz_rect[ 0 ], xmax = sz_rect[ 1 ], ymin = sz_rect[ 2 ], ymax = sz_rect[ 3 ] ),
            fill       = None,
            color      = 'black',
            size       = 0.6,
            linetype   = 'solid',
            inherit_aes = False,
        )
        + coord_fixed( ratio = 1 )
        + lims( x = ( 0, 263 ), y = ( 0, 263 ) )
        + theme_minimal()
        + theme(
            figure_size      = ( 2.5, 2.5 ),
            text             = element_text( family = _JP_FONT ),
            plot_title       = element_text( size = 9, fontweight = 'normal', ha = 'left' ),
            panel_grid_major = element_line( color = '#E0E0E0', size = 0.4 ),
            panel_grid_minor = element_blank(),
            axis_title       = element_blank(),
            axis_text        = element_blank(),
            axis_ticks       = element_blank(),
            plot_background  = element_rect( fill = 'white' ),
            panel_background = element_rect( fill = '#F8F8F8' ),
        )
        + labs( title = f'{ pitch_type }' )
    )

    with warnings.catch_warnings():
        warnings.filterwarnings( 'ignore', category = PlotnineWarning )
        try:
            mpl_fig = p.draw()
            mpl_fig.savefig( buf, format = 'png', dpi = 150, bbox_inches = 'tight' )
            plt.close( mpl_fig )
        except Exception:
            fig, ax = plt.subplots( figsize = ( 5, 5 ) )
            ax.text( 0.5, 0.5, 'Plot error', fontsize = 14, ha = 'center', va = 'center' )
            ax.axis( 'off' )
            fig.savefig( buf, format = 'png', dpi = 150, bbox_inches = 'tight' )
            plt.close( fig )

    buf.seek( 0 )
    return buf
