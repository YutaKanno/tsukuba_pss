"""打者作戦分析モジュール。

_0211_tsukuba_pss データモデル対応:
  - 1行/1球（ピッチ単位）
  - 打席結果: 打席完了行のみ記録
  - 打席Id: 各打席に一意のID
"""
import numpy as np
import pandas as pd


_BB_RESULTS  = frozenset( [ '四球', '死球' ] )
_HIT_MULTI   = frozenset( [ '二塁打', '三塁打', '本塁打' ] )
_ADVANCE     = frozenset( [ '二進', '三進', '本進' ] )
_STEAL_OPS   = frozenset( [ '盗塁', 'エンドラン' ] )
_PICKOFF     = frozenset( [ '投手牽制死', '捕手牽制死' ] )
# 三振・犠打の打席結果値（score_card.py / calc_stats.py 両方の表記を包含）
_K_RESULTS   = frozenset( [ '見三振', '空三振', '振逃', '見逃し三振', '空振り三振', '振り逃げ', 'K3' ] )
_SAC_RESULTS = frozenset( [ '犠打', '犠打失策', '犠飛' ] )

COUNT_KEYS = [
    '単打', '長打', '四死球', '三振', '犠打',
    '盗塁成功', '盗塁失敗', '進塁打', '凡打', '併殺', '牽制死',
]


def _ensure_attack_team( df: pd.DataFrame ) -> pd.DataFrame:
    if '攻撃チーム' not in df.columns:
        df = df.copy()
        df[ '攻撃チーム' ] = np.where(
            df[ '表裏' ] == '表', df[ '先攻チーム' ], df[ '後攻チーム' ]
        )
    return df


def _completion_rows( df_team: pd.DataFrame ) -> pd.DataFrame:
    """打席完了行のみを返す。走者情報・アウト数は打席開始時の状態を反映している。"""
    return df_team[ df_team[ '打席の継続' ] == '打席完了' ]


def _empty_counts() -> dict:
    return { k: 0 for k in COUNT_KEYS }


def _count_events(
    df_abs: pd.DataFrame,
    df_complete: pd.DataFrame,
    runner_col: str,
) -> dict:
    """対象打席の全投球行・完了行からイベント数を集計して返す。"""
    ar = (
        df_complete[ '打席結果' ]
        if '打席結果' in df_complete.columns
        else pd.Series( dtype=str )
    )

    # ── 打席結果カテゴリ ─────────────────────────────────────
    n_single  = int( ( ar == '単打'   ).sum() )
    n_longHit = int( ar.isin( _HIT_MULTI  ).sum() )
    n_bb      = int( ar.isin( _BB_RESULTS ).sum() )
    n_k       = int( ar.isin( _K_RESULTS ).sum() )
    n_sac     = int( ar.isin( [ '犠打', '犠打失策' ] ).sum() )

    # ── 盗塁（打球タイプ == '0' の投球行で作戦が盗塁系）────
    if '作戦' in df_abs.columns and runner_col in df_abs.columns:
        steal_rows = df_abs[
            df_abs[ '作戦' ].isin( _STEAL_OPS ) &
            ( df_abs[ '打球タイプ' ].fillna( '0' ) == '0' )
        ]
        n_steal     = int( steal_rows[ runner_col ].isin( _ADVANCE   ).sum() )
        n_stealFail = int( ( steal_rows[ runner_col ] == '封殺' ).sum() )
    else:
        n_steal = n_stealFail = 0

    # ── 凡打系（進塁打 / 凡打 / 併殺）─────────────────────
    # 打撃結果 が 凡打死 / 凡打出塁 の完了行を対象とする
    if '打撃結果' in df_complete.columns and runner_col in df_complete.columns:
        out_rows = df_complete[
            df_complete[ '打撃結果' ].isin( [ '凡打死', '凡打出塁' ] )
        ]
        r_adv  = out_rows[ runner_col ].isin( _ADVANCE )
        r_seal = out_rows[ runner_col ] == '封殺'

        n_progress   = int( r_adv.sum() )
        n_doublePlay = int( ( r_seal & ~r_adv ).sum() )
        n_out        = len( out_rows ) - n_progress - n_doublePlay
    else:
        n_progress = n_doublePlay = n_out = 0

    # ── 牽制死 ──────────────────────────────────────────────
    n_pickoff = (
        int( df_abs[ runner_col ].isin( _PICKOFF ).sum() )
        if runner_col in df_abs.columns
        else 0
    )

    return {
        '単打'   : n_single,
        '長打'   : n_longHit,
        '四死球' : n_bb,
        '三振'   : n_k,
        '犠打'   : n_sac,
        '盗塁成功': n_steal,
        '盗塁失敗': n_stealFail,
        '進塁打' : n_progress,
        '凡打'   : n_out,
        '併殺'   : n_doublePlay,
        '牽制死' : n_pickoff,
    }


def _r1_mask( df: pd.DataFrame, out: int = None ) -> pd.Series:
    mask = (
        ( df[ '一走氏名' ].fillna( '0' ) != '0' ) &
        ( df[ '二走氏名' ].fillna( '0' ) == '0' ) &
        ( df[ '三走氏名' ].fillna( '0' ) == '0' )
    )
    if out is not None:
        mask &= ( pd.to_numeric( df[ 'アウト' ], errors='coerce' ) == out )
    return mask


def _r2_mask( df: pd.DataFrame ) -> pd.Series:
    return (
        ( df[ '二走氏名' ].fillna( '0' ) != '0' ) &
        ( df[ '三走氏名' ].fillna( '0' ) == '0' )
    )


def analyse_R1_strategy( df: pd.DataFrame, b_team: str, out: int = None ) -> dict:
    """1塁のみ（2・3塁なし）の作戦分析。out を指定するとアウト数でさらに絞り込む。"""
    df = _ensure_attack_team( df )
    df_team = df[ df[ '攻撃チーム' ] == b_team ]

    # 完了行: 走者名・アウト数は打席開始時の状態を反映
    df_complete = _completion_rows( df_team )
    df_complete = df_complete[ _r1_mask( df_complete, out ) ]
    if df_complete.empty:
        return _empty_counts()

    # 同一走者状況のすべての投球行（盗塁・牽制判定に使用）
    df_abs = df_team[ _r1_mask( df_team, out ) ]
    return _count_events( df_abs, df_complete, runner_col='一走状況' )


def analyse_R2_strategy( df: pd.DataFrame, b_team: str ) -> dict:
    """2塁ランナーあり（3塁なし）の作戦分析。"""
    df = _ensure_attack_team( df )
    df_team = df[ df[ '攻撃チーム' ] == b_team ]

    df_complete = _completion_rows( df_team )
    df_complete = df_complete[ _r2_mask( df_complete ) ]
    if df_complete.empty:
        return _empty_counts()

    df_abs = df_team[ _r2_mask( df_team ) ]
    return _count_events( df_abs, df_complete, runner_col='二走状況' )
