"""フレーム表示とドラッグによるROI選択を担当するキャンバス。"""

import tkinter as tk

import cv2
from PIL import Image, ImageTk

from .drawing import to_hex

MIN_ROI_SIZE = 5  # これより小さいドラッグは選択とみなさない（px, 動画座標）


class VideoCanvas(tk.Canvas):
    """動画フレームをアスペクト比を保って表示し、ドラッグでROIを選ばせる。

    コールバック:
        on_drag(width, height)  ドラッグ中の大きさ（動画座標）
        on_select(bbox)         ドラッグ確定。小さすぎた場合は None
        on_resize()             キャンバスの大きさが変わった
    """

    def __init__(self, master, on_drag=None, on_select=None, on_resize=None, **kwargs):
        super().__init__(master, bg='#202020', highlightthickness=1,
                         highlightbackground='#555', **kwargs)
        self._on_drag = on_drag
        self._on_select = on_select
        self._on_resize = on_resize

        self.selectable = False           # ROI選択を受け付けるか
        self.line_color = (0, 255, 0)     # RGB

        self._photo = None
        self._frame_size = (1, 1)         # 表示中フレームの (幅, 高さ)
        self._scale = 1.0
        self._offset = (0, 0)
        self._drag_start = None
        self._rect_id = None

        self.bind('<Button-1>', self._on_press)
        self.bind('<B1-Motion>', self._on_motion)
        self.bind('<ButtonRelease-1>', self._on_release)
        self.bind('<Configure>', self._on_configure)

    # -------------------------------------------------------------- 表示
    def show_frame(self, frame):
        """BGRフレームを中央にレターボックス表示する。オーバーレイは消える。"""
        canvas_w = max(self.winfo_width(), 1)
        canvas_h = max(self.winfo_height(), 1)
        if canvas_w < 10 or canvas_h < 10:
            return

        frame_h, frame_w = frame.shape[:2]
        scale = min(canvas_w / frame_w, canvas_h / frame_h)
        disp_w, disp_h = max(int(frame_w * scale), 1), max(int(frame_h * scale), 1)
        offset_x, offset_y = (canvas_w - disp_w) // 2, (canvas_h - disp_h) // 2
        self._frame_size = (frame_w, frame_h)
        self._scale = scale
        self._offset = (offset_x, offset_y)

        rgb = cv2.cvtColor(cv2.resize(frame, (disp_w, disp_h)), cv2.COLOR_BGR2RGB)
        self._photo = ImageTk.PhotoImage(Image.fromarray(rgb))
        self.delete('frame')
        self.create_image(offset_x, offset_y, anchor='nw', image=self._photo, tags='frame')
        self.tag_lower('frame')
        self.clear_overlay()

    def clear_overlay(self):
        self.delete('crosshair')
        if self._rect_id is not None:
            self.delete(self._rect_id)
            self._rect_id = None

    def draw_bbox(self, bbox):
        """確定済みのROIを、現在の表示倍率にあわせて矩形＋十字で描き直す。"""
        if bbox is None:
            return
        x, y, w, h = bbox
        x0, y0 = self.frame_to_canvas(x, y)
        x1, y1 = self.frame_to_canvas(x + w, y + h)
        self.clear_overlay()
        self._rect_id = self.create_rectangle(x0, y0, x1, y1,
                                              outline=to_hex(self.line_color), width=2)
        self._draw_cross(x0, y0, x1, y1)

    def _draw_cross(self, x0, y0, x1, y1):
        """選択した矩形の内側に十字線を引き、中心（＝追跡される点）を示す。"""
        self.delete('crosshair')
        if not self.selectable:
            return

        left, right = min(x0, x1), max(x0, x1)
        top, bottom = min(y0, y1), max(y0, y1)
        cx, cy = (left + right) // 2, (top + bottom) // 2
        color = to_hex(self.line_color)

        self.create_line(left, cy, right, cy, fill=color, dash=(3, 2), tags='crosshair')
        self.create_line(cx, top, cx, bottom, fill=color, dash=(3, 2), tags='crosshair')
        self.create_oval(cx - 1, cy - 1, cx + 1, cy + 1, outline=color, fill=color,
                         tags='crosshair')

    # -------------------------------------------------------------- 座標
    def canvas_to_frame(self, x, y):
        offset_x, offset_y = self._offset
        frame_w, frame_h = self._frame_size
        fx = (x - offset_x) / self._scale
        fy = (y - offset_y) / self._scale
        return (int(min(max(fx, 0), frame_w - 1)), int(min(max(fy, 0), frame_h - 1)))

    def frame_to_canvas(self, x, y):
        offset_x, offset_y = self._offset
        return (int(offset_x + x * self._scale), int(offset_y + y * self._scale))

    # -------------------------------------------------------- イベント処理
    def _on_configure(self, _event):
        if self._on_resize is not None:
            self._on_resize()

    def _on_press(self, event):
        if not self.selectable:
            return
        self._drag_start = (event.x, event.y)
        self.clear_overlay()
        self._rect_id = self.create_rectangle(event.x, event.y, event.x, event.y,
                                              outline=to_hex(self.line_color), width=2)

    def _on_motion(self, event):
        if self._drag_start is None or self._rect_id is None:
            return
        self.coords(self._rect_id, self._drag_start[0], self._drag_start[1], event.x, event.y)
        self._draw_cross(self._drag_start[0], self._drag_start[1], event.x, event.y)
        if self._on_drag is not None:
            x0, y0 = self.canvas_to_frame(*self._drag_start)
            x1, y1 = self.canvas_to_frame(event.x, event.y)
            self._on_drag(abs(x1 - x0), abs(y1 - y0))

    def _on_release(self, event):
        if self._drag_start is None:
            return
        start = self._drag_start
        self._drag_start = None
        x0, y0 = self.canvas_to_frame(*start)
        x1, y1 = self.canvas_to_frame(event.x, event.y)
        x, y = min(x0, x1), min(y0, y1)
        w, h = abs(x1 - x0), abs(y1 - y0)

        if w < MIN_ROI_SIZE or h < MIN_ROI_SIZE:
            self.clear_overlay()
            bbox = None
        else:
            self._draw_cross(start[0], start[1], event.x, event.y)  # 選択後も十字を残す
            bbox = (x, y, w, h)

        if self._on_select is not None:
            self._on_select(bbox)
