"""
チーム単位の全プレイ DataFrame を1本の st.cache_data に集約（メモリ削減）。
投手分析・打者分析・スタッツモードで共有する。
"""
import numpy as np
import pandas as pd
import streamlit as st

from db import game_repo

_NUMERIC_COLS = ( 'コースX', 'コースY', '打球位置X', '打球位置Y', 'S', 'B', '構え' )


def _add_derived_columns( df: pd.DataFrame ) -> pd.DataFrame:
    df = df.copy()
    df[ '守備チーム' ] = np.where( df[ '表裏' ] == '表', df[ '後攻チーム' ], df[ '先攻チーム' ] )
    df[ '攻撃チーム' ] = np.where( df[ '表裏' ] == '表', df[ '先攻チーム' ], df[ '後攻チーム' ] )
    df[ 'コースYadj' ]   = 263 - pd.to_numeric( df[ 'コースY' ],    errors = 'coerce' )
    df[ '打球位置Yadj' ] = 263 - pd.to_numeric( df[ '打球位置Y' ], errors = 'coerce' )
    df[ '_date' ] = pd.to_datetime( df[ '試合日時' ], errors = 'coerce' )
    return df


@st.cache_data( ttl=3600, max_entries=16, show_spinner=False )
def get_cached_team_plays_df( team_id: int ) -> pd.DataFrame:
    """owner_team_id に紐づく全プレイを前処理済みで返す（単一キャッシュ）。"""
    df = game_repo.get_all_plays_df( team_id )
    if df.empty:
        return df
    for col in _NUMERIC_COLS:
        if col in df.columns:
            df[ col ] = pd.to_numeric( df[ col ], errors = 'coerce' )
    df = df[ df[ '球種' ] != '特殊球' ]
    return _add_derived_columns( df )


def clear_team_plays_cache() -> None:
    """DB 更新後にプレイ DataFrame キャッシュを無効化する。"""
    get_cached_team_plays_df.clear()
