"""打者スタッツ算出モジュール。

_0211_tsukuba_pss のデータモデル（1行/1球）に対応:
- 打席結果 : 打席完了行にのみ記録される打席単位の結果（単打, 三振, …）
- 打撃結果 : 全投球行の投球結果（ボール, 空振り, …）
"""
import numpy as np
import pandas as pd


_NO_SWING = frozenset( [ '見逃し', '見逃し三振', 'ボール', '死球', '四球' ] )
_K_RESULTS = frozenset( [ '見逃し三振', '空振り三振', '振り逃げ', 'K3' ] )


def calc_batting_stats(
    df: pd.DataFrame,
    pitcher_side = None,
    label: str   = '',
) -> dict:
    """打者スタッツを算出して辞書で返す。

    Parameters
    ----------
    df : DataFrame
        対象打者の全プレイデータ（全打席・全投球）
    pitcher_side : str | None
        None = 全体, '右' = 対右投手, '左' = 対左投手
    label : str
        打者氏名（戻り値 'index' キーに使用）
    """
    if pitcher_side is not None:
        df = df[ df[ '投手左右' ] == pitcher_side ].copy()

    # ── 完了打席 ────────────────────────────────────────────────
    df_ab  = df[ df[ '打席の継続' ] == '打席完了' ]
    n_plate = len( df_ab )

    # 打数（打席数 - 犠打・犠飛・四球・死球）
    n_removal = int( df_ab[ '打席結果' ].isin( [ '犠打', '犠飛', '四球', '死球' ] ).sum() )
    n_atBat   = n_plate - n_removal

    # ── 投球データ ───────────────────────────────────────────────
    df_p    = df[ df[ '打撃結果' ] != '0' ]
    n_pitch = len( df_p )

    # 2S打席 / 2S以降投球
    n_2sPlate = int( df_ab[ df_ab[ 'S' ] == 2 ].shape[ 0 ] )
    n_2sPitch = int( df_p[ df_p[ 'S' ] == 2 ].shape[ 0 ] )

    # ゾーン（コースYadj が _add_analysis_cols で生成済みなら使用）
    y_col = 'コースYadj' if 'コースYadj' in df_p.columns else 'コースY'
    in_zone = (
        ( df_p[ 'コースX' ] >= 53 ) & ( df_p[ 'コースX' ] <= 210 ) &
        ( df_p[ y_col ]    >= 53 ) & ( df_p[ y_col ]    <= 210 )
    )
    n_inZone  = int( in_zone.sum() )
    n_outZone = n_pitch - n_inZone

    # スイング
    swing_mask     = ~df_p[ '打撃結果' ].isin( _NO_SWING )
    n_swing        = int( swing_mask.sum() )
    n_outZoneSwing = int( ( swing_mask & ~in_zone ).sum() )

    # ファーストストライク見逃し / スイング
    n_1stMiss  = int( ( ( df_p[ '打撃結果' ] == '見逃し' ) & ( df_p[ 'S' ] == 0 ) ).sum() )
    n_1stSwing = n_plate - n_1stMiss

    # 空振り
    n_whiff = int( df_p[ '打撃結果' ].isin( [ '空振り', '空振り三振' ] ).sum() )

    # ── 打席結果（at-bat level）────────────────────────────────
    ar        = df_ab[ '打席結果' ]
    n_single  = int( ( ar == '単打'   ).sum() )
    n_double  = int( ( ar == '二塁打' ).sum() )
    n_triple  = int( ( ar == '三塁打' ).sum() )
    n_homeRun = int( ( ar == '本塁打' ).sum() )
    n_hit     = n_single + n_double + n_triple + n_homeRun
    n_base    = n_single + 2 * n_double + 3 * n_triple + 4 * n_homeRun

    n_k        = int( ar.isin( _K_RESULTS ).sum() )
    n_bb       = int( ( ar == '四球' ).sum() )
    n_hbp      = int( ( ar == '死球' ).sum() )
    n_bb_total = n_bb + n_hbp
    n_sacBunt  = int( ar.isin( [ '犠打', '犠打失策' ] ).sum() )
    n_sacFly   = int( ( ar == '犠飛' ).sum() )
    n_onBase   = n_hit + n_bb_total

    # 打点（本進）
    n_run = sum(
        int( df[ sc ].fillna( '' ).astype( str ).str.contains( '本進', na=False ).sum() )
        for sc in [ '打者状況', '一走状況', '二走状況', '三走状況' ]
        if sc in df.columns
    )

    # ── 打球 ─────────────────────────────────────────────────────
    if '打球タイプ' in df_ab.columns:
        df_bat  = df_ab[ df_ab[ '打球タイプ' ].notna() & ( df_ab[ '打球タイプ' ] != '0' ) ]
    else:
        df_bat = df_ab.iloc[ 0:0 ]
    n_batted     = len( df_bat )
    n_groundBall = int( ( df_bat[ '打球タイプ' ] == 'ゴロ'     ).sum() ) if n_batted else 0
    n_lineDrive  = int( ( df_bat[ '打球タイプ' ] == 'ライナー' ).sum() ) if n_batted else 0

    if '捕球選手' in df_bat.columns and n_batted:
        fielder       = pd.to_numeric( df_bat[ '捕球選手' ], errors='coerce' )
        fly_mask      = df_bat[ '打球タイプ' ] == 'フライ'
        n_inFieldFly  = int( ( fly_mask & ( fielder < 7  ) ).sum() )
        n_outFieldFly = int( ( fly_mask & ( fielder >= 7 ) ).sum() )
    else:
        n_inFieldFly = n_outFieldFly = 0
    n_flyBall = n_inFieldFly + n_outFieldFly

    # ── rates ─────────────────────────────────────────────────────
    def _r( num, denom, pct=True, dec=1 ):
        if denom and denom > 0:
            v = num / denom
            return round( 100 * v if pct else v, dec )
        return np.nan

    avg = round( n_hit  / n_atBat,              3 ) if n_atBat > 0                   else np.nan
    slg = round( n_base / n_atBat,              3 ) if n_atBat > 0                   else np.nan
    oba = round( n_onBase / ( n_plate - n_sacFly ), 3 ) if ( n_plate - n_sacFly ) > 0 else np.nan
    ops = round( oba + slg, 3 ) if not ( np.isnan( oba ) or np.isnan( slg ) ) else np.nan

    return {
        'index'        : label,
        '打席数'       : n_plate,
        '打数'         : n_atBat,
        '打率'         : avg,
        '出塁率'       : oba,
        '長打率'       : slg,
        'OPS'          : ops,
        '安打数'       : n_hit,
        '本塁打数'     : n_homeRun,
        '打点'         : n_run,
        '三振数'       : n_k,
        '四死球数'     : n_bb_total,
        'K%'           : _r( n_k,           n_plate ),
        'BB%'          : _r( n_bb_total,    n_plate ),
        '犠打数'       : n_sacBunt,
        '平均投球数'       : _r( n_pitch,   n_plate,  pct=False ),
        '2S以降平均投球数' : _r( n_2sPitch, n_2sPlate, pct=False ),
        'スイング率'   : _r( n_swing,        n_pitch  ),
        'ゾーン外SW%'  : _r( n_outZoneSwing, n_outZone ),
        '空振り率'     : _r( n_whiff,        n_swing  ),
        '1stSW率'      : _r( n_1stSwing,     n_plate  ),
        'ゴロ率'       : _r( n_groundBall, n_batted ),
        'フライ率'     : _r( n_flyBall,    n_batted ),
    }
