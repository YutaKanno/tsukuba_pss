"""スコア表（スコアブック）ページ"""
import io
import json
import os

import matplotlib
matplotlib.use( 'Agg' )
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.patches import Rectangle
import pandas as pd
import streamlit as st

from db import game_repo


_HIT_RESULTS   = frozenset( { '単打', '二塁打', '三塁打', '本塁打' } )
_K_RESULTS     = frozenset( { '見三振', '空三振', '振逃' } )
_BB_RESULTS    = frozenset( { '四球', '死球' } )
_ERROR_RESULTS = frozenset( { 'エラー' } )

_HEADER_COLOR = '#1A3A5C'
_ROW_ALT      = '#EEF2F5'


def _register_fonts() -> None:
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


def _go_start() -> None:
    st.session_state.page_ctg = 'start'


@st.cache_data( ttl = 60 )
def _load_plays( game_id: int, team_id: int ) -> pd.DataFrame:
    return game_repo.get_plays_df_for_game( game_id, owner_team_id = team_id )


def _display_innings( df: pd.DataFrame ) -> list:
    """1〜9回を必ず含み、延長がある場合はそれ以降も含むイニングリストを返す。"""
    played  = df[ '回' ].dropna().astype( int ).unique().tolist()
    max_inn = max( max( played ) if played else 0, 9 )
    return list( range( 1, max_inn + 1 ) )


def _inning_runs( df: pd.DataFrame ) -> tuple:
    """Returns (top_runs, bot_runs, top_total, bot_total)."""
    innings  = sorted( df[ '回' ].dropna().astype( int ).unique().tolist() )
    top_runs: dict = {}
    bot_runs: dict = {}
    prev_top = 0
    prev_bot = 0

    for inn in innings:
        df_inn   = df[ df[ '回' ] == inn ]
        top_half = df_inn[ df_inn[ '表裏' ] == '表' ]
        bot_half = df_inn[ df_inn[ '表裏' ] == '裏' ]

        cur_top = prev_top
        if not top_half.empty:
            vals = top_half[ '先攻得点' ].dropna()
            if not vals.empty:
                cur_top = int( vals.max() )

        cur_bot = prev_bot
        if not bot_half.empty:
            vals = bot_half[ '後攻得点' ].dropna()
            if not vals.empty:
                cur_bot = int( vals.max() )

        top_runs[ inn ] = cur_top - prev_top
        bot_runs[ inn ] = cur_bot - prev_bot
        prev_top = cur_top
        prev_bot = cur_bot

    return top_runs, bot_runs, prev_top, prev_bot


def _side_stats( df: pd.DataFrame, side: str ) -> dict:
    """H / E / K / B の合計（batting side 視点）。"""
    df_ab = df[
        ( df[ '表裏' ]       == side       ) &
        ( df[ '打席の継続' ] == '打席完了' ) &
        ( df[ '打席結果' ].notna()         ) &
        ( df[ '打席結果' ]   != '0'        ) &
        ( df[ '打席結果' ]   != ''         )
    ]
    results = df_ab[ '打席結果' ].tolist()
    return {
        'H': sum( 1 for r in results if r in _HIT_RESULTS   ),
        'E': sum( 1 for r in results if r in _ERROR_RESULTS ),
        'K': sum( 1 for r in results if r in _K_RESULTS     ),
        'B': sum( 1 for r in results if r in _BB_RESULTS    ),
    }


def _score_df( df: pd.DataFrame, top_team: str, bot_team: str,
               innings: list ) -> pd.DataFrame:
    """スコアテーブル（1〜9回固定列 + 計 + H/E/K/B）。"""
    top_runs, bot_runs, top_total, bot_total = _inning_runs( df )
    top_stats = _side_stats( df, '表' )
    bot_stats = _side_stats( df, '裏' )

    records = []
    for label, runs_dict, total, stats in [
        ( f'{ top_team }（先攻）', top_runs, top_total, top_stats ),
        ( f'{ bot_team }（後攻）', bot_runs, bot_total, bot_stats ),
    ]:
        row: dict = { 'チーム': label }
        for inn in innings:
            row[ str( inn ) ] = runs_dict.get( inn, '' )
        row[ '計' ] = total
        row[ 'H'  ] = stats[ 'H' ]
        row[ 'E'  ] = stats[ 'E' ]
        row[ 'K'  ] = stats[ 'K' ]
        row[ 'B'  ] = stats[ 'B' ]
        records.append( row )

    return pd.DataFrame( records ).set_index( 'チーム' )


def _safe_position( poses_val, order_int: int ) -> str:
    """poses 配列（リスト or JSON文字列）から打順のポジションを安全に取得。"""
    if poses_val is None:
        return ''
    if isinstance( poses_val, str ):
        try:
            poses_val = json.loads( poses_val )
        except Exception:
            return ''
    if not isinstance( poses_val, list ):
        return ''
    idx = order_int - 1
    if 0 <= idx < len( poses_val ):
        pos = poses_val[ idx ]
        return str( pos ) if pos is not None else ''
    return ''


