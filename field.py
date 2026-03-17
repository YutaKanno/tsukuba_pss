"""
Field image and click handling for hit position.
"""
import base64
import io
import os
import uuid

import streamlit as st
import plotly.graph_objects as go
from PIL import Image, ImageDraw, ImageFont


@st.cache_resource
def load_bg_image():
    """Load field background and convert to RGBA for transparency."""
    path = os.path.join( os.path.dirname( __file__ ), "assets", "Field3.png" )
    return Image.open( path ).convert( "RGBA" )


@st.cache_resource
def load_fonts():
    try:
        font_path = os.path.join( os.path.dirname( __file__ ), 'fonts', 'ipaexg.ttf' )
        font = ImageFont.truetype( font_path, 13 )
        font2 = ImageFont.truetype( font_path, 27 )
    except:
        font = ImageFont.load_default()
        font2 = ImageFont.load_default()
    return font, font2


def clear_canvas() -> None:
    """Reset field click state."""
    if 'image_clicker_unique_key' not in st.session_state:
        st.session_state.image_clicker_unique_key = str( uuid.uuid4() )
    st.session_state.latest_point = None
    st.session_state.image_clicker_unique_key = str( uuid.uuid4() )
    st.rerun()


def field( player_list, r_state ):
    if 'image_clicker_unique_key' not in st.session_state:
        st.session_state.image_clicker_unique_key = str( uuid.uuid4() )
    if 'latest_point' not in st.session_state:
        st.session_state.latest_point = { 'x': 0, 'y': 0 }
    if 'latest_clicked_point' not in st.session_state:
        st.session_state.latest_clicked_point = { 'x': 0, 'y': 0 }
    if 'image_key_counter' not in st.session_state:
        st.session_state.image_key_counter = 0

    bg_image = load_bg_image().copy()
    font, font2 = load_fonts()
    draw = ImageDraw.Draw( bg_image )

    # プレイヤー名の描画
    draw.text( ( 230, 215 ), player_list[12], font=font, fill='black' )
    draw.text( ( 130, 215 ), player_list[14], font=font, fill='black' )
    draw.text( ( 250, 265 ), player_list[11], font=font, fill='black' )
    draw.text( ( 100, 265 ), player_list[13], font=font, fill='black' )
    draw.text( ( 185, 365 ), player_list[10], font=font, fill='black' )
    draw.text( ( 185, 105 ), player_list[16], font=font, fill='black' )
    draw.text( ( 90, 155 ),  player_list[15], font=font, fill='black' )
    draw.text( ( 260, 155 ), player_list[17], font=font, fill='black' )

    # ランナーの状態描画
    if r_state[0] == 1:
        draw.text( ( 260, 275 ), '◇', font=font2, fill='red' )
    if r_state[2] == 1:
        draw.text( ( 130, 275 ), '◇', font=font2, fill='red' )
    if r_state[1] == 1:
        draw.text( ( 193, 211 ), '◇', font=font2, fill='red' )

    # 最新のクリック点を描画
    r = 5
    point2 = st.session_state.latest_point
    if point2 and 'x' in point2 and 'y' in point2:
        draw.ellipse(
            ( point2['x'] - r, point2['y'] - r, point2['x'] + r, point2['y'] + r ),
            fill="black"
        )

    w, h = bg_image.width, bg_image.height

    # PIL画像 → base64
    buf = io.BytesIO()
    bg_image.save( buf, format='PNG' )
    img_b64 = 'data:image/png;base64,' + base64.b64encode( buf.getvalue() ).decode()

    # クリック検出用の透明散布点グリッド（5px刻み）
    step = 5
    all_x, all_y = [], []
    for py in range( 0, h + step, step ):
        for px in range( 0, w + step, step ):
            all_x.append( px )
            all_y.append( py )

    fig = go.Figure()

    # 背景画像（y軸反転で上端y=0）
    fig.add_layout_image(
        source=img_b64,
        xref="x", yref="y",
        x=0, y=0,
        sizex=w, sizey=h,
        xanchor="left", yanchor="top",
        sizing="stretch",
        opacity=1,
        layer="below",
    )

    # クリック検出用の透明散布点
    fig.add_trace( go.Scatter(
        x=all_x, y=all_y,
        mode='markers',
        marker=dict( opacity=0, size=8 ),
        showlegend=False,
        hoverinfo='skip',
    ) )

    fig.update_layout(
        width=w, height=h,
        margin=dict( l=0, r=0, t=0, b=0 ),
        xaxis=dict( range=[ 0, w ], showticklabels=False, showgrid=False, zeroline=False, fixedrange=True ),
        yaxis=dict( range=[ h, 0 ], showticklabels=False, showgrid=False, zeroline=False, fixedrange=True ),
        dragmode='select',
        clickmode='event+select',
    )

    event_data = st.plotly_chart(
        fig,
        on_select="rerun",
        key=st.session_state.image_clicker_unique_key,
        config={ "displayModeBar": False },
        use_container_width=False,
    )

    if event_data and "selection" in event_data:
        pts = event_data["selection"].get( "points", [] )
        if pts:
            cx = int( pts[0].get( "x", 0 ) )
            cy = int( pts[0].get( "y", 0 ) )
            coords = { "x": cx, "y": cy }
            if coords != st.session_state.latest_point:
                st.session_state.latest_point = coords
                st.rerun()

    point2 = st.session_state.latest_point
    if point2 and 'x' in point2 and 'y' in point2:
        x = 263 * point2['x'] / w
        y = 263 * point2['y'] / h
        return x, y
    else:
        return 0, 0
