"""
Compute pitcher/batter stats for display.
"""
from typing import Any, Union

import pandas as pd


def cal_stats(
    df: pd.DataFrame,
    投手氏名: str,
    相手投手: str,
    打者氏名: str,
    次打者氏名: str,
    試合日時: str,
) -> dict:
    """Return dict of today/season stats for the given pitcher and batters."""
    def safe_div( numerator: Union[int, float], denominator: Union[int, float], scale: int = 1000 ) -> Any:
        return round( scale * numerator / denominator ) if denominator != 0 else '--'

    def safe_rate( numerator: Union[int, float], denominator: Union[int, float] ) -> Any:
        return round( numerator / denominator, 2 ) if denominator != 0 else '--'

    def safe_round_div( numerator: Union[int, float], denominator: Union[int, float], decimals: int = 1 ) -> Any:
        return round( numerator / denominator, decimals ) if denominator != 0 else '--'

    # 今日の投手成績
    dfff = df[(df['投手氏名'] == 投手氏名) & (df['試合日時'] == 試合日時)]
    dff = df[df['投手氏名'] == 投手氏名]

    out_counts_today = (
        len(dfff[dfff['打者状況'] == 'アウト']) +
        len(dfff[dfff['一走状況'].isin(['封殺', '投手牽制死', '捕手牽制死'])]) +
        len(dfff[dfff['二走状況'].isin(['封殺', '投手牽制死', '捕手牽制死'])]) +
        len(dfff[dfff['三走状況'].isin(['封殺', '投手牽制死', '捕手牽制死'])])
    )
    投球回 = safe_round_div(out_counts_today, 3)

    Max = dfff['球速'].max() if not dfff.empty else '--'
    dfff_fb = dfff[(dfff['球種'] == 'ストレート') & (dfff['球速'] != 0)]
    Mean = round(dfff_fb['球速'].mean(), 1) if not dfff_fb.empty else '--'

    H = dfff['打撃結果'].isin(['単打', '二塁打', '三塁打', '本塁打']).sum()
    B = dfff['打撃結果'].isin(['四球']).sum()
    K = dfff['打撃結果'].isin(['見逃し三振', '空振り三振', '振り逃げ', 'K3']).sum()
    R = (
        dfff['打者状況'].isin(['本進']).sum() +
        dfff['一走状況'].isin(['本進']).sum() +
        dfff['二走状況'].isin(['本進']).sum() +
        dfff['三走状況'].isin(['本進']).sum()
    )

    # シーズン成績
    打数 = (
        len(dff[dff['打席の継続'] == '打席完了']) -
        len(dff[dff['打撃結果'].isin(['死球', '四球', '犠打', '犠飛'])]) -
        len(dff[dff['打撃結果2'].isin(['守備妨害', '走塁妨害', '打撃妨害'])])
    )
    安打 = len(dff[dff['打撃結果'].isin(['単打', '二塁打', '三塁打', '本塁打'])])
    OAV = safe_div(安打, 打数)

    dffr = dff[dff['打席左右'] == '右']
    打数R = (
        len(dffr[dffr['打席の継続'] == '打席完了']) -
        len(dffr[dffr['打撃結果'].isin(['死球', '四球', '犠打', '犠飛'])]) -
        len(dffr[dffr['打撃結果2'].isin(['守備妨害', '走塁妨害', '打撃妨害'])])
    )
    安打R = len(dffr[dffr['打撃結果'].isin(['単打', '二塁打', '三塁打', '本塁打'])])
    vsR = safe_div(安打R, 打数R)

    dffl = dff[dff['打席左右'] == '左']
    打数L = (
        len(dffl[dffl['打席の継続'] == '打席完了']) -
        len(dffl[dffl['打撃結果'].isin(['死球', '四球', '犠打', '犠飛'])]) -
        len(dffl[dffl['打撃結果2'].isin(['守備妨害', '走塁妨害', '打撃妨害'])])
    )
    安打L = len(dffl[dffl['打撃結果'].isin(['単打', '二塁打', '三塁打', '本塁打'])])
    vsL = safe_div(安打L, 打数L)

    out_counts = (
        len(dff[dff['打者状況'] == 'アウト']) +
        len(dff[dff['一走状況'].isin(['封殺', '投手牽制死', '捕手牽制死'])]) +
        len(dff[dff['二走状況'].isin(['封殺', '投手牽制死', '捕手牽制死'])]) +
        len(dff[dff['三走状況'].isin(['封殺', '投手牽制死', '捕手牽制死'])])
    )
    Inning = safe_round_div(out_counts, 3)

    WHIP = safe_rate(
        len(dff[dff['打撃結果'].isin(['四球', '死球'])]) + len(dff[dff['打撃結果'].isin(['単打', '二塁打', '三塁打', '本塁打'])]),
        out_counts / 3 if out_counts != 0 else 0
    )

    FIP_scale = 3.1
    HR = len(dff[dff['打撃結果'] == '本塁打'])
    BB = len(dff[dff['打撃結果'].isin(['四球', '死球'])])
    SO = len(dff[dff['打撃結果'].isin(['見逃し三振', '空振り三振', '振り逃げ', 'K3'])])
    FIP = safe_rate(13 * HR + 3 * BB - 2 * SO, out_counts / 3 if out_counts != 0 else 0)
    FIP = round(FIP + FIP_scale, 2) if FIP != '--' else '--'

    # 打者 today / season (打者氏名)
    dfff2 = df[(df['打者氏名'] == 打者氏名) & (df['試合日時'] == 試合日時)]
    dff2 = df[df['打者氏名'] == 打者氏名]

    today2 = ", ".join(dfff2[~dfff2['打席結果'].isin(['0', 0])]['打席結果'].astype(str).tolist())

    打数2 = (
        len(dff2[dff2['打席の継続'] == '打席完了']) -
        len(dff2[dff2['打撃結果'].isin(['死球', '四球', '犠打', '犠飛'])]) -
        len(dff2[dff2['打撃結果2'].isin(['守備妨害', '走塁妨害', '打撃妨害'])])
    )
    安打2 = len(dff2[dff2['打撃結果'].isin(['単打', '二塁打', '三塁打', '本塁打'])])
    season2 = safe_div(安打2, 打数2)

    dff2r = dff2[dff2['投手左右'] == '右']
    打数2r = (
        len(dff2r[dff2r['打席の継続'] == '打席完了']) -
        len(dff2r[dff2r['打撃結果'].isin(['死球', '四球', '犠打', '犠飛'])]) -
        len(dff2r[dff2r['打撃結果2'].isin(['守備妨害', '走塁妨害', '打撃妨害'])])
    )
    安打2r = len(dff2r[dff2r['打撃結果'].isin(['単打', '二塁打', '三塁打', '本塁打'])])
    vsR2 = safe_div(安打2r, 打数2r)

    dff2l = dff2[dff2['投手左右'] == '左']
    打数2l = (
        len(dff2l[dff2l['打席の継続'] == '打席完了']) -
        len(dff2l[dff2l['打撃結果'].isin(['死球', '四球', '犠打', '犠飛'])]) -
        len(dff2l[dff2l['打撃結果2'].isin(['守備妨害', '走塁妨害', '打撃妨害'])])
    )
    安打2l = len(dff2l[dff2l['打撃結果'].isin(['単打', '二塁打', '三塁打', '本塁打'])])
    vsL2 = safe_div(安打2l, 打数2l)

    hr2 = len(dff2[dff2['打撃結果'] == '本塁打'])

    # 次打者
    dfff3 = df[(df['打者氏名'] == 次打者氏名) & (df['試合日時'] == 試合日時)]
    dff3 = df[df['打者氏名'] == 次打者氏名]

    today3 = ", ".join(dfff3[~dfff3['打席結果'].isin(['0', 0])]['打席結果'].astype(str).tolist())

    打数3 = (
        len(dff3[dff3['打席の継続'] == '打席完了']) -
        len(dff3[dff3['打撃結果'].isin(['死球', '四球', '犠打', '犠飛'])]) -
        len(dff3[dff3['打撃結果2'].isin(['守備妨害', '走塁妨害', '打撃妨害'])])
    )
    安打3 = len(dff3[dff3['打撃結果'].isin(['単打', '二塁打', '三塁打', '本塁打'])])
    season3 = safe_div(安打3, 打数3)

    dff3r = dff3[dff3['投手左右'] == '右']
    打数3r = (
        len(dff3r[dff3r['打席の継続'] == '打席完了']) -
        len(dff3r[dff3r['打撃結果'].isin(['死球', '四球', '犠打', '犠飛'])]) -
        len(dff3r[dff3r['打撃結果2'].isin(['守備妨害', '走塁妨害', '打撃妨害'])])
    )
    安打3r = len(dff3r[dff3r['打撃結果'].isin(['単打', '二塁打', '三塁打', '本塁打'])])
    vsR3 = safe_div(安打3r, 打数3r)

    dff3l = dff3[dff3['投手左右'] == '左']
    打数3l = (
        len(dff3l[dff3l['打席の継続'] == '打席完了']) -
        len(dff3l[dff3l['打撃結果'].isin(['死球', '四球', '犠打', '犠飛'])]) -
        len(dff3l[dff3l['打撃結果2'].isin(['守備妨害', '走塁妨害', '打撃妨害'])])
    )
    安打3l = len(dff3l[dff3l['打撃結果'].isin(['単打', '二塁打', '三塁打', '本塁打'])])
    vsL3 = safe_div(安打3l, 打数3l)

    hr3 = len(dff3[dff3['打撃結果'] == '本塁打'])
    
    op_np = len(df[(df['投手氏名'] == 相手投手) & (df['プレイの種類'] == '投球') & (df['試合日時'] == 試合日時)])
    np = len(df[(df['投手氏名'] == 投手氏名) & (df['プレイの種類'] == '投球') & (df['試合日時'] == 試合日時)])

    return [
        投球回, Max, Mean, H, K, B, R,
        OAV, vsR, vsL, Inning, WHIP, FIP,
        today2, season2, vsR2, vsL2, hr2,
        today3, season3, vsR3, vsL3, hr3,
        op_np, np, 打数2, 安打2
    ]












