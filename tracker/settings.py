"""GUIの設定値（tk変数）をひとまとめにしたもの。"""

import os
import tkinter as tk

from .constants import MODE_BATCH, MODE_SINGLE, SPEED_OPTIONS
from .drawing import to_bgr, to_bgra, to_hex


class AppSettings:
    """入出力・出力形式・トラッキング・処理後の設定。Tkのルート生成後に作ること。"""

    def __init__(self, default_tracker=''):
        self.mode = tk.StringVar(value=MODE_SINGLE)
        self.input_path = tk.StringVar()
        self.output_dir = tk.StringVar(value=os.path.abspath('./tracked_output'))

        self.save_csv = tk.BooleanVar(value=True)
        self.save_png = tk.BooleanVar(value=True)
        self.save_interval = tk.BooleanVar(value=True)
        self.save_video = tk.BooleanVar(value=False)
        self.interval = tk.IntVar(value=10)

        self.tracker_name = tk.StringVar(value=default_tracker)
        self.thickness = tk.IntVar(value=2)
        self.speed = tk.StringVar(value='1x')
        self.line_color = (0, 255, 0)  # RGB

        self.move_source = tk.BooleanVar(value=False)
        self.move_dir = tk.StringVar(value=os.path.abspath('./tracked_movies'))
        self.auto_next = tk.BooleanVar(value=True)

    # ------------------------------------------------------------ 入出力
    @property
    def is_batch(self):
        return self.mode.get() == MODE_BATCH

    @property
    def is_single(self):
        return self.mode.get() == MODE_SINGLE

    def input_value(self):
        return self.input_path.get().strip().strip('"')

    def output_root(self):
        return self.output_dir.get().strip() or '.'

    def move_target(self):
        return self.move_dir.get().strip()

    # -------------------------------------------------------------- 描画
    def line_hex(self):
        return to_hex(self.line_color)

    def line_bgr(self):
        return to_bgr(self.line_color)

    def line_bgra(self):
        return to_bgra(self.line_color)

    def line_thickness(self):
        return self.thickness.get()

    # -------------------------------------------------------------- 処理
    def speed_factor(self):
        """再生速度の倍率。0.0 = 最速（表示あり）、負値 = 最速（表示なし）。"""
        return dict(SPEED_OPTIONS)[self.speed.get()]

    def interval_seconds(self):
        return max(self.interval.get(), 1)
