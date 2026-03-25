"""打者分析モード – 攻撃分析 / 作戦分析（盗塁）"""
import datetime
import gc
import io
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
from plays_cache import clear_team_plays_cache, get_cached_team_plays_df
from db import batter_comment_repo
from batter_stats_mode import (
    _build_stats_df,
    _fig_to_image,
    _generate_stats_pdf,
)


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
_IMG_CACHE = dict( ttl=1800, max_entries=48, show_spinner=False )

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

# ── 盗塁分析用定数 ──────────────────────────────────────────────
_STEAL_OPS = frozenset( [ '盗塁', 'エンドラン' ] )
_ADV_2ND   = frozenset( [ '二進', '三進', '本進' ] )
_ADV_3RD   = frozenset( [ '三進', '本進' ] )


# ── 攻撃分析 ヘルパー ────────────────────────────────────────────
def _pie( ax, counts: dict, title: str ):
    """円グラフを ax に描画する。0 のカテゴリは除外。"""
    items  = [ ( k, v ) for k, v in counts.items() if v > 0 ]
    total  = sum( v for _, v in items )

    if not items or total == 0:
        ax.text( 0.5, 0.5, 'データなし', ha='center', va='center', fontsize=12 )
        ax.axis( 'off' )
        ax.set_title( title, fontsize=15, fontweight='bold', pad=10 )
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
        labeldistance = 1.18,
        wedgeprops    = { 'linewidth': 0.8, 'edgecolor': 'white' },
    )
    for t in texts:
        t.set_fontsize( 15 )
    for at in autotexts:
        at.set_fontsize( 13 )
        at.set_color( 'white' )
        at.set_fontweight( 'bold' )

    ax.set_title( f'{ title }（n={ total }）', fontsize=17, fontweight='bold', pad=14 )


def _build_figure( counts_list: list ) -> plt.Figure:
    """3状況分の円グラフを横並びで描画した Figure を返す。"""
    fig, axes = plt.subplots( 1, 3, figsize=( 15, 6 ) )
    fig.patch.set_facecolor( 'white' )
    for ax, ( title, counts ) in zip( axes, counts_list ):
        _pie( ax, counts, title )
    plt.tight_layout( pad=2.0 )
    return fig


# ── バント分析用定数 ────────────────────────────────────────────
_SAC_BUNT_STRAT2  = frozenset( [ 'バント', '打からバント構え', 'バスター' ] )
_SAC_BUNT_RESULTS = frozenset( [ '犠打', '犠打失策' ] )

# ── 盗塁分析 ヘルパー ────────────────────────────────────────────
def _steal_rows( df: pd.DataFrame, base: int ) -> pd.DataFrame:
    """盗塁企図行を返す。base=2: 二盗, base=3: 三盗"""
    if base == 2:
        runner_col, block_col = '一走氏名', '二走氏名'
    else:
        runner_col, block_col = '二走氏名', '三走氏名'
    if '作戦' not in df.columns:
        return df.iloc[ :0 ]
    return df[
        df[ '作戦' ].isin( _STEAL_OPS ) &
        ( df[ '打球タイプ' ].fillna( '0' ) == '0' ) &
        ( df[ runner_col ].fillna( '0' ) != '0' ) &
        ( df[ block_col  ].fillna( '0' ) == '0' )
    ]


def _steal_stats( rows: pd.DataFrame, base: int ) -> tuple:
    """(企図数, 成功数) を返す。calc_runner_stats と同じロジック。"""
    col = '一走状況' if base == 2 else '二走状況'
    adv = _ADV_2ND   if base == 2 else _ADV_3RD
    if col not in rows.columns or rows.empty:
        return 0, 0
    success = int( rows[ col ].isin( adv ).sum() )
    failure = int( ( rows[ col ] == '封殺' ).sum() )
    return success + failure, success


def _pct_str( success: int, attempt: int ) -> str:
    return f'{ round( 100 * success / attempt, 1 ) }%' if attempt > 0 else '-'


def _pie_from_series( ax, series: pd.Series, title: str ):
    """pd.Series（index=ラベル, values=件数）から円グラフ描画。"""
    s = series[ series > 0 ].sort_index()
    if s.empty:
        ax.text( 0.5, 0.5, 'データなし', ha='center', va='center', fontsize=11 )
        ax.axis( 'off' )
        ax.set_title( title, fontsize=11, fontweight='bold' )
        return
    ax.pie(
        s.values,
        labels        = [ f'{ k }\n{ v }件' for k, v in s.items() ],
        autopct       = lambda p: f'{p:.1f}%' if p >= 5 else '',
        startangle    = 90,
        pctdistance   = 0.75,
        labeldistance = 1.18,
        wedgeprops    = { 'linewidth': 0.8, 'edgecolor': 'white' },
        textprops     = { 'fontsize': 13 },
    )
    ax.set_title( f'{ title }（n={ int( s.sum() ) }）', fontsize=15, fontweight='bold', pad=12 )


def _show_steal_section( df_team: pd.DataFrame ):
    """作戦分析（盗塁）セクションを描画する。"""
    st.markdown( '## 作戦分析（盗塁）' )

    rows2 = _steal_rows( df_team, 2 )
    rows3 = _steal_rows( df_team, 3 )

    # ── 盗塁データ テーブル ──────────────────────────────────
    st.markdown( '### 盗塁データ' )
    a2, s2 = _steal_stats( rows2, 2 )
    a3, s3 = _steal_stats( rows3, 3 )

    summary_df = pd.DataFrame( [
        { '': '二盗', '企図数': a2, '成功数': s2, '成功率': _pct_str( s2, a2 ) },
        { '': '三盗', '企図数': a3, '成功数': s3, '成功率': _pct_str( s3, a3 ) },
    ] ).set_index( '' )
    st.dataframe( summary_df, use_container_width=False )

    # ── 盗塁数 テーブル（選手別） ────────────────────────────
    st.markdown( '### 盗塁数' )
    runner2_col = '一走氏名'
    runner3_col = '二走氏名'

    players2 = rows2[ runner2_col ].dropna().unique().tolist() if not rows2.empty and runner2_col in rows2.columns else []
    players3 = rows3[ runner3_col ].dropna().unique().tolist() if not rows3.empty and runner3_col in rows3.columns else []
    all_players = sorted( set( players2 ) | set( players3 ) )

    player_records = []
    for player in all_players:
        p2 = rows2[ rows2[ runner2_col ] == player ] if not rows2.empty else rows2
        p3 = rows3[ rows3[ runner3_col ] == player ] if not rows3.empty else rows3
        pa2, ps2 = _steal_stats( p2, 2 )
        pa3, ps3 = _steal_stats( p3, 3 )
        if pa2 + pa3 == 0:
            continue
        rate2 = ps2 / pa2 if pa2 > 0 else 0.0
        player_records.append( {
            '選手名'    : player,
            '二盗企図'  : pa2,
            '二盗成功率': _pct_str( ps2, pa2 ),
            '三盗企図'  : pa3,
            '三盗成功率': _pct_str( ps3, pa3 ),
            '_sort_a2'  : pa2,
            '_sort_r2'  : rate2,
        } )

    if player_records:
        df_p = (
            pd.DataFrame( player_records )
            .sort_values( [ '_sort_a2', '_sort_r2' ], ascending=False )
            .drop( columns=[ '_sort_a2', '_sort_r2' ] )
            .set_index( '選手名' )
        )
        st.dataframe( df_p, use_container_width=False )
    else:
        st.info( '盗塁成功データなし' )

    # ── 状況 円グラフ ────────────────────────────────────────
    st.markdown( '### 状況' )

    def _count_col( rows: pd.DataFrame, col: str ) -> pd.Series:
        if col not in rows.columns or rows.empty:
            return pd.Series( dtype=int )
        return rows[ col ].fillna( '不明' ).astype( str ).value_counts()

    def _sb_series( rows: pd.DataFrame ) -> pd.Series:
        if rows.empty or 'S' not in rows.columns or 'B' not in rows.columns:
            return pd.Series( dtype=int )
        label = (
            rows[ 'S' ].fillna( '?' ).astype( str ) + '-' +
            rows[ 'B' ].fillna( '?' ).astype( str )
        )
        return label.value_counts()

    out2  = _count_col( rows2, 'アウト' )
    sb2   = _sb_series( rows2 )
    out3  = _count_col( rows3, 'アウト' )
    sb3   = _sb_series( rows3 )

    fig, axes = plt.subplots( 2, 2, figsize=( 14, 10 ) )
    fig.patch.set_facecolor( 'white' )
    _pie_from_series( axes[ 0, 0 ], out2, '二盗 × アウトカウント' )
    _pie_from_series( axes[ 0, 1 ], sb2,  '二盗 × S-Bカウント'   )
    _pie_from_series( axes[ 1, 0 ], out3, '三盗 × アウトカウント' )
    _pie_from_series( axes[ 1, 1 ], sb3,  '三盗 × S-Bカウント'   )
    plt.tight_layout( pad=2.5 )
    st.pyplot( fig, use_container_width=True )
    plt.close( fig )