def pt_pct( 投手氏名, df ):
    dff = df[(df['投手氏名'] == 投手氏名) & (df['プレイの種類'] == '投球')]
    counts = dff["球種"].value_counts()
    # ラベル（球種の種類）と値（出現数）をリスト化
    labels = counts.index.tolist()
    values = counts.values.tolist()
    return labels, values


def calc_hekb( df, 先攻チーム, 後攻チーム, 試合日時 ):
    dff = df[(df['試合日時'] == 試合日時) & (df['先攻チーム'] == 先攻チーム) & (df['後攻チーム'] == 後攻チーム)]
    dfft = dff[dff['表.裏'] == '表']
    h_top = len(dfft[dfft['打撃結果'].isin(['単打', '二塁打', '三塁打', '本塁打'])])
    e_bottom = len(dfft[dfft['タイムの種類'].isin([1,2,3,4,5,6,7,8,9])])
    k_top = len(dfft[dfft['打撃結果'].isin(['見逃し三振', '空振り三振', '振り逃げ', 'K3'])])
    b_top = len(dfft[dfft['打撃結果'].isin(['四球', '死球'])])
    
    dffb = dff[dff['表.裏'] == '裏']
    h_bottom = len(dffb[dffb['打撃結果'].isin(['単打', '二塁打', '三塁打', '本塁打'])])
    e_top = len(dffb[dffb['タイムの種類'].isin([1,2,3,4,5,6,7,8,9])])
    k_bottom = len(dffb[dffb['打撃結果'].isin(['見逃し三振', '空振り三振', '振り逃げ', 'K3'])])
    b_bottom = len(dffb[dffb['打撃結果'].isin(['四球', '死球'])])

    return h_top, e_top, k_top, b_top, h_bottom, e_bottom, k_bottom, b_bottom
    
    