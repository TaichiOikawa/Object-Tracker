"""軌跡の描画と色の変換。"""

import cv2


def draw_trajectory(canvas, positions, color, thickness):
    """positions の連続する点を線で結ぶ。None は追跡ロスト/ROI再選択の区切り。"""
    prev = None
    for point in positions:
        if point is not None and prev is not None:
            cv2.line(canvas, prev, point, color, thickness)
        prev = point


def overlay_trajectory(frame, positions, color, thickness):
    """フレームに軌跡を重ね、最新の追跡点に丸を打つ（frame を破壊的に描画）。"""
    draw_trajectory(frame, positions, color, thickness)
    for point in reversed(positions):
        if point is not None:
            cv2.circle(frame, point, max(thickness + 2, 4), color, -1)
            break
    return frame


def to_hex(rgb):
    return '#%02x%02x%02x' % tuple(rgb)


def to_bgr(rgb):
    r, g, b = rgb
    return (b, g, r)


def to_bgra(rgb):
    r, g, b = rgb
    return (b, g, r, 255)