def _table_fig( df: pd.DataFrame, title: str ) -> plt.Figure:
    """DataFrame を matplotlib テーブルとして描画した Figure を返す。"""
    if df.empty:
        fig, ax = plt.subplots( figsize=( 4, 1 ) )
        ax.axis( 'off' )
        ax.text( 0.5, 0.5, 'データなし', ha='center', va='center', fontsize=10 )
        ax.set_title( title, fontweight='bold', loc='left' )
        return fig

    df_r   = df.reset_index()
    cols   = df_r.columns.tolist()
    n_cols = len( cols )
    n_rows = len( df_r )
    fig_h  = max( 1.2, ( n_rows + 1 ) * 0.38 )
    fig_w  = max( 4,   n_cols * 1.1 )

    fig, ax = plt.subplots( figsize=( fig_w, fig_h ) )
    ax.axis( 'off' )
    ax.set_title( title, fontweight='bold', loc='left', pad=4, fontsize=10 )

    all_text = [ cols ] + df_r.fillna( '' ).astype( str ).values.tolist()
    table = ax.table( cellText=all_text, cellLoc='center', bbox=[ 0, 0, 1, 1 ] )
    table.auto_set_font_size( False )
    table.set_fontsize( 9 )
    table.auto_set_column_width( list( range( n_cols ) ) )
    for ( r, c ), cell in table._cells.items():
        cell.set_edgecolor( '#CBD5E1' )
        cell.set_linewidth( 0.3 )
        cell.PAD = 0.04
        if r == 0:
            cell.set_facecolor( '#1E293B' )
            cell.set_text_props( color='white', fontweight='bold' )
        else:
            cell.set_facecolor( '#F8FAFC' if r % 2 == 1 else 'white' )
    plt.tight_layout()
    return fig


