"""OpenCV のトラッカー生成。"""

import cv2

from .constants import TRACKER_SPECS


def available_trackers():
    """この環境で生成できるトラッカーだけを {表示名: ファクトリ関数} で返す。"""
    trackers = {}
    legacy = getattr(cv2, 'legacy', None)
    for name, attr in TRACKER_SPECS:
        factory = getattr(legacy, attr, None) if legacy is not None else None
        if factory is None:
            factory = getattr(cv2, attr, None)
        if factory is not None:
            trackers[name] = factory
    return trackers


def default_tracker_name(trackers):
    """既定で選ぶトラッカー名（CSRT があればそれ、なければ先頭）。"""
    if not trackers:
        return ''
    return 'CSRT' if 'CSRT' in trackers else next(iter(trackers))
