"""スコア表（スコアブック）ページ"""
import pandas as pd
import streamlit as st

from db import game_repo


def _go_start() -> None:
    st.session_state.page_ctg = 'start'


@st.cache_data( ttl = 60 )
def _load_plays( game_id: int, team_id: int ) -> pd.DataFrame:
    return game_repo.get_plays_df_for_game( game_id, owner_team_id = team_id )


def _inning_runs( df: pd.DataFrame ) -> tuple:
    """Returns (top_runs, bot_runs, top_total, bot_total).

    top_runs / bot_runs: dict[inning_int -> runs_scored_in_that_inning]
    """
    innings = sorted( df[ '回' ].dropna().astype( int ).unique().tolist() )
    top_runs: dict = {}
    bot_runs: dict = {}
    prev_top = 0
    prev_bot  = 0

    for inn in innings:
        df_inn = df[ df[ '回' ] == inn ]

        top_half = df_inn[ df_inn[ '表裏' ] == '表' ]
        bot_half  = df_inn[ df_inn[ '表裏' ] == '裏' ]

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
        prev_bot  = cur_bot

    return top_runs, bot_runs, prev_top, prev_bot


def _score_df( df: pd.DataFrame, top_team: str, bot_team: str ) -> pd.DataFrame:
    innings = sorted( df[ '回' ].dropna().astype( int ).unique().tolist() )
    top_runs, bot_runs, top_total, bot_total = _inning_runs( df )

    records = []
    for label, runs_dict, total in [
        ( f'{ top_team }（先攻）', top_runs, top_total ),
        ( f'{ bot_team }（後攻）', bot_runs, bot_total ),
    ]:
        row: dict = { 'チーム': label }
        for inn in innings:
            row[ str( inn ) ] = runs_dict.get( inn, '' )
        row[ '計' ] = total
        records.append( row )

    return pd.DataFrame( records ).set_index( 'チーム' )


def _scorebook_df( df: pd.DataFrame, side: str ) -> pd.DataFrame:
    """Build scorebook grid for one side ('表'=先攻 / '裏'=後攻)."""
    df_ab = df[
        ( df[ '表裏' ]       == side        ) &
        ( df[ '打席の継続' ] == '打席完了'  ) &
        ( df[ '打席結果' ].notna()          ) &
        ( df[ '打席結果' ]   != '0'         ) &
        ( df[ '打席結果' ]   != ''          )
    ].copy()

    if df_ab.empty:
        return pd.DataFrame()

    innings = sorted( df_ab[ '回' ].dropna().astype( int ).unique().tolist() )

    # 打順 → 選手名（最後に出現したもの）
    order_name: dict = {}
    for _, row in df_ab.sort_values( 'プレイの番号' ).iterrows():
        o = row[ '打順' ]
        if pd.notna( o ):
            order_name[ int( o ) ] = str( row[ '打者氏名' ] or '' )

    orders = sorted( order_name.keys() )
    if not orders:
        return pd.DataFrame()

    records = []
    for order in orders:
        row_data: dict = { '打順': order, '選手名': order_name[ order ] }
        for inn in innings:
            results = df_ab[
                ( df_ab[ '打順' ] == order ) & ( df_ab[ '回' ] == inn )
            ][ '打席結果' ].tolist()
            row_data[ str( inn ) ] = ' / '.join( str( r ) for r in results ) if results else ''
        records.append( row_data )

    return pd.DataFrame( records ).set_index( '打順' )


def show() -> None:
    st.button( '← スタートに戻る', on_click = _go_start )
    st.header( 'スコア表' )

    team_id = st.session_state.get( 'logged_in_team_id' )
    games   = game_repo.list_games( team_id = team_id, limit = 200 )

    if not games:
        st.warning( '試合データがありません。先に試合データを入力してください。' )
        return

    # games: (id, 試合日時, Season, Kind, 先攻チーム名, 後攻チーム名)
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

    sel = filtered[ game_idx ]
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

    # ── スコア ─────────────────────────────────────────────────────
    st.subheader( 'スコア' )
    st.dataframe( _score_df( df, top_team, bot_team ), use_container_width = True )

    # ── スコアブック ───────────────────────────────────────────────
    col_top, col_bot = st.columns( 2 )

    with col_top:
        st.subheader( f'先攻：{ top_team }' )
        top_sb = _scorebook_df( df, '表' )
        if top_sb.empty:
            st.info( '先攻の打席データがありません。' )
        else:
            st.dataframe( top_sb, use_container_width = True )

    with col_bot:
        st.subheader( f'後攻：{ bot_team }' )
        bot_sb = _scorebook_df( df, '裏' )
        if bot_sb.empty:
            st.info( '後攻の打席データがありません。' )
        else:
            st.dataframe( bot_sb, use_container_width = True )
