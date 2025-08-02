

import streamlit as st
from streamlit_image_coordinates import streamlit_image_coordinates
from PIL import ImageDraw, Image


def plate(打席左右):
    if 打席左右 == '右':
        base_image = Image.open('Plate_R.png')
    else:
        base_image = Image.open('Plate_L.png')
        
    # 初期化（もしまだない場合）
    if 'latest_clicked_point' not in st.session_state or st.session_state.latest_clicked_point is None:
        st.session_state.latest_clicked_point = {'x': 0, 'y': 0}

    if 'image_clicker_key_counter' not in st.session_state:
        st.session_state.image_clicker_key_counter = 0

    # 表示用画像のコピーと描画準備
    image_for_display = base_image.copy()
    draw = ImageDraw.Draw(image_for_display)
    r = 5

    # 現在の座標にポイントを描画
    point = st.session_state.latest_clicked_point
    if point and 'x' in point and 'y' in point:
        draw.ellipse(
            (
                point['x'] - r,
                point['y'] - r,
                point['x'] + r,
                point['y'] + r
            ),
            fill="black"
        )

    # 座標取得
    coords = streamlit_image_coordinates(
        image_for_display,
        key=f"image_clicker_{st.session_state.image_clicker_key_counter}"
    )

    # 新しいクリックがあれば更新して再描画
    if coords and coords != st.session_state.latest_clicked_point:
        st.session_state.latest_clicked_point = coords
        st.rerun()

    # 現在のクリック位置を 263スケールに換算して返す
    point = st.session_state.latest_clicked_point
    if point and 'x' in point and 'y' in point:
        x = 263 * point['x'] / 400
        y = 263 * point['y'] / 400
        return x, y
    else:
        return 0, 0




#---
def clear_canvas():
    st.session_state.latest_clicked_point = None
    st.session_state.image_clicker_key_counter += 1
