"""アプリ全体で共有する定数。"""

VIDEO_EXTENSIONS = ('.mp4', '.avi', '.mov', '.mkv')

# (表示名, cv2 のファクトリ関数名)。環境によって使えないものがあるので trackers.py で選別する。
TRACKER_SPECS = [
    ('CSRT', 'TrackerCSRT_create'),
    ('KCF', 'TrackerKCF_create'),
    ('MOSSE', 'TrackerMOSSE_create'),
    ('MIL', 'TrackerMIL_create'),
    ('MedianFlow', 'TrackerMedianFlow_create'),
    ('Boosting', 'TrackerBoosting_create'),
    ('TLD', 'TrackerTLD_create'),
]

# 表示なしモードで1回のコールバックあたりに処理するフレーム数
FAST_BATCH = 25

# (表示名, 速度倍率)。0.0 = 最速（表示あり）、負値 = 最速（表示なし）
SPEED_OPTIONS = [
    ('0.5x', 0.5),
    ('1x', 1.0),
    ('2x', 2.0),
    ('最速（表示あり）', 0.0),
    ('最速（表示なし）', -1.0),
]

CSV_HEADER = ['frame', 'time_sec', 'center_x', 'center_y',
              'bbox_x', 'bbox_y', 'bbox_w', 'bbox_h', 'status']

# 動画1本の状態（キュー一覧にそのまま表示される）
STATUS_WAITING = '待機'
STATUS_SELECTING = '選択中'
STATUS_SELECTED = '選択済み'
STATUS_TRACKING = '追跡中'
STATUS_LOAD_FAILED = '読込失敗'
STATUS_DONE = '完了'
STATUS_ABORTED = '中止'

# アプリのフェーズ
PHASE_IDLE = 'idle'
PHASE_ROI = 'roi'
PHASE_RUNNING = 'running'
PHASE_PAUSED = 'paused'
PHASE_REROI = 'reroi'

MODE_SINGLE = 'single'
MODE_BATCH = 'batch'