def _scorebook_df( df: pd.DataFrame, side: str, innings: list ) -> pd.DataFrame:
    """スコアブックグリッド。

    - 代打・選手交代 → 選手ごとに独立した行（元選手の直下に追加）
    - 守備位置 → 試合中に変わった場合は「P → LF」形式
    - 打者一巡（同一イニングに同打順が複数回）→ 「単打 / 三振」と / 区切り
    """
    poses_col = 'top_poses' if side == '表' else 'bottom_poses'

    df_ab = df[
        ( df[ '表裏' ]       == side        ) &
        ( df[ '打席の継続' ] == '打席完了'  ) &
        ( df[ '打席結果' ].notna()          ) &
        ( df[ '打席結果' ]   != '0'         ) &
        ( df[ '打席結果' ]   != ''          )
    ].copy().sort_values( 'プレイの番号' )

    if df_ab.empty:
        return pd.DataFrame()

    # 全打席（未完了含む）: 守備位置の変化追跡に使う
    df_side_all = df[ df[ '表裏' ] == side ].sort_values( 'プレイの番号' )

    # (打順, 選手名) の初回出現順リスト
    seen: dict = {}
    entry_keys: list = []
    for _, row in df_ab.iterrows():
        o = row[ '打順' ]
        n = str( row[ '打者氏名' ] or '' )
        if pd.notna( o ):
            k = ( int( o ), n )
            if k not in seen:
                seen[ k ] = True
                entry_keys.append( k )

    if not entry_keys:
        return pd.DataFrame()

    records = []
    for order, name in entry_keys:
        # この選手の完了打席
        player_ab = df_ab[
            ( df_ab[ '打順' ] == order ) & ( df_ab[ '打者氏名' ] == name )
        ]

        # 守備位置の変化追跡（この選手が打者として立っている全プレイ）
        player_plays = df_side_all[ df_side_all[ '打者氏名' ] == name ]
        positions: list = []
        for _, r in player_plays.iterrows():
            pos = _safe_position( r[ poses_col ], order )
            if pos and ( not positions or positions[ -1 ] != pos ):
                positions.append( pos )
        pos_display = ' → '.join( positions ) if positions else ''

        row_data: dict = {
            '打順'   : order,
            '選手名' : name,
            '守備位置': pos_display,
        }
        for inn in innings:
            # 同一イニングに複数打席（打者一巡）は「/」で列挙
            results = player_ab[ player_ab[ '回' ] == inn ][ '打席結果' ].tolist()
            row_data[ str( inn ) ] = ' / '.join( str( r ) for r in results ) if results else ''
        records.append( row_data )

    return pd.DataFrame( records ).set_index( '打順' )


def _pitcher_df( df: pd.DataFrame, batting_side: str ) -> pd.DataFrame:
    """投手スコアテーブル。

    batting_side='表': 先攻打席 → 後攻投手のスコア
    batting_side='裏': 後攻打席 → 先攻投手のスコア
    """
    df_s  = df[ df[ '表裏' ] == batting_side ]
    df_ab = df_s[
        ( df_s[ '打席の継続' ] == '打席完了' ) &
        ( df_s[ '打席結果' ].notna()         ) &
        ( df_s[ '打席結果' ]  != '0'         ) &
        ( df_s[ '打席結果' ]  != ''          )
    ]

    if df_ab.empty:
        return pd.DataFrame()

    pitcher_order = df_ab.drop_duplicates( '投手氏名' )[ '投手氏名' ].tolist()

    records = []
    for pitcher in pitcher_order:
        grp     = df_ab[ df_ab[ '投手氏名' ] == pitcher ]
        results = grp[ '打席結果' ].tolist()

        total_pitches = df_s[
            ( df_s[ '投手氏名'     ] == pitcher ) &
            ( df_s[ 'プレイの種類' ] == '投球'  )
        ].shape[ 0 ]

        records.append( {
            '投手'  : pitcher,
            '投球数': total_pitches,
            '打者数': len( grp ),
            'H'     : sum( 1 for r in results if r in _HIT_RESULTS ),
            'K'     : sum( 1 for r in results if r in _K_RESULTS   ),
            'B'     : sum( 1 for r in results if r in _BB_RESULTS  ),
        } )

    return pd.DataFrame( records ).set_index( '投手' )


# ── PDF 生成 ──────────────────────────────────────────────────────

_PDF_FONTSIZE = 8
_ROW_H_IN     = 0.28   # 1データ行あたりの高さ（インチ）


