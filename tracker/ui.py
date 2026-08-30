"""ウィンドウのレイアウト。ウィジェットを組み立てて属性として公開する。

操作はすべて controller（TrackerApp）のメソッドに委譲し、
このモジュール自体は追跡の状態を持たない。
"""

import tkinter as tk
from tkinter import ttk

from .constants import MODE_BATCH, MODE_SINGLE, SPEED_OPTIONS
from .video_canvas import VideoCanvas
from .widgets import LogView


class MainView:
    """入出力 / プレビュー / 設定 / ログ の4ブロックを並べたメイン画面。"""

    def __init__(self, root, controller, settings, tracker_names):
        self.root = root
        self.controller = controller
        self.settings = settings
        self.status = tk.StringVar(
            value='動画または動画フォルダを選んで「読み込み」を押してください。')

        root.columnconfigure(0, weight=1)
        root.rowconfigure(1, weight=1)

        self._build_io(root)
        self._build_preview(root)
        self._build_options(root, tracker_names)
        self._build_log(root)

    # ------------------------------------------------------------- 入出力
    def _build_io(self, root):
        top = ttk.LabelFrame(root, text='入出力')
        top.grid(row=0, column=0, columnspan=2, sticky='ew', padx=8, pady=(8, 4))
        top.columnconfigure(1, weight=1)

        mode_row = ttk.Frame(top)
        mode_row.grid(row=0, column=0, columnspan=3, sticky='w', padx=6, pady=(6, 0))
        ttk.Radiobutton(mode_row, text='単一動画', variable=self.settings.mode, value=MODE_SINGLE,
                        command=self.controller.on_mode_change).pack(side='left')
        ttk.Radiobutton(mode_row, text='フォルダ一括', variable=self.settings.mode, value=MODE_BATCH,
                        command=self.controller.on_mode_change).pack(side='left', padx=(12, 0))

        ttk.Label(top, text='入力').grid(row=1, column=0, sticky='w', padx=6, pady=4)
        ttk.Entry(top, textvariable=self.settings.input_path).grid(
            row=1, column=1, sticky='ew', pady=4)
        ttk.Button(top, text='参照...', command=self.controller.browse_input).grid(
            row=1, column=2, padx=6, pady=4)

        ttk.Label(top, text='出力先').grid(row=2, column=0, sticky='w', padx=6, pady=4)
        ttk.Entry(top, textvariable=self.settings.output_dir).grid(
            row=2, column=1, sticky='ew', pady=4)
        ttk.Button(top, text='参照...', command=self.controller.browse_output).grid(
            row=2, column=2, padx=6, pady=4)

    # ------------------------------------------------- プレビューと操作ボタン
    def _build_preview(self, root):
        left = ttk.Frame(root)
        left.grid(row=1, column=0, sticky='nsew', padx=(8, 4), pady=4)
        left.rowconfigure(0, weight=1)
        left.columnconfigure(0, weight=1)

        self.canvas = VideoCanvas(left,
                                  on_drag=self.controller.on_roi_drag,
                                  on_select=self.controller.on_roi_select,
                                  on_resize=self.controller.on_canvas_resize)
        self.canvas.grid(row=0, column=0, sticky='nsew')
        self.canvas.line_color = self.settings.line_color

        seek_row = ttk.Frame(left)
        seek_row.grid(row=1, column=0, sticky='ew', pady=(6, 0))
        seek_row.columnconfigure(1, weight=1)
        ttk.Label(seek_row, text='開始フレーム').grid(row=0, column=0, sticky='w')
        self.seek_scale = ttk.Scale(seek_row, from_=0, to=0, orient='horizontal',
                                    command=self.controller.on_seek_move)
        self.seek_scale.grid(row=0, column=1, sticky='ew', padx=6)
        self.seek_scale.bind('<ButtonRelease-1>', self.controller.on_seek_release)
        self.seek_label = ttk.Label(seek_row, text='0 / 0', width=14)
        self.seek_label.grid(row=0, column=2, sticky='e')

        btn_row = ttk.Frame(left)
        btn_row.grid(row=2, column=0, sticky='ew', pady=6)
        self.btn_load = ttk.Button(btn_row, text='読み込み', command=self.controller.load_input)
        self.btn_start = ttk.Button(btn_row, text='一括追跡開始',
                                    command=self.controller.on_start_button)
        self.btn_pause = ttk.Button(btn_row, text='一時停止', command=self.controller.toggle_pause)
        self.btn_reroi = ttk.Button(btn_row, text='ROI再選択', command=self.controller.begin_reroi)
        self.btn_stop = ttk.Button(btn_row, text='中止して保存',
                                   command=self.controller.stop_and_save)
        self.btn_retry = ttk.Button(btn_row, text='やり直し', command=self.controller.retry_video)
        for i, btn in enumerate((self.btn_load, self.btn_start, self.btn_pause,
                                 self.btn_reroi, self.btn_stop, self.btn_retry)):
            btn.grid(row=0, column=i, padx=3, sticky='ew')
            btn_row.columnconfigure(i, weight=1)

        self.progress = ttk.Progressbar(left, mode='determinate')
        self.progress.grid(row=3, column=0, sticky='ew')
        ttk.Label(left, textvariable=self.status, wraplength=700, justify='left').grid(
            row=4, column=0, sticky='w', pady=(4, 0))

    # ---------------------------------------------------------- 右側の設定
    def _build_options(self, root, tracker_names):
        right = ttk.Frame(root)
        right.grid(row=1, column=1, sticky='ns', padx=(4, 8), pady=4)

        self._build_output_box(right)
        self._build_tracking_box(right, tracker_names)
        self._build_move_box(right)
        self._build_queue_box(right)

    def _build_output_box(self, parent):
        box = ttk.LabelFrame(parent, text='出力形式')
        box.pack(fill='x', pady=(0, 6))
        ttk.Checkbutton(box, text='CSV（座標データ）',
                        variable=self.settings.save_csv).pack(anchor='w', padx=6)
        ttk.Checkbutton(box, text='軌跡PNG（全体）',
                        variable=self.settings.save_png).pack(anchor='w', padx=6)
        ttk.Checkbutton(box, text='区間PNG',
                        variable=self.settings.save_interval).pack(anchor='w', padx=6)

        interval_row = ttk.Frame(box)
        interval_row.pack(anchor='w', padx=24, pady=(0, 4))
        ttk.Label(interval_row, text='間隔').pack(side='left')
        ttk.Spinbox(interval_row, from_=1, to=600, width=5,
                    textvariable=self.settings.interval).pack(side='left', padx=4)
        ttk.Label(interval_row, text='秒').pack(side='left')

        ttk.Checkbutton(box, text='追跡動画（mp4）', variable=self.settings.save_video).pack(
            anchor='w', padx=6, pady=(0, 6))

    def _build_tracking_box(self, parent, tracker_names):
        box = ttk.LabelFrame(parent, text='トラッキング')
        box.pack(fill='x', pady=6)
        ttk.Label(box, text='トラッカー').grid(row=0, column=0, sticky='w', padx=6, pady=4)
        ttk.Combobox(box, textvariable=self.settings.tracker_name, values=list(tracker_names),
                     state='readonly', width=12).grid(row=0, column=1, sticky='w', pady=4)

        ttk.Label(box, text='線の太さ').grid(row=1, column=0, sticky='w', padx=6, pady=4)
        ttk.Spinbox(box, from_=1, to=20, width=5, textvariable=self.settings.thickness).grid(
            row=1, column=1, sticky='w', pady=4)

        ttk.Label(box, text='線の色').grid(row=2, column=0, sticky='w', padx=6, pady=4)
        color_row = ttk.Frame(box)
        color_row.grid(row=2, column=1, sticky='w', pady=4)
        self.color_swatch = tk.Label(color_row, width=4, relief='sunken',
                                     background=self.settings.line_hex())
        self.color_swatch.pack(side='left')
        ttk.Button(color_row, text='選択', width=6,
                   command=self.controller.pick_color).pack(side='left', padx=4)

        ttk.Label(box, text='再生速度').grid(row=3, column=0, sticky='w', padx=6, pady=4)
        ttk.Combobox(box, textvariable=self.settings.speed, values=[n for n, _ in SPEED_OPTIONS],
                     state='readonly', width=14).grid(row=3, column=1, sticky='w', pady=(4, 8))

    def _build_move_box(self, parent):
        box = ttk.LabelFrame(parent, text='処理後')
        box.pack(fill='x', pady=6)
        ttk.Checkbutton(box, text='動画を自動移動する', variable=self.settings.move_source).pack(
            anchor='w', padx=6, pady=(4, 0))
        row = ttk.Frame(box)
        row.pack(fill='x', padx=6, pady=4)
        ttk.Entry(row, textvariable=self.settings.move_dir, width=22).pack(
            side='left', fill='x', expand=True)
        ttk.Button(row, text='...', width=3, command=self.controller.browse_move_dir).pack(
            side='left', padx=(4, 0))

    def _build_queue_box(self, parent):
        box = ttk.LabelFrame(parent, text='処理キュー（クリックで読み込み）')
        box.pack(fill='both', expand=True, pady=6)
        self.queue_list = tk.Listbox(box, height=10, width=34, selectmode='browse',
                                     exportselection=False)
        self.queue_list.pack(fill='both', expand=True, padx=6, pady=(6, 0))
        self.queue_list.bind('<<ListboxSelect>>', self.controller.on_queue_select)
        ttk.Checkbutton(box, text='ROI選択後に次の動画へ進む',
                        variable=self.settings.auto_next).pack(anchor='w', padx=6, pady=(2, 6))

    # ----------------------------------------------------------------- ログ
    def _build_log(self, root):
        self.log = LogView(root)
        self.log.grid(row=2, column=0, columnspan=2, sticky='ew', padx=8, pady=(4, 8))

    # ------------------------------------------------------------- 補助操作
    def set_status(self, message):
        self.status.set(message)

    def set_seek_range(self, last_index, value):
        self.seek_scale.configure(to=last_index)
        self.seek_scale.set(value)
        self.seek_label.configure(text=f'{value} / {last_index}')

    def set_seek_label(self, value, last_index):
        self.seek_label.configure(text=f'{value} / {last_index}')

    def set_progress(self, value, maximum=None):
        if maximum is not None:
            self.progress.configure(maximum=maximum)
        self.progress.configure(value=value)
