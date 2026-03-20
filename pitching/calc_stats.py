import numpy as np
import pandas as pd


def calc_stats( df_p, pitch_type, batter_side, stats_dict ):

    df_p_pt = df_p[ df_p[ '打撃結果' ] != '0' ]

    if batter_side is not None:
        df_p_pt = df_p_pt[ ( df_p_pt[ '打席左右' ] == batter_side ) ]

    if pitch_type is not None:
        df_p_pt = df_p_pt[ ( df_p_pt[ '球種' ] == pitch_type ) ]

    info_dict = {
        '球種': pitch_type,
        '打席左右': batter_side,
    }

    # ================================
    # Basic Stats
    # ================================
    # Pitch Count
    n_pitch = len( df_p_pt )

    # Strike%
    n_strike = len( df_p_pt[ ~ df_p_pt[ '打撃結果' ].isin( [ 'ボール', '四球', '死球' ] ) ] )

    if n_pitch > 0:
        strike_rate = round( 100 * n_strike / n_pitch )
    else:
        strike_rate = np.nan

    # Zone%
    in_zone_mask = (
        ( df_p_pt[ 'コースX' ] >= 53 ) &
        ( df_p_pt[ 'コースX' ] <= 210 ) &
        ( df_p_pt[ 'コースYadj' ] >= 53 ) &
        ( df_p_pt[ 'コースYadj' ] <= 210 )
    )
    n_inZone = len( df_p_pt[ in_zone_mask ] )

    if n_pitch > 0:
        inZone_rate = round( 100 * n_inZone / n_pitch )
    else:
        inZone_rate = np.nan

    # SwStr%
    n_swing = len( df_p_pt[ ~ df_p_pt[ '打撃結果' ].isin( [ '見逃し', '見逃し三振', 'ボール', '死球', '四球' ] ) ] )

    if n_pitch > 0:
        swing_rate = round( 100 * n_swing / n_pitch )
    else:
        swing_rate = np.nan

    # Whiff%
    n_whiff = len( df_p_pt[ df_p_pt[ '打撃結果' ].isin( [ '空振り', '空振り三振' ] ) ] )

    if n_swing > 0:
        whiff_rate = round( 100 * n_whiff / n_swing )
    else:
        whiff_rate = np.nan

    # O-Swing%
    swing_mask  = ~ df_p_pt[ '打撃結果' ].isin( [ '見逃し', '見逃し三振', 'ボール', '死球', '四球' ] )
    out_zone_mask = ~ in_zone_mask
    n_oSwing  = len( df_p_pt[ swing_mask & out_zone_mask ] )
    n_outZone = len( df_p_pt[ out_zone_mask ] )

    if n_outZone > 0:
        oSwing_rate = round( 100 * n_oSwing / n_outZone )
    else:
        oSwing_rate = np.nan

    # PutAway%
    n_strikeOut = len( df_p_pt[ df_p_pt[ '打撃結果' ].isin( [ '見逃し三振', '空振り三振', 'K3', '振り逃げ' ] ) ] )
    n_pitch2S   = len( df_p_pt[ df_p_pt[ 'S' ] == 2 ] )

    if n_pitch2S > 0:
        putAway_rate = round( 100 * n_strikeOut / n_pitch2S )
    else:
        putAway_rate = np.nan

    # GB%, FB%
    n_batted     = len( df_p_pt[ ( df_p_pt[ '打球位置X' ] != 0 ) & ( df_p_pt[ '打球位置Y' ] != 0 ) & ( df_p_pt[ '打席の継続' ] == '打席完了' ) ] )
    n_groundBall = len( df_p_pt[ ( df_p_pt[ '打球タイプ' ] == 'ゴロ' ) & ( df_p_pt[ '打席の継続' ] == '打席完了' ) ] )
    n_flyBall    = len( df_p_pt[ ( df_p_pt[ '打球タイプ' ] == 'フライ' ) & ( df_p_pt[ '打席の継続' ] == '打席完了' ) ] )

    if n_batted > 0:
        ground_rate = round( 100 * n_groundBall / n_batted )
        fly_rate    = round( 100 * n_flyBall / n_batted )
    else:
        ground_rate = np.nan
        fly_rate    = np.nan

    # OAV, SLG
    n_plate   = len( df_p_pt[ df_p_pt[ '打席の継続' ] == '打席完了' ] )
    n_removal = len( df_p_pt[ df_p_pt[ '打撃結果' ].isin( [ '四球', '死球', '犠打', '犠飛' ] ) ] )
    n_hits    = len( df_p_pt[ df_p_pt[ '打撃結果' ].isin( [ '単打', '二塁打', '三塁打', '本塁打' ] ) ] )
    n_base    = (
        len( df_p_pt[ df_p_pt[ '打撃結果' ] == '単打' ] ) +
        2 * len( df_p_pt[ df_p_pt[ '打撃結果' ] == '二塁打' ] ) +
        3 * len( df_p_pt[ df_p_pt[ '打撃結果' ] == '三塁打' ] ) +
        4 * len( df_p_pt[ df_p_pt[ '打撃結果' ] == '本塁打' ] )
    )

    if ( n_plate - n_removal ) > 0:
        oav = round( n_hits / ( n_plate - n_removal ), 3 )
        slg = round( n_base / ( n_plate - n_removal ), 3 )
    else:
        oav = np.nan
        slg = np.nan

    # OBA
    n_onBase   = n_hits + len( df_p_pt[ df_p_pt[ '打撃結果' ].isin( [ '四球', '死球' ] ) ] )
    n_obaDenom = n_plate - n_removal + len( df_p_pt[ df_p_pt[ '打撃結果' ].isin( [ '四球', '死球', '犠飛' ] ) ] )

    if n_obaDenom > 0:
        oba = round( n_onBase / n_obaDenom, 3 )
    else:
        oba = np.nan

    # OPS
    if not ( np.isnan( oba ) or np.isnan( slg ) ):
        ops = round( oba + slg, 3 )
    else:
        ops = np.nan

    row_dict = {
        '投球数': n_pitch,
        'ストライク率': strike_rate,
        'ゾーン率': inZone_rate,
        'スイング率': swing_rate,
        '空振り率': whiff_rate,
        'ゾーン外スイング率': oSwing_rate,
        'PutAway率': putAway_rate,
        'ゴロ率': ground_rate,
        'フライ率': fly_rate,
        '被打率': oav,
        '出塁率': oba,
        '長打率': slg,
        'OPS': ops,
    }

    # ================================
    # Aim
    # ================================
    if n_pitch > 0:
        aim3rd  = round( 100 * len( df_p_pt[ df_p_pt[ '構え' ].isin( [ 11, 12, 16, 17, 21, 22 ] ) ] ) / n_pitch )
        aimMid  = round( 100 * len( df_p_pt[ df_p_pt[ '構え' ].isin( [ 13, 18, 23 ] ) ] ) / n_pitch )
        aim1st  = round( 100 * len( df_p_pt[ df_p_pt[ '構え' ].isin( [ 14, 15, 19, 20, 24, 25 ] ) ] ) / n_pitch )
        aimHigh = round( 100 * len( df_p_pt[ df_p_pt[ '構え' ] <= 10 ] ) / n_pitch )
    else:
        aim3rd = aimMid = aim1st = aimHigh = np.nan

    aim_dict = {
        '3塁側構え': aim3rd,
        '真ん中構え': aimMid,
        '1塁側構え': aim1st,
        '高め構え': aimHigh,
    }

    stats_dict[ f'{pitch_type}_vs{batter_side}' ] = {
        'info_dict':  info_dict,
        'stats_dict': row_dict,
        'aim_dict':   aim_dict,
    }

    return stats_dict