def _generate_strategy_pdf(
    df: pd.DataFrame,
    df_team: pd.DataFrame,
    selected_team: str,
    start_date,
    end_date,
) -> io.BytesIO:
    """チーム作戦分析 PDF を1ページで生成して BytesIO で返す。"""
    from matplotlib.gridspec import GridSpec, GridSpecFromSubplotSpec

    # ─── カラー定義 ────────────────────────────────────────────
    C_BG      = '#F0F4F8'
    C_HDR     = '#0F172A'   # ヘッダー背景（ダークネイビー）
    C_ACCENT  = '#1E3A5F'   # セクションバー背景（濃紺）
    C_TBL_HDR = '#BFDBFE'   # テーブルヘッダー背景（淡い青）
    C_TBL_ALT = '#F1F5F9'

    # ─── データ準備：攻撃分析 ──────────────────────────────────
    counts_list = [
        ( '0アウト1塁',  analyse_R1_strategy( df, selected_team, out=0 ) ),
        ( '1アウト1塁',  analyse_R1_strategy( df, selected_team, out=1 ) ),
        ( 'ランナー2塁', analyse_R2_strategy( df, selected_team )        ),
    ]

    # ─── データ準備：盗塁 ─────────────────────────────────────
    rows2 = _steal_rows( df_team, 2 )
    rows3 = _steal_rows( df_team, 3 )
    a2_t, s2_t = _steal_stats( rows2, 2 )
    a3_t, s3_t = _steal_stats( rows3, 3 )

    steal_summary_df = pd.DataFrame( [
        { '': '二盗', '企図数': a2_t, '成功数': s2_t, '成功率': _pct_str( s2_t, a2_t ) },
        { '': '三盗', '企図数': a3_t, '成功数': s3_t, '成功率': _pct_str( s3_t, a3_t ) },
    ] ).set_index( '' )

    runner2_col, runner3_col = '一走氏名', '二走氏名'
    players2 = rows2[ runner2_col ].dropna().unique().tolist() if not rows2.empty and runner2_col in rows2.columns else []
    players3 = rows3[ runner3_col ].dropna().unique().tolist() if not rows3.empty and runner3_col in rows3.columns else []
    p_records = []
    for player in sorted( set( players2 ) | set( players3 ) ):
        p2 = rows2[ rows2[ runner2_col ] == player ] if not rows2.empty else rows2
        p3 = rows3[ rows3[ runner3_col ] == player ] if not rows3.empty else rows3
        pa2, ps2 = _steal_stats( p2, 2 )
        pa3, ps3 = _steal_stats( p3, 3 )
        if pa2 + pa3 == 0:
            continue
        p_records.append( {
            '選手名'    : player,
            '二盗企図'  : pa2, '二盗成功率': _pct_str( ps2, pa2 ),
            '三盗企図'  : pa3, '三盗成功率': _pct_str( ps3, pa3 ),
            '_a2': pa2, '_r2': ps2 / pa2 if pa2 > 0 else 0.0,
        } )
    player_steal_df = (
        pd.DataFrame( p_records )
        .sort_values( [ '_a2', '_r2' ], ascending=False )
        .drop( columns=[ '_a2', '_r2' ] )
        .set_index( '選手名' )
    ) if p_records else pd.DataFrame()

    def _cnt( rows, col ):
        return rows[ col ].fillna( '不明' ).astype( str ).value_counts() if col in rows.columns and not rows.empty else pd.Series( dtype=int )
    def _sb( rows ):
        if rows.empty or 'S' not in rows.columns or 'B' not in rows.columns:
            return pd.Series( dtype=int )
        return ( rows[ 'S' ].fillna( '?' ).astype( str ) + '-' + rows[ 'B' ].fillna( '?' ).astype( str ) ).value_counts()

    # ─── データ準備：バント ───────────────────────────────────
    comp = df_team[
        ( df_team[ '打席の継続' ] == '打席完了' ) &
        df_team[ '打席結果' ].notna() &
        ( df_team[ '打席結果' ] != '0' ) &
        ( df_team[ '打席結果' ] != '' )
    ].copy()
    if '作戦2' in df_team.columns and not comp.empty:
        bk = (
            df_team[ df_team[ '作戦2' ].isin( _SAC_BUNT_STRAT2 ) ]
            [ [ '打者氏名', '回', '打順' ] ].drop_duplicates().assign( _sac_att=True )
        )
        comp = comp.merge( bk, on=[ '打者氏名', '回', '打順' ], how='left' )
        comp[ '_sac_att' ] = comp[ '_sac_att' ].fillna( False )
    else:
        comp[ '_sac_att' ] = False

    bunt_rows = []
    for label, r1, r2 in [ ( 'R1', True, False ), ( 'R2', False, True ), ( 'R12', True, True ) ]:
        rmask = _runner_mask( comp, r1, r2 )
        for out in [ 0, 1 ]:
            omask   = pd.to_numeric( comp[ 'アウト' ], errors='coerce' ) == out
            sit_df  = comp[ rmask & omask ]
            n_plate = len( sit_df )
            n_att   = int( sit_df[ '_sac_att' ].sum() )
            n_suc   = int( sit_df[ sit_df[ '_sac_att' ] ][ '打撃結果' ].isin( _SAC_BUNT_RESULTS ).sum() ) if n_att > 0 and '打撃結果' in sit_df.columns else 0
            bunt_rows.append( {
                '状況'  : f'{ out }死 { label }',
                '企図数': n_att,
                '企図率': f'{ round( 100 * n_att / n_plate, 1 ) }%' if n_plate > 0 else '-',
                '成功率': f'{ round( 100 * n_suc  / n_att,   1 ) }%' if n_att   > 0 else '-',
            } )
    bunt_df = pd.DataFrame( bunt_rows ).set_index( '状況' )

    safety_df = pd.DataFrame()
    if '作戦2' in df_team.columns and '作戦結果' in df_team.columns:
        sfty = df_team[ df_team[ '作戦2' ] == 'セフティ' ]
        if not sfty.empty and '打者氏名' in sfty.columns:
            sr = [
                { '選手名': p, '企図数': len( g ),
                  '成功数': int( ( g[ '作戦結果' ] == '成功' ).sum() ),
                  '失敗数': int( ( g[ '作戦結果' ] == '失敗' ).sum() ) }
                for p, g in sfty.groupby( '打者氏名', sort=False )
            ]
            if sr:
                safety_df = pd.DataFrame( sr ).sort_values( '企図数', ascending=False ).set_index( '選手名' )

    sq_df = pd.DataFrame()
    if '作戦2' in df_team.columns and '作戦結果' in df_team.columns:
        def _sq( v ):
            r = df_team[ df_team[ '作戦2' ] == v ]
            n = len( r )
            s = int( ( r[ '作戦結果' ] == '成功' ).sum() ) if n > 0 else 0
            return n, s
        sq_a1, sq_s1 = _sq( 'スクイズ' )
        sq_a2, sq_s2 = _sq( 'Sスクイズ' )
        sq_df = pd.DataFrame( [
            { '': 'スクイズ',         '企図数': sq_a1, '成功数': sq_s1, '成功率': _pct_str( sq_s1, sq_a1 ) },
            { '': 'セフティスクイズ', '企図数': sq_a2, '成功数': sq_s2, '成功率': _pct_str( sq_s2, sq_a2 ) },
        ] ).set_index( '' )

    C_TITLE  = '#0F172A'
    _TITLE_H = 0.22       # タイトル領域の高さ比率（A4用に調整）

    # ─── フォントサイズ定数（横向き A4 サイズ用）────────────────
    FS_HDR_TITLE = 16
    FS_HDR_SUB   = 8
    FS_SECTION   = 10
    FS_TBL_TITLE = 7
    FS_TBL       = 6.5
    FS_NODATA    = 6

    # ─── ヘルパー（A4 用フォントサイズ）────────────────────────
    def _draw_tbl( ax, df_t ):
        ax.axis( 'off' )
        ax.add_patch( plt.Rectangle(
            ( 0, 0 ), 1, 1, transform=ax.transAxes,
            facecolor=C_BG, edgecolor='none', zorder=0,
        ) )
        if df_t.empty:
            ax.text( 0.5, 0.5, 'データなし', ha='center', va='center',
                     fontsize=FS_NODATA, color='#64748B', transform=ax.transAxes )
            return
        dr     = df_t.reset_index()
        cols   = dr.columns.tolist()
        n_cols = len( cols )
        # 列名を2文字ごとに折り返し（CJK 列ヘッダーのはみ出し防止）
        def _wrap_header( s ):
            return '\n'.join( s[ i:i+2 ] for i in range( 0, len( s ), 2 ) )
        display_cols = [ _wrap_header( c ) for c in cols ]
        # CJK 対応：col 0（名前列）に幅を多く割り当てる
        if n_cols == 1:
            col_widths = [ 1.0 ]
        else:
            col_widths = [ 0.35 ] + [ 0.65 / ( n_cols - 1 ) ] * ( n_cols - 1 )
        tbl = ax.table(
            cellText  = [ display_cols ] + dr.fillna( '' ).astype( str ).values.tolist(),
            cellLoc   = 'center',
            bbox      = [ 0, 0, 1, 1 - _TITLE_H ],
            colWidths = col_widths,
        )
        tbl.auto_set_font_size( False )
        tbl.set_fontsize( FS_TBL )
        for ( r, c ), cell in tbl._cells.items():
            cell.set_edgecolor( '#CBD5E1' )
            cell.set_linewidth( 0.5 )
            cell.PAD = 0.05
            if r == 0:
                cell.set_facecolor( C_TBL_HDR )
                cell.set_text_props( color='#1E293B', fontweight='bold' )
            else:
                cell.set_facecolor( C_TBL_ALT if r % 2 == 1 else 'white' )

    def _section_ax( ax, label ):
        ax.axis( 'off' )
        ax.add_patch( plt.Rectangle(
            ( 0, 0 ), 1, 1, transform=ax.transAxes,
            facecolor=C_ACCENT, edgecolor='none', zorder=0,
        ) )
        ax.text( 0.02, 0.5, label, color='white',
                 fontsize=FS_SECTION, fontweight='bold', va='center',
                 transform=ax.transAxes, zorder=1 )

    def _tbl_title( ax, label ):
        top = 1 - _TITLE_H / 2
        ax.text( 0.02, top, label, color=C_TITLE,
                 fontsize=FS_TBL_TITLE, fontweight='bold', va='center',
                 transform=ax.transAxes, clip_on=False )
        ax.plot( [ 0, 1 ], [ 1 - _TITLE_H, 1 - _TITLE_H ],
                 color=C_ACCENT, linewidth=1.0,
                 transform=ax.transAxes, clip_on=False )

    def _pie_pdf( ax, counts, title ):
        """PDF用 小サイズ円グラフ"""
        items = [ ( k, v ) for k, v in counts.items() if v > 0 ]
        total = sum( v for _, v in items )
        if not items or total == 0:
            ax.text( 0.5, 0.5, 'データなし', ha='center', va='center', fontsize=FS_NODATA )
            ax.axis( 'off' )
            ax.set_title( title, fontsize=FS_TBL_TITLE, fontweight='bold', pad=4 )
            return
        labels = [ f'{ k }\n{ v }件' for k, v in items ]
        sizes  = [ v for _, v in items ]
        colors = [ _COLORS.get( k, '#CCCCCC' ) for k, _ in items ]
        wedges, texts, autotexts = ax.pie(
            sizes, labels=labels, colors=colors,
            autopct=lambda p: f'{p:.0f}%' if p >= 5 else '',
            startangle=90, pctdistance=0.75, labeldistance=1.15,
            wedgeprops={ 'linewidth': 0.5, 'edgecolor': 'white' },
        )
        for t in texts:
            t.set_fontsize( 5.5 )
        for at in autotexts:
            at.set_fontsize( 5 )
            at.set_color( 'white' )
            at.set_fontweight( 'bold' )
        ax.set_title( f'{ title }（n={ total }）',
                      fontsize=FS_TBL_TITLE, fontweight='bold', pad=4 )

    def _pie_from_series_pdf( ax, series, title ):
        """PDF用 小サイズ円グラフ（Series版）"""
        s = series[ series > 0 ].sort_index() if not series.empty else series
        if s.empty:
            ax.text( 0.5, 0.5, 'データなし', ha='center', va='center', fontsize=FS_NODATA )
            ax.axis( 'off' )
            ax.set_title( title, fontsize=FS_TBL_TITLE, fontweight='bold' )
            return
        ax.pie(
            s.values,
            labels=[ f'{ k }\n{ v }件' for k, v in s.items() ],
            autopct=lambda p: f'{p:.0f}%' if p >= 8 else '',
            startangle=90, pctdistance=0.75, labeldistance=1.15,
            wedgeprops={ 'linewidth': 0.5, 'edgecolor': 'white' },
            textprops={ 'fontsize': 5.5 },
        )
        ax.set_title( f'{ title }（n={ int( s.sum() ) }）',
                      fontsize=FS_TBL_TITLE, fontweight='bold', pad=4 )

    # ─── フィギュア構築（横向き A4）───────────────────────────
    fig = plt.figure( figsize=( 11.69, 8.27 ), facecolor=C_BG )

    gs_main = GridSpec( 2, 1, figure=fig,
                        height_ratios=[ 1.0, 7.0 ],
                        hspace=0.03,
                        left=0.01, right=0.99, top=0.97, bottom=0.02 )

    # ── ヘッダー ─────────────────────────────────────────────
    ax_hdr = fig.add_subplot( gs_main[ 0 ] )
    ax_hdr.axis( 'off' )
    ax_hdr.add_patch( plt.Rectangle(
        ( 0, 0 ), 1, 1, transform=ax_hdr.transAxes,
        facecolor=C_HDR, edgecolor='none', zorder=0,
    ) )
    ax_hdr.text( 0.015, 0.62, 'チーム作戦分析',
                 color='white', fontsize=FS_HDR_TITLE, fontweight='bold',
                 va='center', transform=ax_hdr.transAxes, zorder=1 )
    ax_hdr.text( 0.015, 0.22,
                 f'{ selected_team }　{ start_date } 〜 { end_date }',
                 color='#93C5FD', fontsize=FS_HDR_SUB,
                 va='center', transform=ax_hdr.transAxes, zorder=1 )

    # ── 3列コンテンツ ─────────────────────────────────────────
    gs_content = GridSpecFromSubplotSpec(
        1, 3, subplot_spec=gs_main[ 1 ], wspace=0.07,
    )

    # ── 列0：攻撃分析 ─────────────────────────────────────────
    gs_atk = GridSpecFromSubplotSpec(
        4, 1, subplot_spec=gs_content[ 0, 0 ],
        height_ratios=[ 0.22, 1, 1, 1 ], hspace=0.22,
    )
    _section_ax( fig.add_subplot( gs_atk[ 0 ] ), '攻撃分析' )
    for i, ( title, counts ) in enumerate( counts_list ):
        ax = fig.add_subplot( gs_atk[ i + 1 ] )
        ax.set_facecolor( C_BG )
        _pie_pdf( ax, counts, title )

    # ── 列1：作戦分析（盗塁）──────────────────────────────────
    gs_steal = GridSpecFromSubplotSpec(
        4, 2, subplot_spec=gs_content[ 0, 1 ],
        height_ratios=[ 0.22, 1.8, 1, 1 ], hspace=0.45, wspace=0.08,
    )
    ax_sl = fig.add_subplot( gs_steal[ 0, : ] )
    _section_ax( ax_sl, '作戦分析（盗塁）' )

    ax_sd = fig.add_subplot( gs_steal[ 1, 0 ] )
    ax_sp = fig.add_subplot( gs_steal[ 1, 1 ] )
    _tbl_title( ax_sd, '盗塁データ' )
    _tbl_title( ax_sp, '盗塁数（選手別）' )
    _draw_tbl( ax_sd, steal_summary_df )
    _draw_tbl( ax_sp, player_steal_df )

    for ax, series, title in [
        ( fig.add_subplot( gs_steal[ 2, 0 ] ), _cnt( rows2, 'アウト' ), '二盗×アウト' ),
        ( fig.add_subplot( gs_steal[ 2, 1 ] ), _sb( rows2 ),            '二盗×カウント' ),
        ( fig.add_subplot( gs_steal[ 3, 0 ] ), _cnt( rows3, 'アウト' ), '三盗×アウト' ),
        ( fig.add_subplot( gs_steal[ 3, 1 ] ), _sb( rows3 ),            '三盗×カウント' ),
    ]:
        ax.set_facecolor( C_BG )
        _pie_from_series_pdf( ax, series, title )

    # ── 列2：作戦分析（バント）──────────────────────────────────
    gs_bunt = GridSpecFromSubplotSpec(
        4, 1, subplot_spec=gs_content[ 0, 2 ],
        height_ratios=[ 0.22, 2.5, 1.4, 0.9 ], hspace=0.45,
    )
    _section_ax( fig.add_subplot( gs_bunt[ 0 ] ), '作戦分析（バント）' )

    for ax_b, df_b, lbl in [
        ( fig.add_subplot( gs_bunt[ 1 ] ), bunt_df,   '犠打' ),
        ( fig.add_subplot( gs_bunt[ 2 ] ), safety_df, 'セフティ' ),
        ( fig.add_subplot( gs_bunt[ 3 ] ), sq_df,     'スクイズ' ),
    ]:
        _tbl_title( ax_b, lbl )
        _draw_tbl( ax_b, df_b )

    # ─── 出力 ─────────────────────────────────────────────────
    buf = io.BytesIO()
    fig.savefig( buf, format='pdf', bbox_inches='tight', facecolor=C_BG )
    plt.close( fig )
    buf.seek( 0 )
    return buf


