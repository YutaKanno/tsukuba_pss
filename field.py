"""
Field image and click handling for hit position (PIL + streamlit_image_coordinates).
"""
import os
from typing import Tuple

import streamlit as st
from PIL import Image, ImageDraw, ImageFont
from streamlit_image_coordinates import streamlit_image_coordinates


@st.cache_resource
def load_bg_image() -> Image.Image:
    """Load field background and convert to RGBA for transparency."""
    path = os.path.join( os.path.dirname( __file__ ), "assets", "Field3.png" )
    return Image.open( path ).convert( "RGBA" )


@st.cache_resource
def load_fonts() -> tuple[ImageFont.FreeTypeFont, ImageFont.FreeTypeFont]:
    try:
        font_path = os.path.join( os.path.dirname( __file__ ), "fonts", "ipaexg.ttf" )
        font = ImageFont.truetype( font_path, 13 )
        font2 = ImageFont.truetype( font_path, 27 )
    except Exception:
        font = ImageFont.load_default()
        font2 = ImageFont.load_default()
    return font, font2


def clear_canvas() -> None:
    """Reset field click state."""
    if "field_latest_point" in st.session_state:
        st.session_state.field_latest_point = None
    if "field_image_key_counter" not in st.session_state:
        st.session_state.field_image_key_counter = 0
    st.session_state.field_image_key_counter += 1
    st.rerun()


def field( player_list, r_state ) -> Tuple[float, float]:
    """Render field image and return (x, y) in 263-scale coordinates."""
    if "field_latest_point" not in st.session_state:
        st.session_state.field_latest_point = { "x": 0, "y": 0 }
    if "field_image_key_counter" not in st.session_state:
        st.session_state.field_image_key_counter = 0

    base_image = load_bg_image()
    image_for_display = base_image.copy()
    font, font2 = load_fonts()
    draw = ImageDraw.Draw( image_for_display )

    # プレイヤー名の描画
    draw.text( ( 230, 215 ), player_list[ 12 ], font = font, fill = "black" )
    draw.text( ( 130, 215 ), player_list[ 14 ], font = font, fill = "black" )
    draw.text( ( 250, 265 ), player_list[ 11 ], font = font, fill = "black" )
    draw.text( ( 100, 265 ), player_list[ 13 ], font = font, fill = "black" )
    draw.text( ( 185, 365 ), player_list[ 10 ], font = font, fill = "black" )
    draw.text( ( 185, 105 ), player_list[ 16 ], font = font, fill = "black" )
    draw.text( ( 90, 155 ), player_list[ 15 ], font = font, fill = "black" )
    draw.text( ( 260, 155 ), player_list[ 17 ], font = font, fill = "black" )

    # ランナーの状態描画
    if r_state[ 0 ] == 1:
        draw.text( ( 260, 275 ), "◇", font = font2, fill = "red" )
    if r_state[ 2 ] == 1:
        draw.text( ( 130, 275 ), "◇", font = font2, fill = "red" )
    if r_state[ 1 ] == 1:
        draw.text( ( 193, 211 ), "◇", font = font2, fill = "red" )

    # 最新のクリック点を描画
    r = 6
    point = st.session_state.field_latest_point
    if point and "x" in point and "y" in point:
        draw.ellipse(
            (
                point[ "x" ] - r,
                point[ "y" ] - r,
                point[ "x" ] + r,
                point[ "y" ] + r,
            ),
            fill = "black",
        )

    # 画像クリックコンポーネントで座標取得（plate.py と同様のパターン）
    coords = streamlit_image_coordinates(
        image_for_display,
        key = f"field_image_{st.session_state.field_image_key_counter}",
    )

    if coords and coords != st.session_state.field_latest_point:
        st.session_state.field_latest_point = coords
        st.rerun()

    point = st.session_state.field_latest_point
    w, h = base_image.width, base_image.height
    if point and "x" in point and "y" in point:
        x = 263 * point[ "x" ] / w
        y = 263 * point[ "y" ] / h
        return x, y
    return 0.0, 0.0
