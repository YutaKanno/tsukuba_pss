import streamlit as st
from PIL import Image, ImageDraw, ImageFont
import os
from streamlit_image_coordinates import streamlit_image_coordinates
import uuid # uuidモジュールをインポート


# @st.cache_resource は重いリソースの読み込みに最適
@st.cache_resource
def load_bg_image():
    # RGBAに変換しておくことで、後から描画する要素の透明度を扱える
    return Image.open("Field3.png").convert("RGBA")

@st.cache_resource
def load_fonts():
    try:
        # パスが通っていない可能性があるので、os.path.joinを使うとより堅牢です
        # しかし、ipaexg.ttf が Streamlit アプリのどこに置かれているかによる
        font = ImageFont.truetype('ipaexg.ttf', 13)
        font2 = ImageFont.truetype('ipaexg.ttf', 27)
    except:
        # フォントが見つからない場合のフォールバック
        font = ImageFont.load_default()
        font2 = ImageFont.load_default()
    return font, font2

# clear_canvas 関数を修正
def clear_canvas():
    if 'image_clicker_unique_key' not in st.session_state:
        st.session_state.image_clicker_unique_key = str(uuid.uuid4())

    # 最新のクリック座標をNoneにリセット
    st.session_state.latest_point = None
    # streamlit_image_coordinates のキーを再生成して状態をリセット
    st.session_state.image_clicker_unique_key = str(uuid.uuid4())
    # 画面を再実行して変更を反映
    st.rerun()

def field(player_list, r_state):
    # --- session_state の初期化 ---
    if 'image_clicker_unique_key' not in st.session_state:
        st.session_state.image_clicker_unique_key = str(uuid.uuid4())

    if 'latest_point' not in st.session_state:
        st.session_state.latest_point = {'x': 0, 'y': 0}

    if 'latest_clicked_point' not in st.session_state:
        st.session_state.latest_clicked_point = {'x': 0, 'y': 0}

    if 'image_key_counter' not in st.session_state:
        st.session_state.image_key_counter = 0

    # x, y は現在の座標表示のため、初期値は0,0で良い
    x, y = 0, 0
    # canvas_key は streamlit_drawable_canvas 用なので、今回は直接関係ありません

    # 背景画像の読み込み (cache_resourceを使うので、毎回ロードするわけではない)
    bg_image = load_bg_image().copy() # キャッシュ画像を直接変更しないようにコピー

    # フォントの読み込み (cache_resourceを使う)
    font, font2 = load_fonts()

    # 背景にテキスト・記号を描画
    draw = ImageDraw.Draw(bg_image)
    # プレイヤー名の描画
    draw.text((230, 215), player_list[12], font=font, fill='black') #2B
    draw.text((130, 215), player_list[14], font=font, fill='black') #SS
    draw.text((250, 265), player_list[11], font=font, fill='black') #1B
    draw.text((100, 265), player_list[13], font=font, fill='black') #3B
    draw.text((185, 365), player_list[10], font=font, fill='black') #C
    draw.text((185, 105), player_list[16], font=font, fill='black') #CF
    draw.text((90, 155), player_list[15], font=font, fill='black') #LF
    draw.text((260, 155), player_list[17], font=font, fill='black') #RF

    # ランナーの状態描画
    if r_state[0] == 1: # 1塁
        draw.text((260, 275), '◇', font=font2, fill='red')
    if r_state[2] == 1: # 3塁
        draw.text((130, 275), '◇', font=font2, fill='red')
    if r_state[1] == 1: # 2塁
        draw.text((193, 211), '◇', font=font2, fill='red')
            
    # プロット点の半径
    r = 5

    # 最新のクリック点がある場合のみ描画
    point2 = st.session_state.latest_point
    if point2 and 'x' in point2 and 'y' in point2:
        draw.ellipse(
            (
                point2['x'] - r,
                point2['y'] - r,
                point2['x'] + r,
                point2['y'] + r
            ),
            fill="black"
        )

    # 座標取得 (一意なキーを使用)
    coords = streamlit_image_coordinates(
        bg_image,
        key=st.session_state.image_clicker_unique_key # ここでユニークなキーを使用
    )

    # 新しいクリックがあれば更新して再描画
    # 前回のクリックと同じ座標でなければ処理（無限ループ防止）
    if coords and coords != st.session_state.latest_point:
        st.session_state.latest_point = coords
        st.rerun() # 画面を更新して新しいプロットを表示

    # 現在のクリック位置を 263スケールに換算して返す
    point2 = st.session_state.latest_point
    if point2 and 'x' in point2 and 'y' in point2:
        # 画像サイズ 400x400 を基準に 263スケールに換算
        x = 263 * point2['x'] / bg_image.width
        y = 263 * point2['y'] / bg_image.height
        return x, y
    else:
        # プロットがない場合は0,0を返す
        return 0, 0

# --- (main.py または main_page.py から呼び出す部分) ---
# field 関数が呼び出されるファイル (例: main_page.py) で
# クリアボタンを配置する場合の例

# st.button("プロットをクリア") の設置例 (main_page.py などに記述)
# if st.button("プロットをクリア"):
#     clear_canvas() # clear_canvas 関数を呼び出す

# field 関数からの戻り値の表示例
# 打球位置X, 打球位置Y = field(bottom_names, r_state)
# if 打球位置X == 0 and 打球位置Y == 0:
#     st.write("x=0, y=0 (プロットなし)")
# else:
#     st.write(f"x={打球位置X:.2f}, y={打球位置Y:.2f}")