def _runner_mask( df: pd.DataFrame, r1: bool, r2: bool ) -> pd.Series:
    """走者状況マスク。r1=True: 一走あり, r2=True: 二走あり（三走は常にnし）"""
    h1 = df[ '一走氏名' ].fillna( '0' ) != '0'
    h2 = df[ '二走氏名' ].fillna( '0' ) != '0'
    n3 = df[ '三走氏名' ].fillna( '0' ) == '0'
    if r1 and not r2:
        return h1 & ~h2 & n3
    elif r2 and not r1:
        return ~h1 & h2 & n3
    else:  # R12
        return h1 & h2 & n3


def _show_bunt_section( df_team: pd.DataFrame ):
    """作戦分析（バント）セクションを描画する。"""
    st.markdown( '## 作戦分析（バント）' )

    # 打席完了行
    comp = df_team[
        ( df_team[ '打席の継続' ] == '打席完了' ) &
        df_team[ '打席結果' ].notna() &
        ( df_team[ '打席結果' ] != '0' ) &
        ( df_team[ '打席結果' ] != '' )
    ].copy()

    # 犠打企図 at-bat を全投球行から特定してマージ
    if '作戦2' in df_team.columns and not comp.empty:
        bunt_keys = (
            df_team[ df_team[ '作戦2' ].isin( _SAC_BUNT_STRAT2 ) ]
            [ [ '打者氏名', '回', '打順' ] ]
            .drop_duplicates()
            .assign( _sac_att=True )
        )
        comp = comp.merge( bunt_keys, on=[ '打者氏名', '回', '打順' ], how='left' )
        comp[ '_sac_att' ] = comp[ '_sac_att' ].fillna( False )
    else:
        comp[ '_sac_att' ] = False

    # ── 犠打 テーブル ─────────────────────────────────────────
    st.markdown( '### 犠打' )

    situations = [
        ( 'R1',  True,  False ),
        ( 'R2',  False, True  ),
        ( 'R12', True,  True  ),
    ]
    bunt_rows = []
    for label, r1, r2 in situations:
        rmask = _runner_mask( comp, r1, r2 )
        for out in [ 0, 1 ]:
            omask   = pd.to_numeric( comp[ 'アウト' ], errors='coerce' ) == out
            sit_df  = comp[ rmask & omask ]
            n_plate = len( sit_df )
            n_att   = int( sit_df[ '_sac_att' ].sum() )
            n_suc   = (
                int( sit_df[ sit_df[ '_sac_att' ] ][ '打撃結果' ].isin( _SAC_BUNT_RESULTS ).sum() )
                if n_att > 0 and '打撃結果' in sit_df.columns else 0
            )
            bunt_rows.append( {
                '状況'  : f'{ out }死 { label }',
                '企図数': n_att,
                '企図率': f'{ round( 100 * n_att / n_plate, 1 ) }%' if n_plate > 0 else '-',
                '成功率': f'{ round( 100 * n_suc  / n_att,   1 ) }%' if n_att   > 0 else '-',
            } )

    st.dataframe( pd.DataFrame( bunt_rows ).set_index( '状況' ), use_container_width=False )

    # ── セフティ テーブル ─────────────────────────────────────
    st.markdown( '### セフティ' )

    if '作戦2' in df_team.columns and '作戦結果' in df_team.columns:
        safety_df = df_team[ df_team[ '作戦2' ] == 'セフティ' ]
        if not safety_df.empty and '打者氏名' in safety_df.columns:
            s_records = []
            for player, grp in safety_df.groupby( '打者氏名', sort=False ):
                n_att  = len( grp )
                n_suc  = int( ( grp[ '作戦結果' ] == '成功' ).sum() )
                n_fail = int( ( grp[ '作戦結果' ] == '失敗' ).sum() )
                s_records.append( {
                    '選手名': player, '企図数': n_att, '成功数': n_suc, '失敗数': n_fail,
                } )
            if s_records:
                st.dataframe(
                    pd.DataFrame( s_records )
                    .sort_values( '企図数', ascending=False )
                    .set_index( '選手名' ),
                    use_container_width=False,
                )
            else:
                st.info( 'セフティデータなし' )
        else:
            st.info( 'セフティデータなし' )
    else:
        st.info( 'データなし' )

    # ── スクイズ テーブル ─────────────────────────────────────
    st.markdown( '### スクイズ' )

    if '作戦2' in df_team.columns and '作戦結果' in df_team.columns:
        def _sq_stats( strat2_val: str ) -> tuple:
            rows  = df_team[ df_team[ '作戦2' ] == strat2_val ]
            n_att = len( rows )
            n_suc = int( ( rows[ '作戦結果' ] == '成功' ).sum() ) if n_att > 0 else 0
            return n_att, n_suc

        a1, s1 = _sq_stats( 'スクイズ' )
        a2, s2 = _sq_stats( 'Sスクイズ' )
        sq_df = pd.DataFrame( [
            { '': 'スクイズ',       '企図数': a1, '成功数': s1, '成功率': _pct_str( s1, a1 ) },
            { '': 'セフティスクイズ', '企図数': a2, '成功数': s2, '成功率': _pct_str( s2, a2 ) },
        ] ).set_index( '' )
        st.dataframe( sq_df, use_container_width=False )
    else:
        st.info( 'データなし' )


# ── キャッシュ付き描画ヘルパー ────────────────────────────────────
# キャッシュキーはプリミティブ値のみ（DataFrame ハッシュコスト削減）

def _apply_filters( df: pd.DataFrame, start_date, end_date, selected_team ):
    """(df_team, df_team_all) を返す高速フィルタ（キャッシュなし）。"""
    df_team_all = df[ df[ '攻撃チーム' ] == selected_team ]
    df_filtered  = df[
        ( df[ '_date' ].dt.date >= start_date ) &
        ( df[ '_date' ].dt.date <= end_date   )
    ]
    df_team = df_filtered[ df_filtered[ '攻撃チーム' ] == selected_team ]
    return df_team, df_team_all


@st.cache_data( **_IMG_CACHE )
def _cached_stats_list_image(
    team_id: int, start_date, end_date, selected_team: str, side
) -> bytes | None:
    """スタッツ一覧タブの統計テーブル画像（side: None/'右'/'左'）。"""
    from batting.plot_statsTable import plot_battingStatsTable
    df = get_cached_team_plays_df( team_id )
    if df.empty:
        return None
    df_team, _ = _apply_filters( df, start_date, end_date, selected_team )
    _df_s = _build_stats_df( df_team, side )
    if _df_s.empty:
        return None
    fig = plot_battingStatsTable( _df_s )
    return _fig_to_image( fig, dpi=300 ).getvalue()


@st.cache_data( **_IMG_CACHE )
def _cached_strategy_figure(
    team_id: int, start_date, end_date, selected_team: str
) -> bytes:
    """チーム作戦分析の円グラフ画像。"""
    df = get_cached_team_plays_df( team_id )
    df_filtered = df[
        ( df[ '_date' ].dt.date >= start_date ) &
        ( df[ '_date' ].dt.date <= end_date   )
    ]
    counts_0out_r1 = analyse_R1_strategy( df_filtered, selected_team, out=0 )
    counts_1out_r1 = analyse_R1_strategy( df_filtered, selected_team, out=1 )
    counts_r2      = analyse_R2_strategy( df_filtered, selected_team )
    counts_list = [
        ( '0アウト1塁',  counts_0out_r1 ),
        ( '1アウト1塁',  counts_1out_r1 ),
        ( 'ランナー2塁', counts_r2      ),
    ]
    fig = _build_figure( counts_list )
    buf = io.BytesIO()
    fig.savefig( buf, format='png', dpi=300, bbox_inches='tight' )
    plt.close( fig )
    buf.seek( 0 )
    return buf.getvalue()


@st.cache_data( **_IMG_CACHE )
def _cached_course_chart(
    team_id: int, start_date, end_date, selected_team: str,
    batter_name: str, side
) -> bytes | None:
    df = get_cached_team_plays_df( team_id )
    if df.empty:
        return None
    df_team, _ = _apply_filters( df, start_date, end_date, selected_team )
    df_b = df_team[ df_team[ '打者氏名' ] == batter_name ]
    df_side = df_b if side is None else (
        df_b[ df_b[ '投手左右' ] == side ] if '投手左右' in df_b.columns else df_b.iloc[ 0:0 ]
    )
    buf = _calc_course_chart( df_side )
    return buf.getvalue() if buf else None


@st.cache_data( **_IMG_CACHE )
def _cached_detail_plot(
    team_id: int, start_date, end_date, selected_team: str,
    batter_name: str, side, pitch_type: str
) -> bytes | None:
    from pitching.plot_courseDetail import course_detailPlot
    df = get_cached_team_plays_df( team_id )
    if df.empty:
        return None
    df_team, _ = _apply_filters( df, start_date, end_date, selected_team )
    df_b = df_team[ df_team[ '打者氏名' ] == batter_name ]
    df_side = df_b if side is None else (
        df_b[ df_b[ '投手左右' ] == side ] if '投手左右' in df_b.columns else df_b.iloc[ 0:0 ]
    )
    buf = course_detailPlot( df_side, pitch_type=pitch_type )
    return buf.getvalue() if buf else None