def calc_overallStats( df_p, batter_side, label ):

    df_p_pt = df_p[ df_p[ '打撃結果' ] != '0' ]

    if batter_side is not None:
        df_p_pt = df_p_pt[ df_p_pt[ '打席左右' ] == batter_side ]

    # 登板数
    n_game = df_p_pt.drop_duplicates( subset = [ '試合日時', '先攻チーム', '後攻チーム' ] ).shape[ 0 ]

    # 投球回
    n_inning = round(
        len( df_p_pt[ df_p_pt[ '打者状況' ] == 'アウト' ] ) +
        len( df_p_pt[ df_p_pt[ '一走状況' ].isin( [ '封殺', '投手牽制死', '捕手牽制死' ] ) ] ) +
        len( df_p_pt[ df_p_pt[ '二走状況' ].isin( [ '封殺', '投手牽制死', '捕手牽制死' ] ) ] ) +
        len( df_p_pt[ df_p_pt[ '三走状況' ].isin( [ '封殺', '投手牽制死', '捕手牽制死' ] ) ] ) / 3,
        1
    )

    # 投球数
    n_pitch = len( df_p_pt )

    # 打席数
    n_pa = len( df_p_pt[ df_p_pt[ '打席の継続' ] == '打席完了' ] )

    # 安打数
    n_hit = len( df_p_pt[ df_p_pt[ '打撃結果' ].isin( [ '単打', '二塁打', '三塁打', '本塁打' ] ) ] )

    # 本塁打
    n_hr = len( df_p_pt[ df_p_pt[ '打撃結果' ] == '本塁打' ] )

    # 奪三振
    n_k = len( df_p_pt[ df_p_pt[ '打撃結果' ].isin( [ '見逃し三振', '空振り三振', 'K3', '振り逃げ' ] ) ] )

    # 四死球
    n_bb = len( df_p_pt[ df_p_pt[ '打撃結果' ].isin( [ '四球', '死球' ] ) ] )

    # 失点
    n_runs = len( df_p_pt[ df_p_pt[ '打者状況' ] == '本進' ] )

    # 失点率
    runs_rate = round( 9 * n_runs / n_inning, 2 ) if n_inning > 0 else np.nan

    # ストライク率
    n_strike  = len( df_p_pt[ ~ df_p_pt[ '打撃結果' ].isin( [ 'ボール', '四球', '死球' ] ) ] )
    strike_rate = round( 100 * n_strike / n_pitch ) if n_pitch > 0 else np.nan

    # 空振り率
    n_whiff = len( df_p_pt[ df_p_pt[ '打撃結果' ].isin( [ '空振り', '空振り三振' ] ) ] )
    n_swing = len( df_p_pt[ ~ df_p_pt[ '打撃結果' ].isin( [ '見逃し', '見逃し三振', 'ボール', '死球', '四球' ] ) ] )
    whiff_rate = round( 100 * n_whiff / n_swing ) if n_swing > 0 else np.nan

    # 打数
    n_sac = len( df_p_pt[ df_p_pt[ '打撃結果' ].isin( [ '犠打', '犠飛' ] ) ] )
    n_ab  = n_pa - n_bb - n_sac

    # 被打率
    oav = round( n_hit / n_ab, 3 ) if n_ab > 0 else np.nan

    # 被出塁率
    n_sf        = len( df_p_pt[ df_p_pt[ '打撃結果' ] == '犠飛' ] )
    n_on_base   = n_hit + n_bb
    n_oba_denom = n_ab + n_bb + n_sf
    oba = round( n_on_base / n_oba_denom, 3 ) if n_oba_denom > 0 else np.nan

    # 長打率
    n_base = (
        len( df_p_pt[ df_p_pt[ '打撃結果' ] == '単打'  ] ) +
        2 * len( df_p_pt[ df_p_pt[ '打撃結果' ] == '二塁打' ] ) +
        3 * len( df_p_pt[ df_p_pt[ '打撃結果' ] == '三塁打' ] ) +
        4 * len( df_p_pt[ df_p_pt[ '打撃結果' ] == '本塁打' ] )
    )
    slg = round( n_base / n_ab, 3 ) if n_ab > 0 else np.nan

    # OPS
    ops = round( oba + slg, 3 ) if pd.notna( oba ) and pd.notna( slg ) else np.nan

    # K%, BB%, K-BB%
    k_rate  = round( 100 * n_k  / n_pa, 1 ) if n_pa > 0 else np.nan
    bb_rate = round( 100 * n_bb / n_pa, 1 ) if n_pa > 0 else np.nan
    k_bb_rate = round( k_rate - bb_rate, 1 ) if pd.notna( k_rate ) and pd.notna( bb_rate ) else np.nan

    # 内野フライ率 / ゴロ率
    n_batted = len( df_p_pt[
        df_p_pt[ '打球タイプ' ].notna() &
        ( df_p_pt[ '打球タイプ' ] != '' ) &
        ( df_p_pt[ '打席の継続' ] == '打席完了' )
    ] )
    n_ifb = len( df_p_pt[
        ( df_p_pt[ '打球タイプ' ] == 'フライ' ) &
        ( df_p_pt[ '打席の継続' ] == '打席完了' ) &
        df_p_pt[ '捕球選手' ].astype( str ).isin( [ '1', '2', '3', '4', '5', '6' ] )
    ] )
    n_gb = len( df_p_pt[ df_p_pt[ '打球タイプ' ] == 'ゴロ' ] )

    ifb_rate = round( 100 * n_ifb / n_batted, 1 ) if n_batted > 0 else np.nan
    gb_rate  = round( 100 * n_gb  / n_batted, 1 ) if n_batted > 0 else np.nan

    return {
        'index':        label,
        '登板数':       n_game,
        '投球回':       n_inning,
        '投球数':       n_pitch,
        '打席数':       n_pa,
        '安打数':       n_hit,
        '本塁打数':     n_hr,
        '奪三振数':     n_k,
        '四死球数':     n_bb,
        '失点数':       n_runs,
        '失点率':       runs_rate,
        'ストライク率': strike_rate,
        '空振り率':     whiff_rate,
        '被打率':       oav,
        '被出塁率':     oba,
        '長打率':       slg,
        'OPS':          ops,
        '奪三振率':     k_rate,
        '四死球率':     bb_rate,
        'K-BB%':        k_bb_rate,
        '内野フライ率': ifb_rate,
        'ゴロ率':       gb_rate,
    }


def convert_stats_dict_to_df( stats_dict: dict ) -> pd.DataFrame:
    rows = {}
    for key, val in stats_dict.items():
        rows[ key ] = { **val[ 'info_dict' ], **val[ 'stats_dict' ], **val[ 'aim_dict' ] }

    df = pd.DataFrame( rows ).T.reset_index( drop = True ).drop( columns = [ '打席左右' ] )

    for col in [ '被打率', '出塁率', '長打率' ]:
        if col in df.columns:
            df[ col ] = df[ col ].apply(
                lambda v: f'{v:.3f}'[ 1: ] if pd.notna( v ) and isinstance( v, float ) else v
            )

    return df
