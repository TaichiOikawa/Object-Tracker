"""処理キューの1項目（動画1本）と、フォルダからの動画収集。"""

import os
from dataclasses import dataclass
from typing import Optional, Tuple

from .constants import (STATUS_SELECTED, STATUS_SELECTING, STATUS_WAITING,
                        VIDEO_EXTENSIONS)

BBox = Tuple[int, int, int, int]


@dataclass
class VideoItem:
    """キューに並ぶ動画1本。ROIと開始フレームは選択フェーズで埋まる。"""

    path: str
    status: str = STATUS_WAITING
    bbox: Optional[BBox] = None
    start_frame: int = 0

    @property
    def name(self):
        return os.path.basename(self.path)

    @property
    def is_selected(self):
        return self.status == STATUS_SELECTED

    @property
    def is_pending(self):
        """まだROIを選び終えていない（選択フェーズで拾う対象）。"""
        return self.status in (STATUS_WAITING, STATUS_SELECTING)

    def reset(self):
        self.status = STATUS_WAITING
        self.bbox = None
        self.start_frame = 0

    def select(self, bbox, start_frame):
        self.bbox = bbox
        self.start_frame = start_frame
        self.status = STATUS_SELECTED

    def label(self, current=False):
        marker = '▶ ' if current else '  '
        return f'{marker}{self.name} [{self.status}]'


def find_videos(directory):
    """フォルダ直下の対応拡張子の動画をファイル名順で返す。"""
    return [os.path.join(directory, f) for f in sorted(os.listdir(directory))
            if f.lower().endswith(VIDEO_EXTENSIONS)]


def build_queue(paths):
    return [VideoItem(path=p) for p in paths]