@st.cache_data( **_IMG_CACHE )
def _cached_batted_plot(
    team_id: int, start_date, end_date, selected_team: str,
    batter_name: str, side, pitch_type: str
) -> bytes | None:
    from pitching.plot_battedBall import batted_ball_plot
    df = get_cached_team_plays_df( team_id )
    if df.empty:
        return None
    df_team, _ = _apply_filters( df, start_date, end_date, selected_team )
    df_b = df_team[ df_team[ '打者氏名' ] == batter_name ]
    df_side = df_b if side is None else (
        df_b[ df_b[ '投手左右' ] == side ] if '投手左右' in df_b.columns else df_b.iloc[ 0:0 ]
    )
    buf = batted_ball_plot( df_side, pitch_type=pitch_type )
    return buf.getvalue() if buf else None


@st.cache_data( **_IMG_CACHE )
def _cached_stats_table(
    team_id: int, start_date, end_date, selected_team: str,
    batter_name: str, stats_cols
) -> bytes:
    from batting.calc_stats import calc_batting_stats
    from batting.plot_statsTable import plot_battingStatsTable
    df = get_cached_team_plays_df( team_id )
    df_team, df_team_all = _apply_filters( df, start_date, end_date, selected_team )
    df_b     = df_team    [ df_team    [ '打者氏名' ] == batter_name ]
    df_b_all = df_team_all[ df_team_all[ '打者氏名' ] == batter_name ]
    rows = []
    for df_src, side, lbl in [
        ( df_b,     None, '対全投手' ),
        ( df_b,     '右',  '対右投手' ),
        ( df_b,     '左',  '対左投手' ),
        ( df_b_all, None,  '平均'    ),
    ]:
        df_s = df_src if side is None else (
            df_src[ df_src[ '投手左右' ] == side ]
            if '投手左右' in df_src.columns else df_src.iloc[ 0:0 ]
        )
        rows.append( calc_batting_stats( df_s, None, lbl ) )
    df_st = pd.DataFrame( rows )
    if stats_cols:
        df_st = df_st[ list( stats_cols ) ]
    return _fig_to_image( plot_battingStatsTable( df_st ), dpi=300 ).getvalue()


@st.cache_data( **_IMG_CACHE )
def _cached_pitchtype_stats(
    team_id: int, start_date, end_date, selected_team: str,
    batter_name: str, side, stats_cols
) -> bytes:
    from batting.calc_stats import calc_batting_stats
    from batting.plot_statsTable import plot_battingStatsTable
    df = get_cached_team_plays_df( team_id )
    df_team, _ = _apply_filters( df, start_date, end_date, selected_team )
    df_b = df_team[ df_team[ '打者氏名' ] == batter_name ]
    df_side = df_b if side is None else (
        df_b[ df_b[ '投手左右' ] == side ] if '投手左右' in df_b.columns else df_b.iloc[ 0:0 ]
    )
    _GROUPS = [
        ( 'ストレート', [ 'ストレート' ] ),
        ( 'スラ系',    [ 'スライダー', 'カット', 'カーブ' ] ),
        ( '落ち系',    [ 'フォーク', 'チェンジ', 'ツーシーム', 'シュート', 'シンカー' ] ),
    ]
    rows = []
    for lbl, pt_group in _GROUPS:
        df_g = df_side[ df_side[ '球種' ].isin( pt_group ) ] \
            if '球種' in df_side.columns else df_side.iloc[ 0:0 ]
        rows.append( calc_batting_stats( df_g, None, lbl ) )
    df_pt = pd.DataFrame( rows )
    if stats_cols:
        df_pt = df_pt[ list( stats_cols ) ]
    return _fig_to_image( plot_battingStatsTable( df_pt, highlight_last=False ), dpi=300 ).getvalue()


