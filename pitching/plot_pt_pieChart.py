import os
import matplotlib
matplotlib.use( 'Agg' )
import matplotlib.pyplot as plt
from matplotlib import font_manager
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


def pt_pieChart(
    df_p: pd.DataFrame,
    pt_color_dict: dict,
    batter_side: str = None,
    S: int = None,
    B: int = None,
    show_labels: bool = True,
    figsize: tuple = ( 1.8, 1.8 ),
    count_label: str = None,
) -> plt.Figure:

    df_p = df_p.copy()
    if batter_side is not None:
        df_p = df_p[ df_p[ '打席左右' ] == batter_side ]

    if S is not None:
        df_p = df_p[ df_p[ 'S' ] == S ]
    if B is not None:
        df_p = df_p[ df_p[ 'B' ] == B ]

    if count_label is not None:
        # ラベルを左余白に、pie を右側に配置
        fig = plt.figure( figsize = figsize )
        ax  = fig.add_axes( [ 0.35, 0.05, 0.6, 0.9 ] )
        fig.text(
            0.02, 0.88, count_label,
            ha         = 'left',
            va         = 'top',
            fontsize   = 11,
            fontweight = 'bold',
            color      = '#222222',
        )
    else:
        fig, ax = plt.subplots( figsize = figsize )

    if df_p.empty:
        ax.axis( 'off' )
        return fig

    pt_pct = ( df_p[ '球種' ].value_counts( normalize = True ) * 100 ).reset_index()
    pt_pct.columns = [ '球種', '投球割合' ]

    colors = [ pt_color_dict.get( k, '#888888' ) for k in pt_pct[ '球種' ] ]

    if show_labels:
        labels = [
            f"{row['球種']}\n{row['投球割合']:.1f}%" if row[ '投球割合' ] > 5 else row[ '球種' ]
            for _, row in pt_pct.iterrows()
        ]
        wedges, texts = ax.pie(
            pt_pct[ '投球割合' ], labels = labels, colors = colors, startangle = 90
        )
        for text, color in zip( texts, colors ):
            text.set_color( color )
    else:
        ax.pie( pt_pct[ '投球割合' ], colors = colors, startangle = 90 )

    ax.axis( 'off' )
    return fig
