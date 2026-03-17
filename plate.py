"""
Plate (strike zone) image and click handling.
"""
import base64
import io
import os
from typing import Optional, Tuple

import streamlit as st
import plotly.graph_objects as go
from PIL import Image, ImageDraw


def plate(打席左右: str) -> Tuple[float, float]:
    """Return (x, y) of clicked point on plate image (263 scale)."""
    _base = os.path.join( os.path.dirname( __file__ ), 'assets' )
    if 打席左右 == '右':
        base_image = Image.open( os.path.join( _base, 'Plate_R.png' ) )
    else:
        base_image = Image.open( os.path.join( _base, 'Plate_L.png' ) )

    if 'latest_clicked_point' not in st.session_state or st.session_state.latest_clicked_point is None:
        st.session_state.latest_clicked_point = { 'x': 0, 'y': 0 }
    if 'image_clicker_key_counter' not in st.session_state:
        st.session_state.image_clicker_key_counter = 0

    w, h = base_image.width, base_image.height

    # 現在のクリック点をPILで描画
    image_for_display = base_image.copy()
    draw = ImageDraw.Draw( image_for_display )
    r = 5
    point = st.session_state.latest_clicked_point
    if point and point.get( 'x', 0 ) != 0:
        draw.ellipse(
            ( point['x'] - r, point['y'] - r, point['x'] + r, point['y'] + r ),
            fill="black"
        )

    # PIL画像 → base64
    buf = io.BytesIO()
    image_for_display.save( buf, format='PNG' )
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
        key=f"plate_chart_{st.session_state.image_clicker_key_counter}",
        config={ "displayModeBar": False },
        use_container_width=False,
    )

    if event_data and "selection" in event_data:
        pts = event_data["selection"].get( "points", [] )
        if pts:
            cx = int( pts[0].get( "x", 0 ) )
            cy = int( pts[0].get( "y", 0 ) )
            coords = { "x": cx, "y": cy }
            if coords != st.session_state.latest_clicked_point:
                st.session_state.latest_clicked_point = coords
                st.rerun()

    point = st.session_state.latest_clicked_point
    if point and point.get( 'x', 0 ) != 0:
        return 263 * point['x'] / w, 263 * point['y'] / h
    return 0, 0


def clear_canvas() -> None:
    """Reset plate click state."""
    st.session_state.latest_clicked_point = None
    st.session_state.image_clicker_key_counter = st.session_state.get( 'image_clicker_key_counter', 0 ) + 1