def _generate_player_pdf(
    selected_batters: list,
    df_team:     pd.DataFrame,
    df_team_all: pd.DataFrame,
    selected_team: str,
    start_date,
    end_date,
    stats_cols,
    comments: dict = None,
) -> io.BytesIO:
    from reportlab.lib.pagesizes import A4
    from reportlab.platypus import (
        SimpleDocTemplate, Spacer, KeepTogether, PageBreak, Table, TableStyle,
    )
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.lib import colors
    from reportlab.platypus import Paragraph
    from reportlab.lib.utils import ImageReader
    from reportlab.platypus import Image as RLImage
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from pitching.plot_courceDist import course_distPlot
    from pitching.plot_courseDetail import course_detailPlot
    from pitching.plot_battedBall import batted_ball_plot
    from batting.calc_stats import calc_batting_stats
    from batting.plot_statsTable import plot_battingStatsTable

    # フォント登録
    _font_name = 'IPAexGothic'
    if _font_name not in pdfmetrics.getRegisteredFontNames():
        fpath = os.path.join( os.path.dirname( __file__ ), 'fonts', 'ipaexg.ttf' )
        if os.path.exists( fpath ):
            try:
                pdfmetrics.registerFont( TTFont( _font_name, fpath ) )
            except Exception:
                _font_name = 'Helvetica'
    font = _font_name

    MARGIN = 14 * mm

    C_HEADER = colors.HexColor( '#1A3A5C' )
    C_ACCENT = colors.HexColor( '#1E3A5F' )
    C_ALT    = colors.HexColor( '#EEF2F5' )

    def _buf_to_rl( buf, width ):
        if buf is None:
            return Spacer( width, width )
        ir = ImageReader( buf )
        iw, ih = ir.getSize()
        buf.seek( 0 )
        return RLImage( buf, width=width, height=width * ih / iw )

    def _para( text, size=9, color=colors.black ):
        style = ParagraphStyle( 'p', fontName=font, fontSize=size,
                                textColor=color, leading=size * 1.5 )
        return Paragraph( text, style )

    def _page_header_rl( batter_name ):
        t = Table(
            [ [ _para( f'打者分析　{batter_name}', size=13, color=colors.white ) ],
              [ _para( f'{selected_team}　{start_date} 〜 {end_date}',
                       size=8, color=colors.HexColor( '#B0C4D8' ) ) ] ],
            colWidths=[ CONTENT_W ], rowHeights=[ 9 * mm, 6 * mm ],
        )
        t.setStyle( TableStyle( [
            ( 'BACKGROUND',    ( 0, 0 ), ( -1, -1 ), C_HEADER ),
            ( 'LEFTPADDING',   ( 0, 0 ), ( -1, -1 ), 4 * mm ),
            ( 'TOPPADDING',    ( 0, 0 ), ( 0,  0  ), 2 * mm ),
            ( 'BOTTOMPADDING', ( 0, 1 ), ( -1, 1  ), 2 * mm ),
            ( 'VALIGN',        ( 0, 0 ), ( -1, -1 ), 'MIDDLE' ),
        ] ) )
        return t

    def _section_heading_rl( text, width=None ):
        p = _para( text, size=9, color=colors.HexColor( '#1A3A5C' ) )
        t = Table( [ [ p ] ], colWidths=[ width or CONTENT_W ], rowHeights=[ 6 * mm ] )
        t.setStyle( TableStyle( [
            ( 'LINEBEFORE',    ( 0, 0 ), ( 0, 0 ), 3, C_ACCENT ),
            ( 'LEFTPADDING',   ( 0, 0 ), ( 0, 0 ), 3 * mm ),
            ( 'VALIGN',        ( 0, 0 ), ( -1, -1 ), 'MIDDLE' ),
            ( 'TOPPADDING',    ( 0, 0 ), ( -1, -1 ), 0 ),
            ( 'BOTTOMPADDING', ( 0, 0 ), ( -1, -1 ), 0 ),
        ] ) )
        return t

    label_style = ParagraphStyle(
        'cl', fontName=font, fontSize=7.5, alignment=1, leading=10,
    )

    from reportlab.lib.pagesizes import landscape
    PAGE_SIZE = landscape( A4 )
    PAGE_W    = PAGE_SIZE[ 0 ]
    CONTENT_W = PAGE_W - 2 * MARGIN
    N_COLS    = 3
    cell_w    = CONTENT_W / N_COLS

    PITCH_TYPE_GROUPS = [
        ( 'ストレート', [ 'ストレート' ] ),
        ( 'スラ系',    [ 'スライダー', 'カット', 'カーブ' ] ),
        ( '落ち系',    [ 'フォーク', 'チェンジ', 'ツーシーム', 'シュート', 'シンカー' ] ),
    ]

    def _pitchtype_stats_img( df_side ):
        """球種タイプ別スタッツ画像（BytesIO）を返す。"""
        rows = []
        for lbl, pt_group in PITCH_TYPE_GROUPS:
            df_g = df_side[ df_side[ '球種' ].isin( pt_group ) ] \
                if '球種' in df_side.columns else df_side.iloc[ 0:0 ]
            rows.append( calc_batting_stats( df_g, None, lbl ) )
        df_pt = pd.DataFrame( rows )
        if stats_cols:
            df_pt = df_pt[ list( stats_cols ) ]
        return _fig_to_image( plot_battingStatsTable( df_pt, highlight_last=False ), dpi=200 )

    lbl_para_style = ParagraphStyle( 'cl', fontName=font, fontSize=7, alignment=1 )

    def _scatter_grid( df_side ):
        """詳細散布 + 打球位置の 2行 × N_COLS列グリッドテーブルを返す。"""
        if '球種' not in df_side.columns:
            return None
        pt_list = df_side[ '球種' ].dropna().value_counts().index.tolist()[ :N_COLS ]
        if not pt_list:
            return None
        pts       = ( pt_list + [ '' ] * N_COLS )[ :N_COLS ]
        grid_rows = [ [ Paragraph( pt, lbl_para_style ) for pt in pts ] ]
        for plot_fn in ( course_detailPlot, batted_ball_plot ):
            row = []
            for pt in pts:
                if pt:
                    buf = plot_fn( df_side, pitch_type=pt )
                    row.append( _buf_to_rl( buf, cell_w ) if buf else Spacer( cell_w, cell_w ) )
                else:
                    row.append( Spacer( cell_w, cell_w ) )
            grid_rows.append( row )
        t = Table( grid_rows, colWidths=[ cell_w ] * N_COLS )
        t.setStyle( TableStyle( [
            ( 'ALIGN',          ( 0, 0 ), ( -1, -1 ), 'CENTER' ),
            ( 'VALIGN',         ( 0, 0 ), ( -1, -1 ), 'MIDDLE' ),
            ( 'TOPPADDING',     ( 0, 0 ), ( -1, -1 ), 1 ),
            ( 'BOTTOMPADDING',  ( 0, 0 ), ( -1, -1 ), 1 ),
            ( 'LEFTPADDING',    ( 0, 0 ), ( -1, -1 ), 1 ),
            ( 'RIGHTPADDING',   ( 0, 0 ), ( -1, -1 ), 1 ),
            ( 'LINEBELOW',      ( 0, 0 ), ( -1, 0  ), 0.4, colors.lightgrey ),
            ( 'ROWBACKGROUNDS', ( 0, 0 ), ( -1, -1 ), [ colors.white, C_ALT, colors.white ] ),
        ] ) )
        return t

    course_w = CONTENT_W / 3

    def _page1_elements( batter, df_b, df_right, df_left ):
        """ページ1: ヘッダー + コメント + スタッツ + コース別打率3列"""
        elems = []
        elems.append( _page_header_rl( batter ) )
        elems.append( Spacer( 1, 4 * mm ) )

        comment = ( comments or {} ).get( batter, '' )
        if comment and comment.strip():
            elems.append( _section_heading_rl( 'コメント' ) )
            elems.append( Spacer( 1, 2 * mm ) )
            elems.append( Paragraph(
                comment.replace( '\n', '<br/>' ),
                ParagraphStyle( 'cm', fontName=font, fontSize=9,
                                textColor=colors.black, leading=13.5 ),
            ) )
            elems.append( Spacer( 1, 4 * mm ) )

        rows = []
        for df_src, side, lbl in [
            ( df_b,        None, '対全投手' ),
            ( df_b,        '右',  '対右投手' ),
            ( df_b,        '左',  '対左投手' ),
            ( df_team_all, None,  '平均'    ),
        ]:
            df_s = df_src if side is None else (
                df_src[ df_src[ '投手左右' ] == side ]
                if '投手左右' in df_src.columns else df_src.iloc[ 0:0 ]
            )
            rows.append( calc_batting_stats( df_s, None, lbl ) )
        df_st = pd.DataFrame( rows )
        if stats_cols:
            df_st = df_st[ list( stats_cols ) ]
        elems.append( _section_heading_rl( 'スタッツ' ) )
        elems.append( Spacer( 1, 2 * mm ) )
        elems.append( _buf_to_rl( _fig_to_image( plot_battingStatsTable( df_st ), dpi=200 ), CONTENT_W ) )
        elems.append( Spacer( 1, 4 * mm ) )

        course_row = []
        for df_side in ( df_b, df_right, df_left ):
            buf_c = _calc_course_chart( df_side )
            course_row.append( _buf_to_rl( buf_c, course_w ) if buf_c else Spacer( course_w, course_w ) )
        course_tbl = Table(
            [ [ Paragraph( lbl, lbl_para_style ) for lbl in ( '全投手', '対右投手', '対左投手' ) ],
              course_row ],
            colWidths=[ course_w ] * 3,
        )
        course_tbl.setStyle( TableStyle( [
            ( 'ALIGN',         ( 0, 0 ), ( -1, -1 ), 'CENTER' ),
            ( 'VALIGN',        ( 0, 0 ), ( -1, -1 ), 'MIDDLE' ),
            ( 'TOPPADDING',    ( 0, 0 ), ( -1, -1 ), 1 ),
            ( 'BOTTOMPADDING', ( 0, 0 ), ( -1, -1 ), 1 ),
            ( 'LEFTPADDING',   ( 0, 0 ), ( -1, -1 ), 1 ),
            ( 'RIGHTPADDING',  ( 0, 0 ), ( -1, -1 ), 1 ),
        ] ) )
        elems.append( course_tbl )
        return elems

    def _side_elements( df_side, side_label ):
        """対右/対左ページ: 球種タイプ別スタッツ + 散布図（ヘッダーなし）"""
        elems = []
        elems.append( _section_heading_rl( side_label ) )
        elems.append( Spacer( 1, 2 * mm ) )
        elems.append( _buf_to_rl( _pitchtype_stats_img( df_side ), CONTENT_W ) )
        elems.append( Spacer( 1, 2 * mm ) )
        grid = _scatter_grid( df_side )
        if grid:
            elems.append( grid )
        return elems

    from pypdf import PdfWriter, PdfReader

    writer = PdfWriter()
    for batter in selected_batters:
        df_b     = df_team[ df_team[ '打者氏名' ] == batter ]
        df_right = df_b[ df_b[ '投手左右' ] == '右' ] \
            if '投手左右' in df_b.columns else df_b.iloc[ 0:0 ]
        df_left  = df_b[ df_b[ '投手左右' ] == '左' ] \
            if '投手左右' in df_b.columns else df_b.iloc[ 0:0 ]

        story_one = []

        # ページ1: ヘッダー + コメント + スタッツ + コース別打率
        story_one.extend( _page1_elements( batter, df_b, df_right, df_left ) )

        # ページ2: 対右投手（ヘッダーなし）
        if not df_right.empty:
            story_one.append( PageBreak() )
            story_one.extend( _side_elements( df_right, '対右投手' ) )

        # ページ3: 対左投手（ヘッダーなし）
        if not df_left.empty:
            story_one.append( PageBreak() )
            story_one.extend( _side_elements( df_left, '対左投手' ) )

        buf_one = io.BytesIO()
        doc_one = SimpleDocTemplate(
            buf_one, pagesize=PAGE_SIZE,
            leftMargin=MARGIN, rightMargin=MARGIN,
            topMargin=MARGIN, bottomMargin=MARGIN,
        )
        doc_one.build( story_one )
        buf_one.seek( 0 )
        reader = PdfReader( buf_one )
        for page in reader.pages:
            writer.add_page( page )
        del buf_one, reader, story_one
        gc.collect()

    buf_out = io.BytesIO()
    writer.write( buf_out )
    buf_out.seek( 0 )
    return buf_out


