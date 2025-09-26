import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import plotly.graph_objects as go
import plate
import field
import cal_stats
from datetime import datetime
import io
import warnings

def update_list(list, top_poses, top_names, top_nums, top_lrs, bottom_poses, bottom_names, bottom_nums, bottom_lrs, top_score, bottom_score):

    試合日時 = list[0]
    Season = list[1]
    Kind = list[2]
    Week = list[3]
    Day = list[4]
    GameNumber = list[5]
    主審 = list[6]
    後攻チーム = list[7]
    先攻チーム = list[8]
    プレイの番号 = int(list[9]) + 1
    イニング継続 = list[18]
    試合継続 = list[19]
    開始時刻 = st.session_state['開始時刻']

    現在時刻 = datetime.now().strftime('%H:%M:%S')
    if 開始時刻 in ['', 0]:
        経過時間 = '0:00'
    else:
        経過時間 = datetime.strptime(現在時刻, '%H:%M:%S') - datetime.strptime(開始時刻, '%H:%M:%S')
    
    # 得点数
    先攻得点 = list[12]
    後攻得点 = list[13]
    if list[11] == '表':
        new_score = 先攻得点
    else:
        new_score = 後攻得点
    if list[39] == '本進':
        new_score += 1
    if list[36] == '本進':
        new_score += 1
    if list[37] == '本進':
        new_score += 1
    if list[38] == '本進':
        new_score += 1
    if list[11] == '表':
        先攻得点 = new_score
    else:
        後攻得点 = new_score
        
        
    # アウトカウント + ランナー状況の更新
    new_out = list[16]
    先攻打順 = list[73]
    後攻打順 = list[74]

    捕手 = list[35]
    一走打順 = list[20]
    一走氏名 = list[21]
    二走打順 = list[22]
    二走氏名 = list[23]
    三走打順 = list[24]
    三走氏名 = list[25]
    打順 = list[26]
    打者氏名 = list[27]
    一走状況 = 0
    二走状況 = 0
    三走状況 = 0
            
    if list[39] == 'アウト':
        new_out += 1
    if list[36] in ['封殺', '投手牽制死', '捕手牽制死']:
        new_out += 1
    if list[37] in ['封殺', '投手牽制死', '捕手牽制死']:
        new_out += 1
    if list[38] in ['封殺', '投手牽制死', '捕手牽制死']:
        new_out += 1
    if new_out >= 3: #攻守交替条件
        アウト = 0
        イニング継続 == 'イニング開始'
        一走打順, 一走氏名, 一走状況 = 0,0,0
        二走打順, 二走氏名, 二走状況 = 0,0,0
        三走打順, 三走氏名, 三走状況 = 0,0,0
        S, B = 0, 0
        
        if list[11] == '表':
            回 = list[10]
            表裏 = '裏'
            if 後攻打順 == 9:
                打順 = 1
            else:
                打順 = 後攻打順 + 1
            打者氏名 = bottom_names[後攻打順]
            打席左右 = bottom_lrs[後攻打順]
            if top_score[回-1] == '':
                top_score[回-1] = 0
            # 打席途中で終わった場合
            if list[17] == '打席継続':
                先攻打順 -= 1
                
                
        else:
            回 = list[10] + 1
            表裏 = '表'
            if 先攻打順 == 9:
                打順 = 1
            else:
                打順 = 先攻打順 + 1
            打者氏名 = top_names[先攻打順]
            打席左右 = top_lrs[先攻打順]
            if bottom_score[回-2] == '':
                bottom_score[回-2] = 0
            # 打席途中で終わった場合
            if list[17] == '打席継続':
                後攻打順 -= 1
        
    else:
        回 = list[10]
        表裏 = list[11]
        アウト = new_out
        イニング継続 = 'イニング継続'
        
        if list[17] == '打席継続':
            打順 = list[26]
            打者氏名 = list[27]
            打席左右 = list[28]
        else:
            if list[26] == 9:
                打順 = 1
            else:
                打順 = list[26] + 1
            if 表裏 == '表':
                打者氏名 = top_names[打順-1]
                打席左右 = top_lrs[打順-1]
            else:
                打者氏名 = bottom_names[打順-1]
                打席左右 = bottom_lrs[打順-1]
        
        一走氏名, 一走打順, 二走打順, 二走氏名, 三走打順, 三走氏名 = 0,0,0,0,0,0
        if list[39] == '出塁':
            一走打順 = list[26]
            一走氏名 = list[27]
        elif list[39] == '二進':
            二走打順 = list[26]
            二走氏名 = list[27]
        elif list[39] == '三進':
            三走打順 = list[26]
            三走氏名 = list[27]
            
        if list[36] == '継続':
            一走打順 = list[20]
            一走氏名 = list[21]
        elif list[36] == '二進':
            二走打順 = list[20]
            二走氏名 = list[21]
        elif list[36] == '三進':
            三走打順 = list[20]
            三走氏名 = list[21]
            
        if list[37] == '継続':
            二走打順 = list[22]
            二走氏名 = list[23]
        elif list[37] == '三進':
            三走打順 = list[22]
            三走氏名 = list[23]
        
        if list[38] == '継続':
            三走打順 = list[24]
            三走氏名 = list[25]
    
    
    # ストライクカウントの更新
    if list[17] == '打席完了':
        S = 0
    else:
        if list[45] in ['見逃し', '空振り']:
            S = list[14] + 1
        elif list[45] == 'ファール':
            if list[14] < 2:
                S = list[14] + 1
            else:
                S = list[14]
        else:
            S = list[14]
    
    # ボールカウントの更新
    if list[17] == '打席完了':
        B = 0
    else:
        if list[45] == 'ボール':
            B = list[15] + 1
        else:
            B = list[15]
    
            
    
    
    # 全部更新し終わったあと
    打席の継続 = '打席継続'
    打者状況 = '継続'
    if 表裏 == '表':
        先攻打順 = 打順
        投手氏名 = bottom_names[9]
        投手左右 = bottom_lrs[9]
        投手番号 = list[84][9]
        打者番号 = list[80][打順-1]
        捕手 = bottom_names[10]
        打者位置 = top_poses[打順-1]
    else:
        後攻打順 = 打順
        投手氏名 = top_names[9]
        投手左右 = top_lrs[9]
        投手番号 = list[80][9]
        打者番号 = list[84][打順-1]
        捕手 = top_names[10]
        打者位置 = bottom_poses[打順-1]
        
    if 一走氏名 not in ['0', 0]:
        一走状況 = '継続'
    if 二走氏名 not in ['0', 0]:
        二走状況 = '継続'
    if 三走氏名 not in ['0', 0]:
        三走状況 = '継続'
    
    
    作戦 = 0
    作戦2 = 0
    作戦結果 = 0
    プレイの種類 = '投球'
    構え = 0
    コースX = 0
    コースY = 0
    球種 = '0'
    打撃結果 = '0'
    打撃結果2 = '0'
    捕球選手 = 0
    打球タイプ = '0'
    打球強度 = '0'
    打球位置X = 0
    打球位置Y = 0
    牽制の種類 = '0'
    牽制詳細 = '0'
    エラーの種類 = '0'
    エラー選手 = 0
    球速 = 0
    プレス = '0'
    偽走 = '0'
    打席Id = 0
    打席結果 = '0'
    Result_col = '0'
    打者登録名 = '0'
    一走登録名 = 0
    一走番号 = 0
    二走登録名 = 0
    二走番号 = 0
    三走登録名 = 0
    三走番号 = 0
    
    入力項目 = 0
    経過時間 = 0
    球数 = 0
    開始時刻 = 0
    現在時刻 = 0
    update_list = [試合日時,Season,Kind,Week,Day,GameNumber,主審,後攻チーム,先攻チーム,プレイの番号,回,表裏,先攻得点,後攻得点,S,B,アウト,打席の継続,イニング継続,試合継続,一走打順,一走氏名,二走打順,二走氏名,三走打順,三走氏名,打順,
                   打者氏名,打席左右,作戦,作戦2,作戦結果,投手氏名,投手左右,球数,捕手,一走状況,二走状況,三走状況,打者状況,プレイの種類,構え,コースX,コースY,球種,打撃結果,打撃結果2,捕球選手,打球タイプ,打球強度,打球位置X,打球位置Y,牽制の種類,
                   牽制詳細,エラーの種類,0,球速,プレス,偽走,打者位置,打席Id,打席結果,Result_col,打者登録名,打者番号,一走登録名,一走番号,二走登録名,二走番号,三走登録名,三走番号,投手番号,入力項目,先攻打順,後攻打順,経過時間, 開始時刻, 現在時刻,
                   top_poses, top_names, top_nums, top_lrs, bottom_poses, bottom_names, bottom_nums, bottom_lrs, top_score, bottom_score]
    return update_list
    


















