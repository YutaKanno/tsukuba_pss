"""スコア表（スコアブック）ページ"""
import io
import json
import os

import matplotlib
matplotlib.use( 'Agg' )
import matplotlib.pyplot as plt
from matplotlib import font_manager
import pandas as pd
import streamlit as st

from db import game_repo


_HIT_RESULTS   = frozenset( { '単打', '二塁打', '三塁打', '本塁打' } )
_K_RESULTS     = frozenset( { '見三振', '空三振', '振逃' } )
_BB_RESULTS    = frozenset( { '四球', '死球' } )
_ERROR_RESULTS = frozenset( { 'エラー' } )
_SAC_RESULTS   = frozenset( { '犠打', '犠飛' } )

# PDF セル文字色
_COLOR_HIT = '#DC2626'   # 赤（ヒット）
_COLOR_BB  = '#2563EB'   # 青（四死球・エラー）
_COLOR_SAC = '#16A34A'   # 緑（犠打・犠飛）


def _result_color( text: str ):
    """打席結果テキストに対応する PDF 文字色を返す（なければ None）。

    '単打 / 三振' のような打者一巡表記は全パーツを確認し優先度で判定:
    ヒット > 四死球/エラー > 犠打/犠飛
    （1セルは単色テキストのため複数色には対応不可）
    """
    parts = [ p.strip() for p in text.split( '/' ) ]
    if any( p in _HIT_RESULTS for p in parts ):
        return _COLOR_HIT
    if any( p in _BB_RESULTS or p in _ERROR_RESULTS for p in parts ):
        return _COLOR_BB
    if any( p in _SAC_RESULTS for p in parts ):
        return _COLOR_SAC
    return None


def _scorebook_color_fn( df: 'pd.DataFrame' ):
    """スコアブック用セル文字色関数を返す（イニング列のみ適用）。"""
    col_headers = [ str( df.index.name ) ] + df.columns.tolist()
    inning_cols = { i for i, h in enumerate( col_headers ) if h.isdigit() }

    def fn( r, col, text ):
        if col not in inning_cols or not text:
            return None
        return _result_color( text )

    return fn


def _score_table_color_fn( df: 'pd.DataFrame' ):
    """スコアテーブル用セル文字色関数を返す（点が入ったイニング列を赤）。"""
    col_headers = [ str( df.index.name ) ] + df.columns.tolist()
    inning_cols = { i for i, h in enumerate( col_headers ) if h.isdigit() }

    def fn( r, col, text ):
        if col not in inning_cols:
            return None
        try:
            if int( text ) > 0:
                return _COLOR_HIT
        except ( ValueError, TypeError ):
            pass
        return None

    return fn


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

    # 打順ごとに出現順の選手リストを構築
    # → 同打順内では時系列順、打順間は打順番号順に並べる
    from collections import defaultdict as _dd
    order_players_seq: dict = _dd( list )
    seen_keys: set = set()
    for _, row in df_ab.iterrows():
        o = row[ '打順' ]
        n = str( row[ '打者氏名' ] or '' )
        if pd.notna( o ):
            k = ( int( o ), n )
            if k not in seen_keys:
                seen_keys.add( k )
                order_players_seq[ int( o ) ].append( n )

    if not order_players_seq:
        return pd.DataFrame()

    # 打順昇順 → 各打順内は出現順（代打は元選手の直下に来る）
    entry_keys = [
        ( order, name )
        for order in sorted( order_players_seq.keys() )
        for name  in order_players_seq[ order ]
    ]

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
        pos_display = ''.join( positions ) if positions else ''

        # 打席左右（最初の非 null 値を使用）
        lr_series = player_ab[ '打席左右' ].dropna()
        lr_val    = str( lr_series.iloc[ 0 ] ) if not lr_series.empty else ''

        row_data: dict = {
            '打順'   : order,
            '守備位置': pos_display,
            '選手名' : name,
            '打席左右': lr_val,
        }
        for inn in innings:
            # 同一イニングに複数打席（打者一巡）は「/」で列挙
            results = player_ab[ player_ab[ '回' ] == inn ][ '打席結果' ].tolist()
            row_data[ str( inn ) ] = ' / '.join( str( r ) for r in results ) if results else ''
        records.append( row_data )

    return pd.DataFrame( records ).set_index( '打順' )


