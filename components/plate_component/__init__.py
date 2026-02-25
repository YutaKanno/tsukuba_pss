"""
ストライクゾーン用カスタムコンポーネント。
クリック座標は「確定」押下時のみ Python に返し、クリックのたびの rerun を防ぐ。
"""
import os
import base64
import streamlit.components.v1 as components

_RELEASE = True
_component_path = os.path.join(os.path.dirname(__file__), "frontend", "build")

if not _RELEASE or not os.path.exists(os.path.join(_component_path, "index.html")):
    _component_path = os.path.join(os.path.dirname(__file__), "frontend", "dist")

if not os.path.exists(os.path.join(_component_path, "index.html")):
    _component_func = None
else:
    _component_func = components.declare_component("plate_component", path=_component_path)


def plate_component(image_base64, key=None):
    """
    Args:
        image_base64: 表示するプレート画像の base64 文字列（data URL の本体でも可）
        key: Streamlit のユニークキー
    Returns:
        {"x": int, "y": int} または None（未確定時）
        座標は画像上のピクセル。263スケール換算は呼び出し側で行う。
    """
    if _component_func is None:
        return None
    return _component_func(image_base64=image_base64, key=key)


def plate_component_available():
    return _component_func is not None