def main_page(list):
    column_names = [
                            "試合日時", "Season", "Kind", "Week", "Day", "GameNumber", "主審", "後攻チーム", "先攻チーム", "プレイの番号", "回", "表.裏", 
                            "先攻得点", "後攻得点", "S", "B", "アウト", "打席の継続", "イニング継続", "試合継続", "一走打順", "一走氏名", "二走打順", 
                            "二走氏名", "三走打順", "三走氏名", "打順", "打者氏名", "打席左右", "作戦", "作戦2", "作戦結果", "投手氏名", "投手左右", 
                            "球数", "捕手", "一走状況", "二走状況", "三走状況", "打者状況", "プレイの種類", "構え", "コースX", "コースY", "球種", 
                            "打撃結果", "打撃結果2", "捕球選手", "打球タイプ", "打球強度", "打球位置X", "打球位置Y", "牽制の種類", "牽制詳細", 
                            "エラーの種類", "タイムの種類", "球速", "プレス", "偽走", "打者位置", "打席Id", "打席結果", "Result_col", "打者登録名", 
                            "打者番号", "一走登録名", "一走番号", "二走登録名", "二走番号", "三走登録名", "三走番号", "投手番号", "入力項目", 
                            "先攻打順", "後攻打順", "経過時間", "開始時刻", "現在時刻",  "top_poses", "top_names", "top_nums", "top_lrs",
                            "bottom_poses", "bottom_names", "bottom_nums", "bottom_lrs",
                            "top_score", "bottom_score"
                        ]
    
    dataframe = pd.DataFrame(st.session_state['all_list'], columns=column_names)
    
    if '開始時刻' not in st.session_state:
        st.session_state['開始時刻'] = list[76]
    if '現在時刻' not in st.session_state:
        st.session_state['現在時刻'] = list[77]
    if '経過時間' not in st.session_state:
        st.session_state['経過時間'] = list[75]



    コメント = ''
    top_poses, top_names, top_nums, top_lrs, bottom_poses, bottom_names, bottom_nums, bottom_lrs = list[78:86]
    top_score, bottom_score = list[86], list[87]
    
    updated_list = update_list(list, top_poses, top_names, top_nums, top_lrs, bottom_poses, bottom_names, bottom_nums, bottom_lrs, top_score, bottom_score)
    top_score, bottom_score = updated_list[86], updated_list[87]
    

    if 'data_list' not in st.session_state:
        st.session_state['data_list'] = updated_list
    current_list = st.session_state['data_list']
    
    
    

    試合日時, Season, Kind, Week, Day, GameNumber = current_list[0:6]
    主審, 後攻チーム, 先攻チーム, プレイの番号, 回, 表裏 = current_list[6:12]
    先攻得点, 後攻得点, S, B, アウト, 打席の継続 = current_list[12:18]
    イニング継続, 試合継続, 一走打順, 一走氏名, 二走打順, 二走氏名 = current_list[18:24]
    三走打順, 三走氏名, 打順, 打者氏名, 打席左右, 作戦 = current_list[24:30]
    作戦2, 作戦結果, 投手氏名, 投手左右, 球数, 捕手 = current_list[30:36]
    一走状況, 二走状況, 三走状況, 打者状況, プレイの種類, 構え = current_list[36:42]
    コースX, コースY, 球種, 打撃結果, 打撃結果2, 捕球選手 = current_list[42:48]
    打球タイプ, 打球強度, 打球位置X, 打球位置Y = current_list[48:52]
    牽制の種類, 牽制詳細, エラーの種類, エラー選手 = 0,0,0,0
    球速, プレス, 偽走, 打者位置, 打席Id, 打席結果 = current_list[56:62]
    Result_col, 打者登録名, 打者番号, 一走登録名, 一走番号 = current_list[62:67]
    二走登録名, 二走番号, 三走登録名, 三走番号, 投手番号 = current_list[67:72]
    入力項目, 先攻打順, 後攻打順, 経過時間, 開始時刻, 現在時刻 = current_list[72:78]
    
    
    
    r0_state, r1_state, r2_state, r3_state = '継続' ,current_list[36], current_list[37], current_list[38]
    
    if S == 0:
        s_count = '〇〇'
    elif S == 1:
        s_count = '●〇'
    elif S == 2:
        s_count = '●●'
    if B == 0:
        b_count = '〇〇〇'
    elif B == 1:
        b_count = '●〇〇'
    elif B == 2:
        b_count = '●●〇'
    elif B == 3:
        b_count = '●●●'
    if アウト == 0:
        o_count = '〇〇'
    elif アウト == 1:
        o_count = '●〇'
    elif アウト == 2:
        o_count = '●●'
        
    
    
    st.session_state['エラー選手'] = 0    
        
    
        
        
    
    
    if "already_rerun" not in st.session_state:
        st.session_state["already_rerun"] = False

    if 表裏 == '表':
        offence_initial = 先攻チーム[0]
        if 打順 == 9:
            next_batter = top_names[0]
        else:
            next_batter = top_names[打順]
        opponent_p = top_names[9]
        投手氏名 = bottom_names[9]
        投手左右 = bottom_lrs[9]
        投手番号 = bottom_nums[9]
        打者氏名 = top_names[打順-1]
        打席左右 = top_lrs[打順-1]
        打者番号 = top_nums[打順-1]
        if 一走状況 not in ['0', 0]:
            一走氏名 = top_names[一走打順-1]
        if 二走状況 not in ['0', 0]:
            二走氏名 = top_names[二走打順-1]
        if 三走状況 not in ['0', 0]:
            三走氏名 = top_names[三走打順-1]
    else:
        offence_initial = 後攻チーム[0]
        if 打順 == 9:
            next_batter = bottom_names[0]
        else:
            next_batter = bottom_names[打順]
        opponent_p = bottom_names[9]
        投手氏名 = top_names[9]
        投手左右 = top_lrs[9]
        投手番号 = top_nums[9]
        打者氏名 = bottom_names[打順-1]
        打席左右 = bottom_lrs[打順-1]
        打者番号 = bottom_nums[打順-1]
        if 一走状況 not in ['0', 0]:
            一走氏名 = bottom_names[一走打順-1]
        if 二走状況 not in ['0', 0]:
            二走氏名 = bottom_names[二走打順-1]
        if 三走状況 not in ['0', 0]:
            三走氏名 = bottom_names[三走打順-1]
    stats = cal_stats.cal_stats(dataframe, 投手氏名, opponent_p, 打者氏名, next_batter, 試合日時)
    球数 = stats[24]+1

    if not st.session_state["already_rerun"]:
        st.session_state["already_rerun"] = True 
        st.rerun()
    
    
    
    
    
    
    
    
    
    
    
    
    
        
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    tab2, tab1, tab3 = st.tabs(['メニュー', 'データ入力', 'データ一覧'])
    with tab3:
        st.dataframe(dataframe.astype(str))

        
    with tab1:
        container = st.container()
        with container:
            col1, col2 = st.columns(2)
            with col1:
                col31, col32 = st.columns([1,5])
                with col31:
                    warnings.filterwarnings("ignore")
                    # 球種の出現数を取得
                    labels, values = cal_stats.pt_pct(投手氏名, dataframe)

                    # カラーパレットを定義
                    palette = {
                        "ストレート": "#FF3333",
                        "ツーシーム": "#FF9933",
                        "スライダー": "#6666FF",
                        "カット": "#9933FF",
                        "カーブ": "#66B2FF",
                        "チェンジ": "#00CC66",
                        "フォーク": "#009900",
                        "シンカー": "#CC00CC",
                        "シュート": "#FF66B2",
                        "特殊球": "#000000"
                    }

                    # 球種ラベルに対応する色を取得
                    colors = [palette.get(label, "#CCCCCC") for label in labels]  # 未定義の球種には灰色を指定

                    # 円グラフを作成
                    fig = go.Figure(data=[go.Pie(
                        labels=labels,
                        values=values,
                        showlegend=False,
                        textinfo='none',
                        marker=dict(colors=colors),
                        hole=0  # ドーナツ型ではない
                    )])

                    # レイアウトを指定してサイズと余白を制御
                    fig.update_layout(
                        margin=dict(l=0, r=0, t=0, b=0),
                        height=70,
                        width=50,
                        showlegend=False
                    )

                    # domainでサイズをさらに調整
                    fig.update_traces(
                        domain=dict(x=[0, 1], y=[0, 1])
                    )

                    # Streamlitで表示
                    # Streamlitで表示
                    st.plotly_chart(
                        fig,
                        config={"displayModeBar": False},  # 表示設定（例: ツールバー非表示）
                        use_container_width=False
                    )



                with col32:
                    html = f"""
                    <style>
                    table.custom {{
                        border-collapse: collapse;
                        width: 100%;
                        text-align: center;
                        font-size: 14px;
                        padding: 0px;
                    }}
                    table.custom th, table.custom td {{
                        border: 1px solid #ccc;
                        padding: 5px 10px; /* セル内のパディングを調整 */
                        height: 25px; /* セルの高さを調整 */
                        line-height: 1.2; /* テキストの行間を調整 */
                    }}
                    .circle {{
                        text-align: left;
                    }}
                    .green {{ color: #b6e3b6; }}
                    .red {{ color: #FF6666; }}
                    .yellow {{ color: #FFCC33; }}
                    </style>

                    <table class="custom">
                    <tr>
                        <th>日付</th><td colspan="2">{試合日時}</td>
                        <th>時刻</th><td colspan="3">{st.session_state['経過時間']}</td>
                        <td class="green"><b>B</b></td>
                        <td class="green circle">{b_count}</td>
                    </tr>
                    <tr>
                        <th>投手</th>
                        <td>球数</td>
                        <td>{球数-1}</td>
                        <th>打者</th>
                        <td colspan="3">.{stats[14]} ({stats[25]}-{stats[26]})</td>
                        <td class="yellow"><b>S</b></td>
                        <td class="yellow circle">{s_count}</td>
                    </tr>
                    <tr>
                        <td>{投手氏名}</td>
                        <td>{投手左右}</td>
                        <td>#{投手番号}</td>
                        <td>{打順}</td>
                        <td>{打者氏名}</td>
                        <td>{打席左右}</td>
                        <td>#{打者番号}</td>
                        <td class="red"><b>O</b></td>
                        <td class="red circle">{o_count}</td>
                    </tr>
                    </table>
                    """
                    st.markdown(html, unsafe_allow_html=True)













                ## 第２段
                # 5列のボタン
                col11, col12, col13 = st.columns([1, 4, 1])
                options = ['--', '3高', '3中', '3低', '中高', '中中', '中低', '1高', '1中', '1低']
                if "radio_selection" not in st.session_state:
                    st.session_state.radio_selection = options[0]

                if "reset_flag" not in st.session_state:
                    st.session_state.reset_flag = False

                if "pickoff_selection" not in st.session_state:
                    st.session_state.pickoff_selection = '0'  # 牽制の選択状態を初期化

                # ボタン押下フラグが立っていたらradioをリセット（描画前）
                if st.session_state.reset_flag:
                    st.session_state.radio_selection = options[0]
                    st.session_state.pickoff_selection = '0'  # 牽制の選択状態もリセット
                    st.session_state.reset_flag = False  # フラグを戻す

                with col11:
                    aim = st.radio('構え', options, key="radio_selection")
                    st.session_state['構え_aim'] = aim

                    if aim == '3高':
                        構え = st.radio('', [7, 6, 1, 2], label_visibility='collapsed', key='stance_3ba')
                    elif aim == '3中':
                        構え = st.radio('', [12, 11], label_visibility='collapsed', key='stance_3bb')
                    elif aim == '3低':
                        構え = st.radio('', [17, 16, 21, 22], label_visibility='collapsed', key='stance_3bc')
                    elif aim == '中高':
                        構え = st.radio('', [8, 3], label_visibility='collapsed', key='stance_2ba')
                    elif aim == '中中':
                        構え = st.radio('', [13], label_visibility='collapsed', key='stance_2bb')
                    elif aim == '中低':
                        構え = st.radio('', [18, 23], label_visibility='collapsed', key='stance_2bc')
                    elif aim == '1高':
                        構え = st.radio('', [9, 10, 4, 5], label_visibility='collapsed', key='stance_1ba')
                    elif aim == '1中':
                        構え = st.radio('', [14, 15], label_visibility='collapsed', key='stance_1bb')
                    elif aim == '1低':
                        構え = st.radio('', [19, 20, 24, 25], label_visibility='collapsed', key='stance_1bc')
                    else:
                        構え = 0
                    st.session_state['構え'] = 構え  # 構えの最終的な選択状態を保存
                with col12:
                    コースX, コースY = plate.plate(打席左右)
                    
                
                    
                with col13:
                    if st.button('Tag'):
                        st.session_state['現在時刻'] = datetime.now().strftime('%H:%M:%S')
                        現在時刻 = datetime.now().strftime('%H:%M:%S')
                        if st.session_state['開始時刻'] in ['', 0]:
                            st.session_state['経過時間'] = '0:00'
                        else:
                            st.session_state['経過時間'] = datetime.strptime(st.session_state['現在時刻'], '%H:%M:%S') - datetime.strptime(st.session_state['開始時刻'], '%H:%M:%S')
                        st.success(st.session_state['経過時間'])
                        
                    st.write(f'{コースX}-{コースY}')
                    r_state = [0, 0, 0]
                    pickoff = ['0']
                    if 一走氏名 not in ['0', 0]:
                        r_state[0] = 1
                        pickoff.append('一塁牽制')
                    if 二走氏名 not in ['0', 0]:
                        r_state[1] = 1
                        pickoff.append('二塁牽制')
                    if 三走氏名 not in ['0', 0]:
                        r_state[2] = 1
                        pickoff.append('三塁牽制')
                    牽制の種類 = st.radio('牽制', pickoff, key="pickoff_selection")  # keyを追加
                    if 牽制の種類 != '0':
                        プレイの種類 = '牽制'
                        牽制詳細 = st.radio('結果', ['セーフ', 'アウト', '牽制エラー'])
                        打者状況 = '継続'
                        if 牽制詳細 == 'アウト':
                            if 牽制の種類 == '一塁牽制':
                                r1_state = '投手牽制死'
                            elif 牽制の種類 == '二塁牽制':
                                r2_state = '投手牽制死'
                            elif 牽制の種類 == '三塁牽制':
                                r3_state = '投手牽制死'
                        elif 牽制詳細 == '牽制エラー':
                            エラーの種類 = '牽制エラー'
                            if 一走氏名 not in ['0', 0]:
                                r1_state = '二進'
                            if 二走氏名 not in ['0', 0]:
                                r2_state = '三進'
                            if 三走氏名 not in ['0', 0]:
                                r3_state = '本進'
                        elif 牽制詳細 == 'セーフ':
                            if 牽制の種類 == '一塁牽制':
                                r1_state = '継続'
                            elif 牽制の種類 == '二塁牽制':
                                r2_state = '継続'
                            elif 牽制の種類 == '三塁牽制':
                                r3_state = '継続'
                            
                        
                
                
                
                
                
                
                        

                ## 第3段
                if st.session_state.get('構え', 0) not in  ['0', 0]:
                    pt_lists = ['0','FB', 'CB', 'SL', 'CT', 'ST', '2S', 'CH', 'SP', 'SK', 'OT']
                    pts = st.radio('球種', pt_lists, index=0, horizontal=True, key='pitch_type', label_visibility='collapsed')
                    if pts == 'FB':
                        球種 = 'ストレート'
                    elif pts == 'CB':
                        球種 = 'カーブ'
                    elif pts == 'SL':
                        球種 = 'スライダー'
                    elif pts == 'CT':
                        球種 = 'カット'
                    elif pts == 'ST':
                        球種 = 'シュート'
                    elif pts == '2S':
                        球種 = 'ツーシーム'
                    elif pts == 'CH':
                        球種 = 'チェンジ'
                    elif pts == 'SP':
                        球種 = 'フォーク'
                    elif pts == 'SK':
                        球種 = 'シンカー'
                    elif pts == 'OT':
                        球種 = '特殊球'
                else:
                    col31, col32 = st.columns(2)
                    with col31:
                        
                        
                        card_style = """
                        <style>
                        .card-container {
                            display: flex;
                            gap: 16px;
                            margin-top: 10px;
                            flex-wrap: wrap;
                        }
                        .card {
                            flex: 1;
                            background-color: #ffffff;
                            padding: 10px 14px;
                            border-radius: 10px;
                            box-shadow: 0 1px 6px rgba(0,0,0,0.08);
                            font-family: 'Arial', sans-serif;
                            min-width: 300px;
                            max-width: 500px;
                        }
                        .card h4 {
                            margin-bottom: 6px;
                            font-size: 17px;
                            color: #222;
                            border-bottom: 1px solid #ddd;
                            padding-bottom: 2px;
                        }
                        .card .grid {
                            display: grid;
                            grid-template-columns: repeat(3, 1fr);
                            gap: 2px 6px;
                            font-size: 13px;
                            color: #333;
                            margin-bottom: 4px;
                        }
                        .card .grid-4col {
                            display: grid;
                            grid-template-columns: repeat(4, 1fr);
                            gap: 2px 6px;
                            font-size: 13px;
                            color: #333;
                            margin-bottom: 4px;
                        }
                        .card .label {
                            color: #666;
                        }
                        .card .value {
                            font-weight: bold;
                            color: #000;
                        }
                        .card .section-title {
                            margin: 6px 0 2px;
                            font-size: 13px;
                            font-weight: bold;
                            color: #444;
                            border-bottom: 1px dashed #ccc;
                        }
                        </style>
                        """

                        html = f"""
                        <div class="card-container">
                            <div class="card">
                                <h4>
                                    P. {投手氏名} 
                                    <span style="font-size: 12px; color: #555;">vs.({offence_initial}) {opponent_p}: {stats[23]}球</span>
                                </h4>
                                <div class="value"></div>
                                <div class="grid">
                                    <div class="label">Inning</div><div class="label">Max</div><div class="label">Ave</div>
                                    <div class="value">{stats[0]}</div><div class="value">{stats[1]}</div><div class="value">{stats[2]}</div>
                                </div>
                                <div class="grid-4col">
                                    <div class="label">H</div><div class="label">K</div><div class="label">B</div><div class="label">R</div>
                                    <div class="value">{stats[3]}</div><div class="value">{stats[4]}</div><div class="value">{stats[5]}</div><div class="value">{stats[6]}</div>
                                </div>
                                <div class="section-title"></div>
                                <div class="grid">
                                    <div class="label">OAV</div><div class="label">vsR</div><div class="label">vsL</div>
                                    <div class="value">.{stats[7]}</div><div class="value">.{stats[8]}</div><div class="value">.{stats[9]}</div>
                                    <div class="label">Inning</div><div class="label">WHIP</div><div class="label">FIP</div>
                                    <div class="value">{stats[10]}</div><div class="value">{stats[11]}</div><div class="value">{stats[12]}</div>
                                </div>
                            </div>
                        </div>
                        """

                        st.markdown(card_style + html, unsafe_allow_html=True)
                    
                    
                    
                    with col32:


                        card_style = """
                        <style>
                        .card-container {
                            display: flex;
                            gap: 16px;
                            margin-top: 10px;
                            flex-wrap: wrap;
                        }
                        .card {
                            flex: 1;
                            background-color: #ffffff;
                            padding: 10px 14px;
                            border-radius: 10px;
                            box-shadow: 0 1px 6px rgba(0,0,0,0.08);
                            font-family: 'Arial', sans-serif;
                            min-width: 300px;
                            max-width: 500px;
                        }
                        .card h4 {
                            margin-bottom: 6px;
                            font-size: 17px;
                            color: #222;
                            border-bottom: 1px solid #ddd;
                            padding-bottom: 2px;
                        }
                        .card .grid {
                            display: grid;
                            grid-template-columns: repeat(3, 1fr);
                            gap: 2px 6px;
                            font-size: 13px;
                            color: #333;
                            margin-bottom: 4px;
                        }
                        .card .grid-2col {
                            display: grid;
                            grid-template-columns: 1fr 3fr;
                            gap: 2px 6px;
                            font-size: 13px;
                            color: #333;
                            margin-bottom: 4px;
                        }
                        .card .grid-4col {
                            display: grid;
                            grid-template-columns: repeat(4, 1fr);
                            gap: 2px 6px;
                            font-size: 13px;
                            color: #333;
                            margin-bottom: 4px;
                        }
                        .card .grid-6col {
                            display: grid;
                            grid-template-columns: repeat(6, 1fr);
                            gap: 2px 6px;
                            font-size: 13px;
                            color: #333;
                            margin-bottom: 4px;
                        }
                        .card .label {
                            color: #666;
                        }
                        .card .value {
                            font-weight: bold;
                            color: #000;
                        }
                        .card .section-title {
                            margin: 6px 0 2px;
                            font-size: 13px;
                            font-weight: bold;
                            color: #444;
                            border-bottom: 1px dashed #ccc;
                        }
                        </style>
                        """

                        html = f"""
                        <div class="card-container">
                            <div class="card">
                                <h4>{打順}. {打者氏名}</h4>
                                <div class="grid-2col">
                                    <div class="label">Today:</div>
                                    <div class="value">{stats[13]}</div>
                                </div>
                                <div class="grid-6col">
                                    <div class="label">Season:</div>
                                    <div class="value">.{stats[14]}</div>
                                    <div class="label">vsR:</div>
                                    <div class="value">.{stats[15]}</div>
                                    <div class="label">vsL:</div>
                                    <div class="value">.{stats[16]}</div>
                                </div>
                                <div class="grid-6col">
                                    <div class="label">HR:</div>
                                    <div class="value">{stats[17]}</div>
                                    <div class="label"></div>
                                    <div class="value"></div>
                                    <div class="label"></div>
                                    <div class="value"></div>
                                </div>
                                <div class="grid-2col">
                                    <div class="label"></div>
                                </div>
                                <h4>next. {next_batter}</h4>
                                <div class="grid-2col">
                                    <div class="label">Today:</div>
                                    <div class="value">{stats[18]}</div>
                                </div>
                                <div class="grid-6col">
                                    <div class="label">Season:</div>
                                    <div class="value">.{stats[19]}</div>
                                    <div class="label">vsR:</div>
                                    <div class="value">.{stats[20]}</div>
                                    <div class="label">vsL:</div>
                                    <div class="value">.{stats[21]}</div>
                                </div>
                                <div class="grid-6col">
                                    <div class="label">HR:</div>
                                    <div class="value">{stats[22]}</div>
                                    <div class="label"></div>
                                    <div class="value"></div>
                                    <div class="label"></div>
                                    <div class="value"></div>
                                </div>
                                </div>
                            </div>
                        </div>
                        """

                        st.markdown(card_style + html, unsafe_allow_html=True)







                
                
                ## 第4段
                col01, col02, col03, col04, col05 = st.columns(5)
                result_ctg = 'continue'
                if 球種 != '0':
                    with col01:
                        result_ctg = st.radio('打撃結果', ['continue', 'K', 'BB', 'outs', 'hits', 'miss', 'sacrifice'], key='result_ctg')

                        打撃結果 = '0'
                        if result_ctg == 'continue':
                            with col02:
                                打撃結果 = st.radio('入力してください', ['0', '見逃し', '空振り', 'ファール', 'ボール'], key='batting_result_cont')
                                if 打撃結果 in ['見逃し', '空振り'] and S == 2:
                                    打撃結果 = '見逃し三振'
                                elif 打撃結果 == 'ボール' and B == 3:
                                    打撃結果 = '四球'
                                    
                        elif result_ctg == 'K':
                            with col02:
                                打撃結果 = st.radio('入力してください', ['0', '見逃し三振', '空振り三振', '振り逃げ', 'K3'], key='batting_result_k')
                        elif result_ctg == 'BB':
                            with col02:
                                打撃結果 = st.radio('入力してください', ['0', '四球', '死球'], key='batting_result_bb')
                        elif result_ctg == 'outs':
                            with col02:
                                打撃結果 = st.radio('入力してください', ['0', '凡打死', '凡打出塁', 'ファールフライ'], key='batting_result_out')
                        elif result_ctg == 'hits':
                            with col02:
                                打撃結果 = st.radio('入力してください', ['0', '単打', '二塁打', '三塁打', '本塁打'], key='batting_result_hit')
                        elif result_ctg == 'miss':
                            with col02:
                                打撃結果 = st.radio('入力してください', ['0', 'エラー', '野手選択', '犠打失策'], key='batting_result_miss')
                        elif result_ctg == 'sacrifice':
                            with col02:
                                打撃結果 = st.radio('入力してください', ['0', '犠打', '犠飛', '犠打失策'], key='batting_result_sac')
                        st.session_state['打撃結果'] = 打撃結果

                    打撃結果2 = '0'
                    if st.session_state.get('打撃結果', '0') != '0':
                        with col03:
                            打撃結果2 = st.radio('その他の項目', ['0', 'PB', 'WP', '守備妨害', '打撃妨害', '走塁妨害', 'ボーク'], key='other_result')

                        プレス = '0'
                        with col04:
                            プレス = st.radio('プレス', ['0', '3プレス', '1プレス', '両プレス'], key='press')

                        
                        with col05:
                            牽制の種類 = st.radio('捕手牽制', ['0', '1塁牽制', '2塁牽制', '3塁牽制'], key='catcher_pickoff')


                # R状況の処理
                if result_ctg == 'continue' and st.session_state['打撃結果'] not in ['見逃し三振', '空振り三振', '四球']:
                    打席の継続 = '打席継続'
                else:
                    打席の継続 = '打席完了'
                    if st.session_state.get('打撃結果') in ['見逃し三振', '空振り三振', 'K3', '凡打死', 'ファールフライ']:
                        r0_state = 'アウト'
                    elif st.session_state.get('打撃結果') in ['犠打', '野手選択', 'エラー', '振り逃げ', '単打', '凡打出塁', '犠打失策']:
                        if st.session_state.get('打撃結果') == '犠打':
                            r0_state = 'アウト'
                        else:
                            r0_state = '出塁'
                        if r1_state not in ['0', 0]:
                            r1_state = '二進'
                        if r2_state not in ['0', 0]:
                            r2_state = '三進'
                        if r3_state not in ['0', 0]:
                            r3_state = '本進'
                    elif st.session_state.get('打撃結果') in ['四球', '死球']:
                        r0_state = '出塁'
                        if r1_state not in ['0', 0]:
                            r1_state = '二進'
                            if r2_state not in ['0', 0]:
                                r2_state = '三進'
                                if r3_state not in ['0', 0]:
                                    r3_state = '本進'
                            
                    elif st.session_state.get('打撃結果') == '犠飛':
                        r0_state = 'アウト'
                        if r3_state not in ['0', 0]:
                            r3_state = '本進'
                    elif st.session_state.get('打撃結果') == '二塁打':
                        r0_state = '二進'
                        if r1_state not in ['0', 0]:
                            r1_state = '三進'
                        if r2_state not in ['0', 0]:
                            r2_state = '本進'
                        if r3_state not in ['0', 0]:
                            r3_state = '本進'
                    elif st.session_state.get('打撃結果') == '三塁打':
                        r0_state = '三進'
                        if r1_state not in ['0', 0]:
                            r1_state = '三進'
                        if r2_state not in ['0', 0]:
                            r2_state = '本進'
                        if r3_state not in ['0', 0]:
                            r3_state = '本進'
                    elif st.session_state.get('打撃結果') == '本塁打':
                        r0_state = '本進'
                        if r1_state not in ['0', 0]:
                            r1_state = '本進'
                        if r2_state not in ['0', 0]:
                            r2_state = '本進'
                        if r3_state not in ['0', 0]:
                            r3_state = '本進'
                    
                if 打撃結果2 in ['PB', 'WP']:
                    if r1_state not in ['0', 0]:
                        r1_state = '二進'
                    if r2_state not in ['0', 0]:
                        r2_state = '三進'
                    if r3_state not in ['0', 0]:
                        r3_state = '本進'
                elif 打撃結果2 == 'ボーク':
                    if r1_state not in ['0', 0]:
                        r1_state = '二進'
                    if r2_state not in ['0', 0]:
                        r2_state = '三進'
                    if r3_state not in ['0', 0]:
                        r3_state = '本進'
                    プレイの種類 = 'ボーク'


            with col2:
                h_top, e_top, k_top, b_top, h_bottom, e_bottom, k_bottom, b_bottom = cal_stats.calc_hekb(dataframe, 先攻チーム, 後攻チーム, 試合日時)

                top_score[12:16] = [h_top, e_top, k_top, b_top]
                bottom_score[12:16] = [h_bottom, e_bottom, k_bottom, b_bottom]

                scores = {
                    'team': [先攻チーム, 後攻チーム],
                    '1': [top_score[0], bottom_score[0]],
                    '2': [top_score[1], bottom_score[1]],
                    '3': [top_score[2], bottom_score[2]],
                    '4': [top_score[3], bottom_score[3]],
                    '5': [top_score[4], bottom_score[4]],
                    '6': [top_score[5], bottom_score[5]],
                    '7': [top_score[6], bottom_score[6]],
                    '8': [top_score[7], bottom_score[7]],
                    '9': [top_score[8], bottom_score[8]],
                    '10': [top_score[9], bottom_score[9]],
                    '11': [top_score[10], bottom_score[10]],
                    '12': [top_score[11], bottom_score[11]],
                    'R': [先攻得点, 後攻得点],
                    'H': [top_score[12], bottom_score[12]],
                    'E': [top_score[13], bottom_score[13]],
                    'K': [top_score[14], bottom_score[14]],
                    'B': [top_score[15], bottom_score[15]]
                }
                df = pd.DataFrame(scores)

                # HTML生成
                header_html = ''.join([f'<th>{col}</th>' for col in df.columns])
                rows_html = ''
                for i in range(len(df)):
                    row = df.iloc[i]
                    row_html = ''.join([f'<td>{cell}</td>' for cell in row])
                    rows_html += f'<tr>{row_html}</tr>'

                html = f"""
                <style>
                table.custom {{
                    border-collapse: collapse;
                    width: 100%;
                    text-align: center;
                    font-size: 12px;
                }}
                table.custom th, table.custom td {{
                    border: 1px solid #ccc;
                    padding: 4px 6px;
                }}
                </style>
                <table class="custom">
                    <tr>{header_html}</tr>
                    {rows_html}
                </table>
                """

                st.markdown(html, unsafe_allow_html=True)

                ## 第２段
                col61, col62, col64, col63 = st.columns([3,12, 2,2])
                with col61:
                    if aim != '--' or プレイの種類 == '牽制':
                        if 牽制詳細 == '牽制エラー':
                            error_player_0, error_player_1 = 1, 0
                        else:
                            error_player_0, error_player_1 = 0, 1
                            
                        エラー選手 = st.selectbox('エラー選手', [error_player_0, error_player_1, 2, 3, 4, 5, 6, 7, 8, 9], key='error_player')
                        打者状況 = st.selectbox(f'{打順}:{打者氏名}', [r0_state , '継続', '二進', '三進', '本進', '封殺', '投手牽制死', '捕手牽制死'], key='runner_0_state')
                        if 一走氏名 not in ['0', 0]:
                            一走状況_options = [r1_state , '継続', '二進', '三進', '本進', '封殺', '投手牽制死', '捕手牽制死'] if r1_state not in ['0',0] else ['0']
                            一走状況 = st.selectbox(f'1R:{一走氏名}', 一走状況_options, key='runner_1_state')
                        if 二走氏名 not in ['0', 0]:    
                            二走状況_options = [r2_state , '継続', '三進', '本進', '封殺', '投手牽制死', '捕手牽制死'] if r2_state not in ['0',0] else ['0']
                            二走状況 = st.selectbox(f'2R:{二走氏名}', 二走状況_options, key='runner_2_state')
                        if 三走氏名 not in ['0', 0]:
                            三走状況_options = [r3_state , '継続', '本進', '封殺', '投手牽制死', '捕手牽制死'] if r3_state not in ['0',0] else ['0']
                            三走状況 = st.selectbox(f'3R{三走氏名}', 三走状況_options, key='runner_3_state')

                hits = 0
                打球強度 = 0
                
                if result_ctg not in ['continue', 'K', 'BB']:
                    with col63:
                        hits = st.radio('打球', [0, 'G', 'L', 'F'], key='ball_type')
                        打球強度 = st.radio('強度', [0, 'A', 'B', 'C'], key='ball_speed')
                    with col64:
                        捕球選手 = st.radio('捕球', range(1, 10))

                elif 打撃結果 == 'ファール':
                    with col63:
                        hits = st.radio('打球', [0, 'G', 'L', 'F'], key='ball_type')
                else:
                    with col63:
                        st.write("")
                        
                if hits == 'G':
                    打球タイプ = 'ゴロ'
                elif hits == 'L':
                    打球タイプ = 'ライナー'
                elif hits == 'F':
                    打球タイプ = 'フライ'
                else:
                    打球タイプ = '0'
                        
    
                with col62:
                    if 表裏 == '裏':
                        打球位置X, 打球位置Y = field.field(top_names, r_state)
                    else:
                        打球位置X, 打球位置Y = field.field(bottom_names, r_state)
                
                if result_ctg in ['continue', 'K', 'BB'] and 打撃結果 != 'ファール':
                    打球位置X, 打球位置Y = 0, 0
                
                with col63:
                    st.write(f'{打球位置X}-{打球位置Y}')
                        

                球速 = 0
                作戦2 = 0
                col21, col22, col23, col24, col25 =  st.columns([1,1,2,4,4])
                if 打撃結果 not in ['0', 0]:
                    with st.container():
                        with col21:
                            first_number = st.radio('十の位', range(10), label_visibility='collapsed', key='first_num')
                        with col22:
                            second_number = st.radio('一の位', range(10), label_visibility='collapsed', key='second_num')
                        try:
                            potential_speed = int(f'{first_number}{second_number}')
                            if potential_speed >= 65:
                                球速 = potential_speed
                            elif potential_speed == 0:
                                球速 = 0
                            else:
                                球速 = int(f'1{first_number}{second_number}')
                        except ValueError:
                            球速 = 0 # エラーハンドリング
                        st.session_state['球速'] = 球速
                        


                        with col23:
                            st.write(f'**球速: {st.session_state.get("球速", 0)}km/h**')
                            作戦 = st.radio('作戦', ['0' ,'盗塁', 'バント', 'エンドラン'], key='strategy')
                        if 作戦 == '盗塁':
                            with col24:
                                作戦2 = st.radio('作戦2', ['盗塁', 'ディレード', 'Wスチール'], key='strategy2_steal')
                                作戦結果 = st.radio('作戦結果', ['0', '成功', '失敗', '盗塁成功'], key='strategy_result_steal')
                        elif 作戦 == 'バント':
                            with col24:
                                作戦2 = st.radio('作戦2', ['バント', '打からバント構え', 'セフティ', 'スクイズ', 'バスター', 'Sスクイズ'], key='strategy2_bunt')
                                作戦結果 = st.radio('作戦結果', ['0', '成功', '失敗'], key='strategy_result_bunt')
                        elif 作戦 == 'エンドラン':
                            with col24:
                                作戦2 = st.radio('作戦2', ['HAR', 'RAH', 'BAR', 'BSAR'], key='strategy2_endrun')
                                作戦結果 = st.radio('作戦結果', ['0', '成功', '失敗', '盗塁成功'], key='strategy_result_endrun')
                        else:
                            作戦2 = '0'
                            作戦結果 = '0'

                    with col25:
                        if エラー選手 not in ['0', 0]:
                            エラーの種類 = st.radio('エラーの種類', ['処理E', '送球E', '捕球E', 'その他'])




                # 打席結果の定義
                if 打席の継続 == '打席完了':
                    if 打撃結果 == '見逃し三振':
                        打席結果 = '見三振'
                    elif 打撃結果 == '空振り三振':
                        打席結果 = '空三振'
                    elif 打撃結果 == '振り逃げ':
                        打席結果 = '振逃'
                    elif 打撃結果 == 'ファールフライ':
                        打席結果 = '邪飛'
                    elif 打撃結果 in ['凡打死', '凡打出塁']:
                        打席結果 = f'{捕球選手}{打球タイプ}'
                    else:
                        打席結果 = 打撃結果









                if st.session_state.get('打撃結果', '0') != '0' or 牽制の種類 not in ['0', 0]:
                    with col25:
                        button_css = f"""
                        <style>
                        div.stButton > button:first-child  {{
                            font-weight  : bold        ;/* 文字：太字              */
                            border      :  5px solid '#ff9999'    ;/* 枠線：ピンク色で5ピクセルの実線 */
                            border-radius: 10px 10px 10px 10px ;/* 枠線：半径10ピクセルの角丸       */
                            background   : #ddd        ;/* 背景色：薄いグレー            */
                            font-size    : 50px        }}
                        </style>
                        """
                        st.markdown(button_css, unsafe_allow_html=True)
                        if st.button('.　　　確定　　　.', key='confirm_button'):
                            
                            if 打撃結果 == 'エラー' and エラー選手 == 0 and プレイの種類 == '投球':
                                st.warning('エラー選手が未入力')
                            if 構え in ['0', 0] and プレイの種類 == '投球':
                                st.warning('構えが未入力')
                            elif コースX == 0 and コースY == 0 and プレイの種類 == '投球':
                                st.warning('コースが未入力')
                            elif 球種 in ['0', 0] and プレイの種類 == '投球':
                                st.warning('球種が未入力')
                            elif 打撃結果 in ['0', 0] and プレイの種類 == '投球':
                                st.warning('打撃結果が未入力')
                            elif (result_ctg not in ['continue', 'K', 'BB'] or 打撃結果 == 'ファール') and (打球位置X == 0 and 打球位置Y == 0) and プレイの種類 == '投球':
                                st.warning('打球位置が未入力')
                            elif (result_ctg not in ['continue', 'K', 'BB']) and (捕球選手 == 0) and プレイの種類 == '投球':
                                st.warning('捕球選手が未入力')
                            elif (result_ctg not in ['continue', 'K', 'BB'] or 打撃結果 == 'ファール') and (打球タイプ in ['0', 0]) and プレイの種類 == '投球':
                                st.warning('打球タイプが未入力')
                            else:
                        
                                inputed_list = [
                                    試合日時, Season, Kind, Week, Day, GameNumber,
                                    主審, 後攻チーム, 先攻チーム, プレイの番号, 回, 表裏,
                                    先攻得点, 後攻得点, S, B, アウト, 打席の継続, イニング継続, 試合継続,
                                    一走打順, 一走氏名, 二走打順, 二走氏名, 三走打順, 三走氏名, 打順, 打者氏名, 打席左右, 作戦,
                                    作戦2, 作戦結果, 投手氏名, 投手左右, 球数, 捕手,
                                    一走状況, 二走状況, 三走状況, 打者状況, プレイの種類, 構え,
                                    コースX, コースY, 球種, 打撃結果, 打撃結果2, 捕球選手,
                                    打球タイプ, 打球強度, 打球位置X, 打球位置Y, 牽制の種類, 牽制詳細, エラーの種類, エラー選手,
                                    球速, プレス, 偽走, 打者位置, コメント, 打席結果,
                                    Result_col, 打者登録名, 打者番号, 一走登録名, 一走番号, 二走登録名, 二走番号, 三走登録名, 三走番号, 投手番号,
                                    入力項目, 先攻打順, 後攻打順, st.session_state['経過時間'], st.session_state['開始時刻'], st.session_state['現在時刻'],
                                    top_poses, top_names, top_nums, top_lrs, bottom_poses, bottom_names, bottom_nums, bottom_lrs,
                                    top_score, bottom_score
                                    ]
                                
                                
                                st.session_state['all_list'].append(inputed_list)
                                
                                dataframe = pd.DataFrame(st.session_state['all_list'], columns=column_names)
                                
                                st.session_state['現在時刻'] = datetime.now().strftime('%H:%M:%S')
                                print(開始時刻)
                                if 開始時刻 in ['']:
                                    st.session_state['経過時間'] = '0:00'
                                else:
                                    st.session_state['経過時間'] = datetime.strptime(st.session_state['現在時刻'], '%H:%M:%S') - datetime.strptime(st.session_state['開始時刻'], '%H:%M:%S')
                                
                                
                                


                                
                                
                                
                                scoring_runners = [打者状況, 一走状況, 二走状況, 三走状況]
                                得点 = scoring_runners.count('本進')

                                if 表裏 == '表':
                                    先攻得点 += 得点
                                    if top_score[回-1] == '':
                                        if 得点 > 0:
                                            top_score[回-1] = 得点
                                    else:
                                        top_score[回-1] += 得点
                                        
                                    if 打撃結果 in ['単打', '二塁打', '三塁打', '本塁打']:
                                        top_score[12] +=1
                                    if エラー選手 not in [0, '0']:
                                        bottom_score[13] +=1
                                    if 打撃結果 in ['見逃し三振', '空振り三振', '振り逃げ', 'K3']:
                                        top_score[14] += 1
                                    if 打撃結果 == '四球':
                                        top_score[15] += 1

                                else:
                                    後攻得点 += 得点
                                    if bottom_score[回-1] == '':
                                        if 得点 > 0:
                                            bottom_score[回-1] = 得点
                                    else:
                                        bottom_score[回-1] += 得点
                                    
                                    if 打撃結果 in ['単打', '二塁打', '三塁打', '本塁打']:
                                        bottom_score[12] +=1
                                    if エラー選手 not in [0, '0']:
                                        top_score[13] +=1
                                    if 打撃結果 in ['見逃し三振', '空振り三振', '振り逃げ', 'K3']:
                                        bottom_score[14] += 1
                                    if 打撃結果 == '四球':
                                        bottom_score[15] += 1
                                
                                
                                updated_list = update_list(inputed_list, top_poses, top_names, top_nums, top_lrs, bottom_poses, bottom_names, bottom_nums, bottom_lrs, top_score, bottom_score)
                                
                                st.session_state['data_list'] = updated_list
                                
                                st.session_state['打撃結果'], st.session_state['エラー選手'], エラー選手 = '0', 0, 0 
                                st.session_state.reset_flag = True
                                r0_state, r1_state, r2_state, r3_state = '継続', updated_list[36], updated_list[37], updated_list[38]
                                
                                plate.clear_canvas()
                                field.clear_canvas()
                                st.rerun() # 画面を再表示
        
    with tab2:
        st.write('## 試合開始')
        st.success(f"試合開始: {st.session_state['開始時刻']}")
        if st.button('試合開始'):
            st.session_state['開始時刻'] = datetime.now().strftime('%H:%M:%S')
            st.success(f"試合開始: {st.session_state['開始時刻']}")
        st.write('---')
        st.markdown(f"## 設定")
        if st.button('1つ削除して戻る'):
            if st.session_state['all_list']:
                
                last_entry = st.session_state['all_list'].pop()

                表裏 = last_entry[11] 
                回 = last_entry[12]  
                打者状況 = last_entry[13]
                一走状況 = last_entry[14]
                二走状況 = last_entry[15]
                三走状況 = last_entry[16]
                打撃結果 = last_entry[17]
                エラー選手 = last_entry[21]  


                # 得点計算と減算処理
                scoring_runners = [打者状況, 一走状況, 二走状況, 三走状況]
                得点 = scoring_runners.count('本進')

                if 表裏 == '表':
                    先攻得点 += 得点

                    if top_score[回 - 1] == '':
                        if 得点 > 0:
                            top_score[回 - 1] = 得点
                    else:
                        top_score[回 - 1] += 得点

                    if 打撃結果 in ['単打', '二塁打', '三塁打', '本塁打']:
                        top_score[12] += 1
                    if エラー選手 not in [0, '0']:
                        bottom_score[13] += 1
                    if 打撃結果 in ['見逃し三振', '空振り三振', '振り逃げ', 'K3']:
                        top_score[14] += 1
                    if 打撃結果 == '四球':
                        top_score[15] += 1

                else:
                    後攻得点 += 得点

                    if bottom_score[回 - 1] == '':
                        if 得点 > 0:
                            bottom_score[回 - 1] = 得点
                    else:
                        bottom_score[回 - 1] += 得点

                    if 打撃結果 in ['単打', '二塁打', '三塁打', '本塁打']:
                        bottom_score[12] += 1
                    if エラー選手 not in [0, '0']:
                        top_score[13] += 1
                    if 打撃結果 in ['見逃し三振', '空振り三振', '振り逃げ', 'K3']:
                        bottom_score[14] += 1
                    if 打撃結果 == '四球':
                        bottom_score[15] += 1


                # 一覧を再更新
                updated_list = update_list(
                    st.session_state['all_list'][-1],
                    top_poses, top_names, top_nums, top_lrs,
                    bottom_poses, bottom_names, bottom_nums, bottom_lrs,
                    top_score,
                    bottom_score
                )

                # 状態更新
                st.session_state['data_list'] = updated_list
                st.session_state.reset_flag = True

                # キャンバスをクリアして再表示
                plate.clear_canvas()
                field.clear_canvas()
                st.rerun()

        if st.button('選手交代'):
            st.session_state.page_ctg = 'member'
            
        csv_str = dataframe.to_csv(index=False)
        
        # バイト列に変換（UTF-8ならそのままOK、Shift-JISで保存したいならencode指定）
        csv_bytes = csv_str.encode('cp932')
        
        # バッファに乗せる
        csv_buffer = io.BytesIO(csv_bytes)

        # ダウンロードボタン（バイナリデータ使用）
        st.download_button(
            label="データ保存",
            data=csv_buffer,
            file_name="game_data.csv",
            mime="text/csv",
            help="ゲームデータをCSVで保存"
        )
        
        st.write('---')
        st.write('画面の一部が表示されない場合:')
        if st.button('ここをクリック'):
            st.rerun()
        
        st.write('---')
        st.write('## 状況変更')
        change_回 = st.selectbox('イニング変更', [回, 1,2,3,4,5,6,7,8,9,10,11,12])
        change_表裏 = st.selectbox('表裏変更', [表裏, '表', '裏'])
        change_先攻得点 = st.text_input('先攻得点変更', 先攻得点)
        change_後攻得点 = st.text_input('後攻得点変更', 後攻得点)
        change_S = st.selectbox('S変更', [S, 0, 1, 2])
        change_B = st.selectbox('B変更', [B, 0, 1, 2, 3])
        change_アウト = st.selectbox('O変更', [アウト, 0, 1, 2])
        change_打順 = st.selectbox('打順変更', [打順, 1, 2, 3, 4, 5, 6, 7, 8, 9])
        change_一走打順 = st.selectbox('一走変更', [一走打順, 0, 1, 2, 3, 4, 5, 6, 7, 8, 9])
        change_二走打順 = st.selectbox('二走変更', [二走打順, 0, 1, 2, 3, 4, 5, 6, 7, 8, 9])
        change_三走打順 = st.selectbox('三走変更', [三走打順, 0, 1, 2, 3, 4, 5, 6, 7, 8, 9])
        # 変更確定ボタンが押されたとき
        if st.button('変更確定'):
            # 初期確認：data_list が存在するか、ない場合はエラー表示
            if 'data_list' in st.session_state:
                current_data2 = st.session_state['data_list'].copy()
                
                # 型変換（文字列を整数に直すなど）
                try:
                    change_先攻得点 = int(change_先攻得点)
                    change_後攻得点 = int(change_後攻得点)
                except ValueError:
                    st.error('得点は数字で入力してください')
                    st.stop()

                # 対象インデックスを正確に更新
                current_data2[10] = change_回
                current_data2[11] = change_表裏
                current_data2[12] = change_先攻得点
                current_data2[13] = change_後攻得点
                current_data2[14] = change_S
                current_data2[15] = change_B
                current_data2[16] = change_アウト

                current_data2[20] = change_一走打順
                current_data2[22] = change_二走打順
                current_data2[24] = change_三走打順
                current_data2[26] = change_打順
                
            
                if change_一走打順 != 0:
                    current_data2[36] = '継続'
                    if change_表裏 == '表':
                        current_data2[21] = top_names[change_一走打順-1]
                    else:
                        current_data2[21] = bottom_names[change_一走打順-1]
                else:
                    current_data2[36] = '0'
                    current_data2[21] = '0'
                    
                if change_二走打順 != 0:
                    current_data2[37] = '継続'
                    if change_表裏 == '表':
                        current_data2[23] = top_names[change_二走打順-1]
                    else:
                        current_data2[23] = bottom_names[change_二走打順-1]
                else:
                    current_data2[37] = '0'
                    current_data2[23] = '0'
                    
                    
                if change_三走打順 != 0:
                    current_data2[38] = '継続'
                    if change_表裏 == '表':
                        current_data2[25] = top_names[change_三走打順-1]
                    else:
                        current_data2[25] = bottom_names[change_三走打順-1]
                else:
                    current_data2[38] = '0'
                    current_data2[25] = '0'
                    

                # update_list() 関数を適用して、最新状態に変換
                updated_list_ = update_list(
                    current_data2, top_poses, top_names, top_nums, top_lrs,
                    bottom_poses, bottom_names, bottom_nums, bottom_lrs,
                    top_score, bottom_score
                )
                
                
                # 更新反映
                st.session_state['data_list'] = updated_list_
            
                st.success('変更を反映しました')
                st.rerun()
            else:
                st.warning('まだプレイが入力されていません')

            


        return st.session_state['data_list']