_NON_OUT_RESULTS = _HIT_RESULTS | _BB_RESULTS | _ERROR_RESULTS


def _format_ip( outs: int ) -> str:
    """アウト数を投球回表記に変換（例: 7 → '2⅓'）。"""
    full = outs // 3
    rem  = outs % 3
    if rem == 0:
        return str( full )
    frac = '⅓' if rem == 1 else '⅔'
    return f'{ full }{ frac }' if full > 0 else frac


def _pitcher_df( df: pd.DataFrame, batting_side: str ) -> pd.DataFrame:
    """投手スコアテーブル。

    batting_side='表': 先攻打席 → 後攻投手のスコア
    batting_side='裏': 後攻打席 → 先攻投手のスコア

    投手名は全プレイ（投球含む）から取得し、完了打席がなくても
    投球数だけ記録されている場合も表示できるようにする。
    """
    df_s = df[ df[ '表裏' ] == batting_side ]

    if df_s.empty:
        return pd.DataFrame()

    # 投手名は全プレイから（完了打席がなくても名前を取得できる）
    pitcher_order = (
        df_s.dropna( subset = [ '投手氏名' ] )
            .drop_duplicates( '投手氏名' )[ '投手氏名' ]
            .tolist()
    )
    if not pitcher_order:
        return pd.DataFrame()

    # 完了打席（投球回・H/K/B 集計に使用）
    df_ab = df_s[
        ( df_s[ '打席の継続' ] == '打席完了' ) &
        ( df_s[ '打席結果' ].notna()         ) &
        ( df_s[ '打席結果' ]  != '0'         ) &
        ( df_s[ '打席結果' ]  != ''          )
    ]

    records = []
    for pitcher in pitcher_order:
        grp     = df_ab[ df_ab[ '投手氏名' ] == pitcher ] if not df_ab.empty else df_ab
        results = grp[ '打席結果' ].tolist()

        total_pitches = df_s[
            ( df_s[ '投手氏名'     ] == pitcher ) &
            ( df_s[ 'プレイの種類' ] == '投球'  )
        ].shape[ 0 ]

        # 投球回：ヒット・四死球・エラー以外の完了打席をアウトとみなす
        outs = sum( 1 for r in results if r not in _NON_OUT_RESULTS and r )

        records.append( {
            '投手'  : pitcher,
            '投球回': _format_ip( outs ),
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

# モダンカラーパレット
_PC_HDR_BG   = '#1E293B'   # ヘッダー背景（ダークネイビー）
_PC_HDR_TEXT = '#FFFFFF'   # ヘッダー文字
_PC_IDX_BG   = '#E2E8F0'   # インデックス列背景
_PC_IDX_TEXT = '#334155'   # インデックス列文字
_PC_ROW_ODD  = '#F8FAFC'   # 奇数データ行
_PC_ROW_EVEN = '#FFFFFF'   # 偶数データ行
_PC_EDGE     = '#CBD5E1'   # 罫線
_PC_ACCENT   = '#3B82F6'   # セクションタイトルアクセント


def _draw_table_on_ax(
    ax: plt.Axes,
    df: pd.DataFrame,
    title: str,
    cell_text_color_fn  = None,
    compact_cols: set   = None,
    blank_header_cols: set = None,
) -> None:
    """DataFrame を1つの Axes にスタイル付きテーブルとして描画する。

    Parameters
    ----------
    cell_text_color_fn : callable(r, col, text) -> str | None
        データセルの文字色を返す関数。None のとき色付けなし。
    compact_cols : set of str
        列名を空白にして幅を1文字分（1.0倍補正）に抑えたい列名の集合。
    blank_header_cols : set of str
        列名を空白にするが幅は通常（1.5倍補正）の列名の集合。
    """
    ax.axis( 'off' )
    ax.set_facecolor( 'white' )

    if df.empty:
        ax.text( 0.5, 0.5, 'データなし', ha = 'center', va = 'center',
                 fontsize = _PDF_FONTSIZE, color = '#64748B',
                 transform = ax.transAxes )
        return

    if title:
        ax.set_title(
            title,
            fontsize   = _PDF_FONTSIZE + 1,
            fontweight = 'bold',
            color      = '#1E293B',
            loc        = 'left',
            pad        = 4,
        )

    # インデックスを通常列に含めることで auto_set_column_width の対象にする
    # （rowLabels は auto_set_column_width が効かないため列幅が異常に広くなる）
    df_disp     = df.reset_index()
    col_headers = df_disp.columns.tolist()
    n_cols      = len( col_headers )

    # ヘッダー非表示 index セットを構築
    compact_idxs      = { i for i, h in enumerate( col_headers ) if compact_cols      and h in compact_cols      }
    blank_header_idxs = { i for i, h in enumerate( col_headers ) if blank_header_cols and h in blank_header_cols }
    hidden_header_idxs = compact_idxs | blank_header_idxs

    # ヘッダー行で非表示対象の列名を空白にする
    display_headers = [
        '' if i in hidden_header_idxs else h
        for i, h in enumerate( col_headers )
    ]
    all_text  = [ display_headers ] + df_disp.fillna( '' ).astype( str ).values.tolist()
    total_row = len( all_text )

    table = ax.table(
        cellText = all_text,
        cellLoc  = 'center',
        bbox     = [ 0, 0, 1, 1 ],
    )
    table.auto_set_font_size( False )
    table.set_fontsize( _PDF_FONTSIZE )
    table.auto_set_column_width( list( range( n_cols ) ) )
    table.scale( 1, 1.25 )

    # Linux/CJK 文字幅補正
    # compact 列は 1.0 倍（1文字分幅）、それ以外は 1.5 倍
    for col in range( n_cols ):
        mult = 1.0 if col in compact_idxs else 1.5
        for r in range( total_row ):
            if ( r, col ) in table._cells:
                w = table._cells[ r, col ].get_width()
                table._cells[ r, col ].set_width( w * mult )

    # セル着色を cell.set_facecolor() で直接指定（platform に依存しない）
    for ( r, col ), cell in table._cells.items():
        cell.set_edgecolor( _PC_EDGE )
        cell.set_linewidth( 0.3 )
        cell.PAD = 0.04

        if r == 0:                          # ヘッダー行
            cell.set_facecolor( _PC_HDR_BG )
            cell.set_text_props( color = _PC_HDR_TEXT, fontweight = 'bold' )
        elif col == 0:                      # インデックス列（元 rowLabels）
            cell.set_facecolor( _PC_IDX_BG )
            cell.set_text_props( color = _PC_IDX_TEXT, fontweight = 'bold' )
        else:                               # データセル
            cell.set_facecolor( _PC_ROW_ODD if r % 2 == 1 else _PC_ROW_EVEN )
            if cell_text_color_fn is not None:
                tc = cell_text_color_fn( r, col, cell.get_text().get_text() )
                if tc:
                    cell.set_text_props( color = tc )


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

    # 色付け関数
    score_color  = _score_table_color_fn( score_data ) if not score_data.empty else None
    top_sb_color = _scorebook_color_fn( top_sb )       if not top_sb.empty   else None
    bot_sb_color = _scorebook_color_fn( bot_sb )       if not bot_sb.empty   else None

    # スコア（2列連結）
    ax_score = fig.add_subplot( gs[ 0, : ] )
    _draw_table_on_ax( ax_score, score_data, 'スコア',
                       cell_text_color_fn = score_color )

    # 先攻スコアブック（2列連結）
    ax_top = fig.add_subplot( gs[ 1, : ] )
    _draw_table_on_ax( ax_top, top_sb, f'先攻スコアブック：{ top_team }',
                       cell_text_color_fn = top_sb_color,
                       compact_cols       = { '打席左右' },
                       blank_header_cols  = { '打順', '選手名', '守備位置' } )

    # 後攻スコアブック（2列連結）
    ax_bot = fig.add_subplot( gs[ 2, : ] )
    _draw_table_on_ax( ax_bot, bot_sb, f'後攻スコアブック：{ bot_team }',
                       cell_text_color_fn = bot_sb_color,
                       compact_cols       = { '打席左右' },
                       blank_header_cols  = { '打順', '選手名', '守備位置' } )

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