def _calc_course_chart( df: pd.DataFrame ) -> io.BytesIO | None:
    """コース別打率チャートを PNG BytesIO で返す。データ不足時は None。"""
    from plotnine import (
        ggplot, aes, geom_rect, geom_polygon, annotate, theme, element_blank,
    )

    if not { 'コースX', 'コースYadj' }.issubset( df.columns ):
        return None

    def _band( v ):
        v = np.asarray( v, dtype=float )
        out = np.full( v.shape, -1, dtype=np.int8 )
        m = np.isfinite( v )
        out[ m ] = np.select(
            [ v[m] <= 53, v[m] <= 105.7, v[m] <= 131.5, v[m] <= 158.7, v[m] <= 211 ],
            [ 0, 1, 2, 3, 4 ], default=5,
        )
        return out

    x_num = pd.to_numeric( df[ 'コースX' ],    errors='coerce' )
    y_num = pd.to_numeric( df[ 'コースYadj' ], errors='coerce' )
    finite = np.isfinite( x_num.to_numpy( dtype=float ) ) & np.isfinite( y_num.to_numpy( dtype=float ) )
    df = df.loc[ finite ].copy()
    if df.empty:
        return None

    x = x_num.to_numpy( dtype=float )[ finite ]
    y = y_num.to_numpy( dtype=float )[ finite ]
    df[ 'コースX' ] = x
    df[ 'コースYadj' ] = y

    c     = np.full( len( df ), np.nan )
    valid = np.ones( len( df ), dtype=bool )
    xn    = _band( x )
    yn    = _band( y )

    ic = ( xn >= 1 ) & ( xn <= 3 )
    c[ ic & ( yn == 4 ) ]                          = xn[ ic & ( yn == 4 ) ]
    c[ ic & ( ( yn == 2 ) | ( yn == 3 ) ) ]        = 3 + xn[ ic & ( ( yn == 2 ) | ( yn == 3 ) ) ]
    c[ ic & ( yn == 1 ) ]                          = 6 + xn[ ic & ( yn == 1 ) ]

    rem = np.isnan( c )
    c[ rem & ( ( ( xn == 0 ) & ( yn >= 3 ) ) | ( ( yn == 5 ) & ( xn <= 2 ) ) ) ] = 10
    rem = np.isnan( c )
    c[ rem & ( ( ( xn == 0 ) & ( yn <= 2 ) ) | ( ( yn == 0 ) & ( xn <= 2 ) ) ) ] = 12
    rem = np.isnan( c )
    c[ rem & ( ( ( xn == 4 ) & ( yn >= 3 ) ) | ( ( yn == 5 ) & ( xn >= 2 ) ) ) ] = 11
    rem = np.isnan( c )
    c[ rem & ( ( ( xn == 4 ) & ( yn <= 2 ) ) | ( ( yn == 0 ) & ( xn >= 2 ) ) ) ] = 13
    rem = np.isnan( c )
    c[ rem & ( xn == 5 ) & ( y > 131.5  ) ] = 11
    rem = np.isnan( c )
    c[ rem & ( xn == 5 ) & ( y <= 131.5 ) ] = 13
    df[ 'cource_no' ] = c

    cd = {}
    for cno in range( 1, 14 ):
        dc = df[ df[ 'cource_no' ] == cno ]
        n_plate = len( dc[ dc[ '打席の継続' ] == '打席完了' ] )
        n_ab  = n_plate - len( dc[ dc[ '打撃結果' ].isin( [ '犠打', '犠飛', '四球', '死球' ] ) ] )
        n_hit = len( dc[ dc[ '打撃結果' ].isin( [ '単打', '二塁打', '三塁打', '本塁打' ] ) ] )
        if n_ab > 0:
            r   = n_hit / n_ab
            s   = f'{r:.3f}'
            avg = s[ 1: ] if s.startswith( '0.' ) else s
            col = '#CC2222' if r >= 0.3 else ( '#3333CC' if r <= 0.22 else '#AAAAAA' )
        else:
            avg, col = '--', '#AAAAAA'
        cd[ cno ] = { 'avg': avg, 'lbl': f'{ n_ab }-{ n_hit }', 'col': col }

    def _rects():
        return [
            geom_rect( aes( xmin=0,  xmax=5,  ymin=5, ymax=10 ), fill=cd[10]['col'], color='black', size=1 ),
            geom_rect( aes( xmin=5,  xmax=10, ymin=5, ymax=10 ), fill=cd[11]['col'], color='black', size=1 ),
            geom_rect( aes( xmin=0,  xmax=5,  ymin=0, ymax=5  ), fill=cd[12]['col'], color='black', size=1 ),
            geom_rect( aes( xmin=5,  xmax=10, ymin=0, ymax=5  ), fill=cd[13]['col'], color='black', size=1 ),
            geom_rect( aes( xmin=2,  xmax=4,  ymin=6, ymax=8  ), fill=cd[ 1]['col'], color='black', size=1 ),
            geom_rect( aes( xmin=4,  xmax=6,  ymin=6, ymax=8  ), fill=cd[ 2]['col'], color='black', size=1 ),
            geom_rect( aes( xmin=6,  xmax=8,  ymin=6, ymax=8  ), fill=cd[ 3]['col'], color='black', size=1 ),
            geom_rect( aes( xmin=2,  xmax=4,  ymin=4, ymax=6  ), fill=cd[ 4]['col'], color='black', size=1 ),
            geom_rect( aes( xmin=4,  xmax=6,  ymin=4, ymax=6  ), fill=cd[ 5]['col'], color='black', size=1 ),
            geom_rect( aes( xmin=6,  xmax=8,  ymin=4, ymax=6  ), fill=cd[ 6]['col'], color='black', size=1 ),
            geom_rect( aes( xmin=2,  xmax=4,  ymin=2, ymax=4  ), fill=cd[ 7]['col'], color='black', size=1 ),
            geom_rect( aes( xmin=4,  xmax=6,  ymin=2, ymax=4  ), fill=cd[ 8]['col'], color='black', size=1 ),
            geom_rect( aes( xmin=6,  xmax=8,  ymin=2, ymax=4  ), fill=cd[ 9]['col'], color='black', size=1 ),
        ]

    _zone = {
        1: (3,7), 2: (5,7), 3: (7,7),
        4: (3,5), 5: (5,5), 6: (7,5),
        7: (3,3), 8: (5,3), 9: (7,3),
    }
    _corner = { 10: (1,9.6), 11: (9,9.6), 12: (1,1.0), 13: (9,1.0) }

    p = ggplot()
    for layer in _rects():
        p = p + layer
    for cno, ( cx, cy ) in _zone.items():
        p = ( p
              + annotate( 'text', x=cx, y=cy,       label=cd[cno]['avg'], size=40, fontweight='bold', color='white' )
              + annotate( 'text', x=cx, y=cy - 0.6,  label=cd[cno]['lbl'], size=25, fontweight='bold', color='white' ) )
    for cno, ( cx, cy ) in _corner.items():
        p = ( p
              + annotate( 'text', x=cx, y=cy,       label=cd[cno]['avg'], size=40, fontweight='bold', color='white' )
              + annotate( 'text', x=cx, y=cy - 0.6,  label=cd[cno]['lbl'], size=25, fontweight='bold', color='white' ) )
    p = ( p
          + geom_polygon( aes( x=[4,6,6,5,4,4], y=[0.8,0.8,0.4,0,0.4,0.8] ), fill='white', color='black', size=1 )
          + theme(
              axis_text=element_blank(), axis_ticks=element_blank(),
              axis_title=element_blank(), axis_line=element_blank(),
              panel_grid=element_blank(), panel_border=element_blank(),
              plot_background=element_blank(), panel_background=element_blank(),
              legend_position='none', figure_size=( 5, 5 ),
          ) )

    mpl_fig = p.draw()
    buf = io.BytesIO()
    mpl_fig.savefig( buf, format='png', dpi=150, bbox_inches='tight' )
    plt.close( mpl_fig )
    buf.seek( 0 )
    return buf


def _go_start():
    st.session_state.page_ctg = 'start'