def _draw_table_on_ax( ax: plt.Axes, df: pd.DataFrame, title: str ) -> None:
    """DataFrame を1つの Axes にスタイル付きテーブルとして描画する。"""
    ax.axis( 'off' )
    if df.empty:
        ax.text( 0.5, 0.5, 'データなし', ha = 'center', va = 'center',
                 fontsize = _PDF_FONTSIZE, transform = ax.transAxes )
        return

    ax.set_title( title, fontsize = _PDF_FONTSIZE + 1, fontweight = 'bold',
                  loc = 'left', pad = 3 )

    n_cols    = len( df.columns )
    all_text  = [ df.columns.tolist() ] + df.fillna( '' ).astype( str ).values.tolist()
    row_labels = [ '' ] + [ str( i ) for i in df.index ]
    total_row  = len( all_text )

    table = ax.table(
        cellText  = all_text,
        rowLabels = row_labels,
        cellLoc   = 'center',
        bbox      = [ 0, 0, 1, 1 ],
    )
    table.set_zorder( 2 )
    table.auto_set_font_size( False )
    table.set_fontsize( _PDF_FONTSIZE )
    table.auto_set_column_width( list( range( n_cols ) ) )
    table.scale( 1, 1.2 )

    for col in range( n_cols ):
        for r in range( total_row ):
            if ( r, col ) in table._cells:
                w = table._cells[ r, col ].get_width()
                table._cells[ r, col ].set_width( w * 1.5 )

    ax.figure.canvas.draw()

    def _patch( row_idx, col_s, col_e, color ):
        first  = table[ row_idx, col_s ]
        last   = table[ row_idx, col_e ]
        x0, y0 = first.get_xy()
        x1     = last.get_xy()[ 0 ] + last.get_width()
        h      = first.get_height()
        ax.add_patch( Rectangle( ( x0, y0 ), x1 - x0, h,
                                  facecolor = color, edgecolor = 'none',
                                  transform = ax.transAxes, zorder = 1 ) )

    _patch( 0, 0, n_cols - 1, _HEADER_COLOR )
    for r in range( 1, total_row ):
        _patch( r, 0, n_cols - 1, _ROW_ALT if r % 2 == 0 else 'white' )
    for col in range( n_cols ):
        if ( 0, col ) in table._cells:
            table._cells[ 0, col ].set_text_props( color = 'white', fontweight = 'bold' )


def generate_score_card_pdf(
    df: pd.DataFrame,
    top_team: str,
    bot_team: str,
    game_date: str,
    game_kind: str,
    innings: list,
) -> io.BytesIO:
    """全セクションを1ページにまとめた PDF を生成して BytesIO で返す。"""
    score_data = _score_df( df, top_team, bot_team, innings )
    top_sb     = _scorebook_df( df, '表', innings )
    bot_sb     = _scorebook_df( df, '裏', innings )
    p_top      = _pitcher_df( df, '裏' )
    p_bot      = _pitcher_df( df, '表' )

    # 各セクションの行数（ヘッダー1行 + データ行）
    def _n( d ):
        return len( d ) + 1 if not d.empty else 1

    score_rows  = _n( score_data )
    top_sb_rows = _n( top_sb )
    bot_sb_rows = _n( bot_sb )
    pitch_rows  = max( _n( p_top ), _n( p_bot ) )

    # セクション高さ（インチ）: データ行数 × 行高 + タイトル余白
    _sec_h = lambda r: r * _ROW_H_IN + 0.35

    h_score  = _sec_h( score_rows  )
    h_top    = _sec_h( top_sb_rows )
    h_bot    = _sec_h( bot_sb_rows )
    h_pitch  = _sec_h( pitch_rows  )
    h_title  = 0.5   # 全体タイトル
    h_pad    = 0.3   # 余白合計

    fig_h = h_title + h_score + h_top + h_bot + h_pitch + h_pad
    fig_w = max( 14.0, ( len( innings ) + 7 ) * 0.75 )

    height_ratios = [ h_score, h_top, h_bot, h_pitch ]

    # 先攻/後攻スコアブックと投手スコアを行方向に配置
    # 投手スコアだけ 2列
    fig = plt.figure( figsize = ( fig_w, fig_h ), dpi = 150 )
    fig.suptitle(
        f'{ game_date }  { game_kind }  { top_team } vs { bot_team }',
        fontsize = 11, fontweight = 'bold',
    )

    from matplotlib.gridspec import GridSpec
    gs = GridSpec(
        4, 2,
        figure       = fig,
        height_ratios = height_ratios,
        hspace       = 0.55,
        wspace       = 0.25,
    )

    # スコア（2列連結）
    ax_score = fig.add_subplot( gs[ 0, : ] )
    _draw_table_on_ax( ax_score, score_data, 'スコア' )

    # 先攻スコアブック（2列連結）
    ax_top = fig.add_subplot( gs[ 1, : ] )
    _draw_table_on_ax( ax_top, top_sb, f'先攻スコアブック：{ top_team }' )

    # 後攻スコアブック（2列連結）
    ax_bot = fig.add_subplot( gs[ 2, : ] )
    _draw_table_on_ax( ax_bot, bot_sb, f'後攻スコアブック：{ bot_team }' )

    # 投手スコア（左右 2列）
    ax_p1 = fig.add_subplot( gs[ 3, 0 ] )
    ax_p2 = fig.add_subplot( gs[ 3, 1 ] )
    _draw_table_on_ax( ax_p1, p_top, f'{ top_team } 投手' )
    _draw_table_on_ax( ax_p2, p_bot, f'{ bot_team } 投手' )

    buf = io.BytesIO()
    fig.savefig( buf, format = 'pdf', bbox_inches = 'tight' )
    plt.close( fig )
    buf.seek( 0 )
    return buf


