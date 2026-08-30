"""動画1本のキャプチャと追跡状態（GUIに依存しない追跡の中身）。"""

import cv2


class VideoOpenError(Exception):
    """動画を開けなかった / 1フレームも読めなかった。"""


class VideoSession:
    """1本の動画の VideoCapture と、追跡中に貯まる位置・記録をまとめて持つ。"""

    def __init__(self, path):
        cap = cv2.VideoCapture(path)
        ret, frame = cap.read()
        if not ret:
            cap.release()
            raise VideoOpenError(path)

        self.path = path
        self.cap = cap
        self.height, self.width = frame.shape[:2]
        fps = cap.get(cv2.CAP_PROP_FPS)
        self.fps = fps if fps and fps > 0 else 30.0
        self.total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)

        self.current_frame = frame     # 最後に読んだ生フレーム
        self.frame_idx = 0
        self.positions = []            # [(cx, cy) | None, ...]
        self.records = []              # CSVに書き出す行
        self.tracker = None

    # ------------------------------------------------------------ 基本情報
    @property
    def size(self):
        return (self.width, self.height)

    @property
    def last_frame_index(self):
        return max(self.total_frames - 1, 0)

    @property
    def tracked_count(self):
        return sum(1 for point in self.positions if point is not None)

    def describe(self):
        return f'{self.width}x{self.height}, {self.fps:.2f} fps, {self.total_frames} frames'

    # ------------------------------------------------------------ フレーム
    def seek(self, index):
        """index へシークして1フレーム読む。読めなければ None を返す。"""
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, index)
        ret, frame = self.cap.read()
        if not ret:
            return None
        self.current_frame = frame
        return frame

    def read(self):
        """次のフレームを読む。終端なら None。"""
        ret, frame = self.cap.read()
        if not ret:
            return None
        self.current_frame = frame
        return frame

    # -------------------------------------------------------------- 追跡
    def start_tracking(self, tracker, frame, bbox, frame_index):
        """フレーム frame・矩形 bbox からトラッカーを初期化し、記録をリセットする。"""
        self.tracker = tracker
        self.tracker.init(frame, tuple(bbox))
        self.current_frame = frame
        self.frame_idx = frame_index
        self.positions = []
        self.records = []

    def restart_tracking(self, tracker, bbox):
        """ROI再選択：現在のフレームでトラッカーを作り直し、軌跡をそこで区切る。"""
        self.tracker = tracker
        self.tracker.init(self.current_frame, tuple(bbox))
        self.positions.append(None)  # 軌跡の線をここで区切る
        if self.records:
            self.records[-1] = self.records[-1][:8] + ('reinit',)

    def update(self, frame):
        """1フレーム分トラッカーを進め、中心座標と記録を積む。追跡成功なら True。"""
        self.frame_idx += 1
        success, box = self.tracker.update(frame)
        time_sec = self.frame_idx / self.fps
        if success:
            x, y, w, h = [int(v) for v in box]
            cx, cy = x + w // 2, y + h // 2
            self.positions.append((cx, cy))
            self.records.append((self.frame_idx, time_sec, cx, cy, x, y, w, h, 'tracked'))
        else:
            self.positions.append(None)
            self.records.append((self.frame_idx, time_sec, '', '', '', '', '', '', 'lost'))
        return success

    # -------------------------------------------------------------- 後始末
    def release(self):
        self.tracker = None
        if self.cap is not None:
            self.cap.release()
            self.cap = None