def show() -> None:
    col_back, col_reload = st.columns( [ 6, 1 ] )
    with col_back:
        st.button( '← スタートに戻る', on_click=_go_start )
    with col_reload:
        if st.button( 'データを更新', key='bam_reload' ):
            clear_team_plays_cache()
            st.rerun()

    team_id = st.session_state.get( 'logged_in_team_id' )
    df_pre  = get_cached_team_plays_df( team_id )

    if df_pre.empty:
        st.warning( 'データがありません。先に試合データを入力してください。' )
        return

    # ── 期間・チーム選択（軽量な前処理済みDFから）────────────────
    valid_dates = df_pre[ '_date' ].dropna()
    date_min = valid_dates.min().date() if not valid_dates.empty else datetime.date.today()
    date_max = valid_dates.max().date() if not valid_dates.empty else datetime.date.today()

    col_start, col_end, col_team = st.columns( 3 )
    with col_start:
        start_date = st.date_input( '開始日', value=date_min, key='bam_start' )
    with col_end:
        end_date = st.date_input( '終了日', value=date_max, key='bam_end' )

    # チームリストは全期間から
    teams = sorted( df_pre[ '攻撃チーム' ].dropna().unique().tolist() )
    if not teams:
        st.warning( '打者データが見つかりません。' )
        return

    my_team  = st.session_state.get( 'logged_in_team_name', '' )
    team_idx = teams.index( my_team ) if my_team in teams else 0

    with col_team:
        selected_team = st.selectbox( '攻撃チーム', teams, index=team_idx, key='bam_team' )

    # ── セクション切り替え（radio: 選択中のみ重い処理を実行）────────
    section = st.radio(
        'セクション',
        [ 'スタッツ一覧', 'チーム作戦分析', 'プレイヤー分析', '出力' ],
        horizontal=True, key='bam_section',
    )
    st.divider()

    # ── スタッツ一覧 ─────────────────────────────────────────
    if section == 'スタッツ一覧':
        stat_view = st.radio(
            '投手区分', [ '全体', '対右投手', '対左投手' ],
            horizontal=True, key='bam_stats_side',
        )
        _side_map = { '全体': None, '対右投手': '右', '対左投手': '左' }
        _side = _side_map[ stat_view ]
        raw = _cached_stats_list_image( team_id, start_date, end_date, selected_team, _side )
        if raw:
            st.image( raw, use_container_width=True )
        else:
            st.info( 'データがありません。' )
        st.markdown( '---' )
        st.markdown( '**PDF**' )
        if st.button( 'PDF 生成', key='bam_gen_pdf' ):
            df_team, _ = _apply_filters( df_pre, start_date, end_date, selected_team )
            with st.spinner( 'PDF 生成中...' ):
                _pdf = _generate_stats_pdf( df_team, selected_team, start_date, end_date )
            st.download_button(
                label     = 'PDF ダウンロード',
                data      = _pdf.getvalue(),
                file_name = f'batting_stats_{ selected_team }_{ start_date }_{ end_date }.pdf',
                mime      = 'application/pdf',
                key       = 'bam_dl_pdf',
            )

    # ── チーム作戦分析 ────────────────────────────────────────
    elif section == 'チーム作戦分析':
        st.markdown( '## 攻撃分析' )
        raw_fig = _cached_strategy_figure( team_id, start_date, end_date, selected_team )
        st.image( raw_fig, use_container_width=True )

        # 盗塁・バント分析（軽量なため都度計算）
        df_team, _ = _apply_filters( df_pre, start_date, end_date, selected_team )
        _show_steal_section( df_team )
        _show_bunt_section( df_team )

        st.markdown( '---' )
        st.markdown( '**PDF**' )
        if st.button( 'PDF 生成', key='bam_strategy_gen_pdf' ):
            df_team, _ = _apply_filters( df_pre, start_date, end_date, selected_team )
            df_filtered = df_pre[
                ( df_pre[ '_date' ].dt.date >= start_date ) &
                ( df_pre[ '_date' ].dt.date <= end_date   )
            ]
            with st.spinner( 'PDF 生成中...' ):
                _pdf = _generate_strategy_pdf(
                    df_filtered, df_team, selected_team, start_date, end_date,
                )
            st.download_button(
                label     = 'PDF ダウンロード',
                data      = _pdf.getvalue(),
                file_name = f'strategy_{ selected_team }_{ start_date }_{ end_date }.pdf',
                mime      = 'application/pdf',
                key       = 'bam_strategy_dl_pdf',
            )

    # ── プレイヤー分析 ────────────────────────────────────────
    elif section == 'プレイヤー分析':
        df_team, df_team_all = _apply_filters( df_pre, start_date, end_date, selected_team )
        batters_all = sorted( df_team[ '打者氏名' ].dropna().unique().tolist() )
        if not batters_all:
            st.info( 'データがありません。' )
        else:
            selected_batters = st.multiselect(
                '打者を選択', batters_all, default=batters_all[ :1 ],
                key='bam_player_select',
            )
            if not selected_batters:
                st.info( '打者を選択してください。' )
            else:
                from batting.calc_stats import calc_batting_stats as _cbs_ref
                _STATS_COLS = tuple( _cbs_ref( df_team.iloc[ 0:0 ], None, '' ).keys() )

                def _render_scatter_by_side( batter: str, side_str ):
                    """詳細散布 + 打球位置をキャッシュ経由で球種別5列表示"""
                    # 球種リストはキャッシュ済み df から取得
                    df_b = df_team[ df_team[ '打者氏名' ] == batter ]
                    df_s = df_b if side_str is None else (
                        df_b[ df_b[ '投手左右' ] == side_str ]
                        if '投手左右' in df_b.columns else df_b.iloc[ 0:0 ]
                    )
                    if '球種' not in df_s.columns:
                        return
                    pt_list = df_s[ '球種' ].dropna().value_counts().index.tolist()[ :5 ]
                    if not pt_list:
                        st.info( 'データ不足' )
                        return
                    cols_sc = st.columns( 5 )
                    for j, pt in enumerate( pt_list ):
                        raw_d = _cached_detail_plot(
                            team_id, start_date, end_date, selected_team, batter, side_str, pt )
                        raw_b = _cached_batted_plot(
                            team_id, start_date, end_date, selected_team, batter, side_str, pt )
                        with cols_sc[ j ]:
                            st.caption( pt )
                            if raw_d:
                                st.image( raw_d, use_container_width=True )
                            if raw_b:
                                st.image( raw_b, use_container_width=True )

                # コメントを一括取得（N+1クエリ防止）
                _cached_comments = batter_comment_repo.get_all_comments( team_id )

                _view_options = selected_batters + [ 'PDF出力' ]
                _selected_view = st.radio(
                    '表示', _view_options, horizontal=True, key='bam_player_view'
                )

                if _selected_view != 'PDF出力':
                    batter = _selected_view
                    # ── コメント ────────────────────────────────
                    _ck_edit = f'ba_comment_editing_{batter}'
                    if _ck_edit not in st.session_state:
                        st.session_state[ _ck_edit ] = False
                    saved_comment = _cached_comments.get( batter, '' )
                    if st.session_state[ _ck_edit ]:
                        new_text = st.text_area(
                            'コメント', value=saved_comment,
                            height=150, key=f'ba_comment_input_{batter}',
                        )
                        c_save, c_cancel = st.columns( [ 1, 1 ] )
                        with c_save:
                            if st.button( '保存', key=f'ba_comment_save_{batter}' ):
                                batter_comment_repo.upsert_comment( team_id, batter, new_text )
                                st.session_state[ _ck_edit ] = False
                                _cached_comments[ batter ] = new_text
                                st.rerun()
                        with c_cancel:
                            if st.button( 'キャンセル', key=f'ba_comment_cancel_{batter}' ):
                                st.session_state[ _ck_edit ] = False
                                st.rerun()
                    else:
                        if saved_comment:
                            st.text( saved_comment )
                        else:
                            st.info( 'コメントはまだ登録されていません。' )
                        if st.button( 'Edit', key=f'ba_comment_edit_{batter}' ):
                            st.session_state[ _ck_edit ] = True
                            st.rerun()

                    # ── スタッツテーブル（キャッシュ・プリミティブキー）──
                    st.image(
                        _cached_stats_table(
                            team_id, start_date, end_date, selected_team, batter, _STATS_COLS
                        ),
                        use_container_width=True,
                    )

                    # ── コース別打率（全/右/左）横3列 ──────────────
                    col_all, col_r, col_l = st.columns( 3 )
                    for col, label, side in [
                        ( col_all, '全投手',   None ),
                        ( col_r,   '対右投手', '右'  ),
                        ( col_l,   '対左投手', '左'  ),
                    ]:
                        with col:
                            st.caption( label )
                            raw_c = _cached_course_chart(
                                team_id, start_date, end_date, selected_team, batter, side )
                            if raw_c:
                                st.image( raw_c, use_container_width=True )
                            else:
                                st.info( 'データ不足' )

                    # ── 対右投手 球種タイプ別スタッツ + 散布図 ──────────
                    st.markdown( '#### 対右投手' )
                    st.image(
                        _cached_pitchtype_stats(
                            team_id, start_date, end_date, selected_team, batter, '右', _STATS_COLS
                        ),
                        use_container_width=True,
                    )
                    _render_scatter_by_side( batter, '右' )

                    # ── 対左投手 球種タイプ別スタッツ + 散布図 ──────────
                    st.markdown( '#### 対左投手' )
                    st.image(
                        _cached_pitchtype_stats(
                            team_id, start_date, end_date, selected_team, batter, '左', _STATS_COLS
                        ),
                        use_container_width=True,
                    )
                    _render_scatter_by_side( batter, '左' )

                else:
                    st.markdown( '**PDF（選択選手全員）**' )
                    if st.button( 'PDF 生成', key='bam_player_gen_pdf' ):
                        _all_comments = batter_comment_repo.get_all_comments( team_id )
                        _comments = { b: _all_comments.get( b, '' ) for b in selected_batters }
                        with st.spinner( 'PDF 生成中...' ):
                            _pdf = _generate_player_pdf(
                                selected_batters, df_team, df_team_all,
                                selected_team, start_date, end_date, _STATS_COLS,
                                comments=_comments,
                            )
                        st.download_button(
                            label     = 'PDF ダウンロード',
                            data      = _pdf.getvalue(),
                            file_name = f'player_analysis_{selected_team}_{start_date}_{end_date}.pdf',
                            mime      = 'application/pdf',
                            key       = 'bam_player_dl_pdf',
                        )

    # ── 出力 ─────────────────────────────────────────────────
    else:
        df_team, df_team_all = _apply_filters( df_pre, start_date, end_date, selected_team )
        df_filtered = df_pre[
            ( df_pre[ '_date' ].dt.date >= start_date ) &
            ( df_pre[ '_date' ].dt.date <= end_date   )
        ]
        st.markdown( '### 統合出力（スタッツ一覧 + チーム作戦分析 + プレイヤー分析）' )

        batters_for_export = sorted(
            df_team[ '打者氏名' ].dropna().unique().tolist()
        )
        selected_export_batters = st.multiselect(
            '出力する打者を選択',
            batters_for_export,
            default=batters_for_export[ :1 ] if batters_for_export else [],
            key='bam_export_batter_select',
        )

        from batting.calc_stats import calc_batting_stats as _cbs_export
        _EXPORT_STATS_COLS = tuple( _cbs_export( df_team.iloc[ 0:0 ], None, '' ).keys() )

        from generate_combined_output import generate_combined_pdf, generate_combined_pptx

        col_pdf, col_pptx = st.columns( 2 )

        with col_pdf:
            st.markdown( '**PDF**' )
            if st.button( 'PDF 生成', key='bam_export_gen_pdf' ):
                with st.spinner( 'PDF 生成中...' ):
                    _pdf = generate_combined_pdf(
                        df_filtered, df_team, df_team_all,
                        selected_team, start_date, end_date,
                        selected_export_batters, _EXPORT_STATS_COLS, team_id,
                    )
                st.download_button(
                    label     = 'PDF ダウンロード',
                    data      = _pdf.getvalue(),
                    file_name = f'combined_{selected_team}_{start_date}_{end_date}.pdf',
                    mime      = 'application/pdf',
                    key       = 'bam_export_dl_pdf',
                )

        with col_pptx:
            st.markdown( '**PPTX**' )
            if st.button( 'PPTX 生成', key='bam_export_gen_pptx' ):
                with st.spinner( 'PPTX 生成中...' ):
                    try:
                        _pptx = generate_combined_pptx(
                            df_filtered, df_team, df_team_all,
                            selected_team, start_date, end_date,
                            selected_export_batters, _EXPORT_STATS_COLS, team_id,
                        )
                        st.download_button(
                            label     = 'PPTX ダウンロード',
                            data      = _pptx.getvalue(),
                            file_name = f'combined_{selected_team}_{start_date}_{end_date}.pptx',
                            mime      = 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
                            key       = 'bam_export_dl_pptx',
                        )
                    except ImportError as e:
                        st.error(
                            f'PPTX生成に必要なライブラリが不足しています: {e}\n\n'
                            '`pip install pymupdf pypdf python-pptx` を実行してください。'
                        )