# ── Streamlit ページ ───────────────────────────────────────────────

def show() -> None:
    st.button( '← スタートに戻る', on_click = _go_start )
    st.header( 'スコア表' )

    team_id = st.session_state.get( 'logged_in_team_id' )
    games   = game_repo.list_games( team_id = team_id, limit = 200 )

    if not games:
        st.warning( '試合データがありません。先に試合データを入力してください。' )
        return

    all_teams = sorted( { g[ 4 ] for g in games } | { g[ 5 ] for g in games } )

    col_team, col_game = st.columns( [ 2, 5 ] )
    with col_team:
        selected_team = st.selectbox( 'チーム', all_teams, key = 'sc_team' )

    filtered = [ g for g in games if g[ 4 ] == selected_team or g[ 5 ] == selected_team ]
    if not filtered:
        st.warning( f'{ selected_team } の試合データがありません。' )
        return

    game_labels = [
        f"{ g[ 1 ] }　{ g[ 3 ] or '' }　{ g[ 4 ] } vs { g[ 5 ] }"
        for g in filtered
    ]
    with col_game:
        game_idx = st.selectbox(
            '試合', range( len( game_labels ) ),
            format_func = lambda i: game_labels[ i ],
            key = 'sc_game',
        )

    sel       = filtered[ game_idx ]
    game_id   = sel[ 0 ]
    top_team  = sel[ 4 ]
    bot_team  = sel[ 5 ]
    game_date = sel[ 1 ]
    game_kind = sel[ 3 ] or ''

    df = _load_plays( game_id, team_id )
    if df.empty:
        st.info( 'この試合にはまだデータが入力されていません。' )
        return

    st.caption( f'{ game_date }　{ game_kind }　{ top_team } vs { bot_team }' )
    innings = _display_innings( df )

    # ── スコア ─────────────────────────────────────────────────────
    st.subheader( 'スコア' )
    st.dataframe( _score_df( df, top_team, bot_team, innings ),
                  use_container_width = True )

    # ── スコアブック ───────────────────────────────────────────────
    col_top, col_bot = st.columns( 2 )

    with col_top:
        st.subheader( f'先攻：{ top_team }' )
        top_sb = _scorebook_df( df, '表', innings )
        if top_sb.empty:
            st.info( '先攻の打席データがありません。' )
        else:
            st.dataframe( top_sb, use_container_width = True )

    with col_bot:
        st.subheader( f'後攻：{ bot_team }' )
        bot_sb = _scorebook_df( df, '裏', innings )
        if bot_sb.empty:
            st.info( '後攻の打席データがありません。' )
        else:
            st.dataframe( bot_sb, use_container_width = True )

    # ── 投手スコア ─────────────────────────────────────────────────
    st.subheader( '投手スコア' )
    col_p1, col_p2 = st.columns( 2 )

    with col_p1:
        st.markdown( f'**{ top_team } 投手**' )
        p_top = _pitcher_df( df, '裏' )
        if p_top.empty:
            st.info( 'データがありません。' )
        else:
            st.dataframe( p_top, use_container_width = True )

    with col_p2:
        st.markdown( f'**{ bot_team } 投手**' )
        p_bot = _pitcher_df( df, '表' )
        if p_bot.empty:
            st.info( 'データがありません。' )
        else:
            st.dataframe( p_bot, use_container_width = True )

    # ── PDF 出力 ───────────────────────────────────────────────────
    st.divider()
    if st.button( 'PDF 生成', key = 'sc_gen_pdf' ):
        with st.spinner( 'PDF 生成中...' ):
            pdf_buf = generate_score_card_pdf(
                df, top_team, bot_team, game_date, game_kind, innings,
            )
        st.download_button(
            label     = 'PDF ダウンロード',
            data      = pdf_buf.getvalue(),
            file_name = f'score_{ top_team }_vs_{ bot_team }_{ game_date }.pdf',
            mime      = 'application/pdf',
            key       = 'sc_dl_pdf',
        )
