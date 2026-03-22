"""打者分析モード – ランナー別作戦割合（円グラフ）"""
import datetime
import os

import matplotlib
matplotlib.use( 'Agg' )
import matplotlib.pyplot as plt
from matplotlib import font_manager
import numpy as np
import pandas as pd
import streamlit as st

from batting.analyse_strategy import (
    analyse_R1_strategy,
    analyse_R2_strategy,
    COUNT_KEYS,
)
from pitcher_analysis import _load_plays_df


# ── フォント ────────────────────────────────────────────────────
def _register_fonts():
    font_dir = os.path.join( os.path.dirname( __file__ ), 'fonts' )
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


# ── カラーパレット ──────────────────────────────────────────────
_COLORS = {
    '単打'   : '#4CAF50',
    '長打'   : '#1565C0',
    '四死球' : '#9C27B0',
    '三振'   : '#F44336',
    '犠打'   : '#FF9800',
    '盗塁成功': '#00BCD4',
    '盗塁失敗': '#B0BEC5',
    '進塁打' : '#8BC34A',
    '凡打'   : '#9E9E9E',
    '併殺'   : '#607D8B',
    '牽制死' : '#795548',
}


def _pie(ax, counts: dict, title: str):
    """円グラフを ax に描画する。0 のカテゴリは除外。"""
    items  = [ ( k, v ) for k, v in counts.items() if v > 0 ]
    total  = sum( v for _, v in items )

    if not items or total == 0:
        ax.text( 0.5, 0.5, 'データなし', ha='center', va='center', fontsize=12 )
        ax.axis( 'off' )
        ax.set_title( title, fontsize=12, fontweight='bold', pad=10 )
        return

    labels = [ f'{ k }\n{ v }件' for k, v in items ]
    sizes  = [ v for _, v in items ]
    colors = [ _COLORS.get( k, '#CCCCCC' ) for k, _ in items ]

    wedges, texts, autotexts = ax.pie(
        sizes,
        labels        = labels,
        colors        = colors,
        autopct       = lambda p: f'{p:.1f}%' if p >= 3 else '',
        startangle    = 90,
        pctdistance   = 0.75,
        labeldistance = 1.15,
        wedgeprops    = { 'linewidth': 0.8, 'edgecolor': 'white' },
    )
    for t in texts:
        t.set_fontsize( 9 )
    for at in autotexts:
        at.set_fontsize( 8 )
        at.set_color( 'white' )
        at.set_fontweight( 'bold' )

    ax.set_title( f'{ title }（n={ total }）', fontsize=12, fontweight='bold', pad=12 )


def _build_figure( counts_list: list ) -> plt.Figure:
    """3状況分の円グラフを横並びで描画した Figure を返す。"""
    fig, axes = plt.subplots( 1, 3, figsize=( 15, 6 ) )
    fig.patch.set_facecolor( 'white' )
    for ax, ( title, counts ) in zip( axes, counts_list ):
        _pie( ax, counts, title )
    plt.tight_layout( pad=2.0 )
    return fig


def _go_start():
    st.session_state.page_ctg = 'start'


def show() -> None:
    st.button( '← スタートに戻る', on_click=_go_start )
    st.header( '打者分析' )

    team_id = st.session_state.get( 'logged_in_team_id' )
    df = _load_plays_df( team_id )

    if df.empty:
        st.warning( 'データがありません。先に試合データを入力してください。' )
        return

    df = df.copy()
    df[ '攻撃チーム' ] = np.where( df[ '表裏' ] == '表', df[ '先攻チーム' ], df[ '後攻チーム' ] )

    # ── 期間フィルター ────────────────────────────────────────
    df[ '_date' ] = pd.to_datetime( df[ '試合日時' ], errors='coerce' )
    valid_dates   = df[ '_date' ].dropna()
    date_min = valid_dates.min().date() if not valid_dates.empty else datetime.date.today()
    date_max = valid_dates.max().date() if not valid_dates.empty else datetime.date.today()

    col_start, col_end, col_team = st.columns( 3 )
    with col_start:
        start_date = st.date_input( '開始日', value=date_min, key='bam_start' )
    with col_end:
        end_date = st.date_input( '終了日', value=date_max, key='bam_end' )

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
        selected_team = st.selectbox( '攻撃チーム', teams, index=team_idx, key='bam_team' )

    # ── 分析 ────────────────────────────────────────────────
    counts_0out_r1 = analyse_R1_strategy( df, selected_team, out=0 )
    counts_1out_r1 = analyse_R1_strategy( df, selected_team, out=1 )
    counts_r2      = analyse_R2_strategy( df, selected_team )

    counts_list = [
        ( '0アウト1塁',   counts_0out_r1 ),
        ( '1アウト1塁',   counts_1out_r1 ),
        ( 'ランナー2塁',  counts_r2      ),
    ]

    fig = _build_figure( counts_list )
    st.pyplot( fig, use_container_width=True )
    plt.close( fig )
