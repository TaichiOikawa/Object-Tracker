"""Tkinter GUI for object tracking (single video / batch directory).

映像を Tkinter Canvas に埋め込み、ドラッグでROIを選んで追跡する。
    - 単一動画モード / フォルダ一括モード
    - 一時停止・再開・中止・やり直し・ROI再選択・再生速度の変更
    - CSV / 軌跡PNG / 区間PNG / 追跡動画 の出力

操作は2フェーズ制:
    Phase 1  キューの動画を順にROI選択（選び終わった動画は [選択済み]）
    Phase 2  「一括追跡開始」で選択済みの動画をまとめて処理
キューの項目をクリックすればその動画をいつでも読み込み直して選択をやり直せる。
"""

import os
import tkinter as tk
from tkinter import colorchooser, filedialog, messagebox

from .constants import (FAST_BATCH, PHASE_IDLE, PHASE_PAUSED, PHASE_REROI,
                        PHASE_ROI, PHASE_RUNNING, STATUS_ABORTED, STATUS_DONE,
                        STATUS_LOAD_FAILED, STATUS_SELECTING, STATUS_TRACKING)
from .drawing import overlay_trajectory
from .exporters import (ensure_output_dir, move_video, open_video_writer,
                        write_csv, write_interval_pngs, write_trajectory_png)
from .queue_model import build_queue, find_videos
from .session import VideoOpenError, VideoSession
from .settings import AppSettings
from .trackers import available_trackers, default_tracker_name
from .ui import MainView


class TrackerApp(tk.Tk):
    """画面と追跡処理をつなぐコントローラ。"""

    def __init__(self):
        super().__init__()
        self.title('Object Tracker')
        self.geometry('1180x780')
        self.minsize(960, 680)

        self.ready = False
        self.trackers = available_trackers()
        if not self.trackers:
            messagebox.showerror('Error', 'OpenCVに利用可能なトラッカーがありません。')
            self.destroy()
            return

        # --- 実行時の状態 ---
        self.phase = PHASE_IDLE
        self.queue = []                    # [VideoItem, ...]
        self.queue_index = -1
        self.suppress_queue_event = False  # 一覧の再描画で選択イベントが跳ね返るのを防ぐ
        self.session = None                # 読み込み中の VideoSession
        self.writer = None                 # 追跡動画の VideoWriter
        self.bbox = None                   # 選択中/追跡中のROI
        self.start_frame = 0
        self.after_id = None

        self.settings = AppSettings(default_tracker_name(self.trackers))
        self.view = MainView(self, self, self.settings, self.trackers)
        self.canvas = self.view.canvas

        self._update_buttons()
        self.protocol('WM_DELETE_WINDOW', self.on_close)
        self.ready = True

    # -------------------------------------------------------------- 小道具
    def log(self, message):
        self.view.log.append(message)

    def set_status(self, message):
        self.view.set_status(message)

    @property
    def current_item(self):
        if 0 <= self.queue_index < len(self.queue):
            return self.queue[self.queue_index]
        return None

    @property
    def selected_count(self):
        return sum(1 for item in self.queue if item.is_selected)

    def _update_buttons(self):
        view = self.view

        def enable(button, condition):
            button.configure(state='normal' if condition else 'disabled')

        loaded = self.session is not None
        selected = self.selected_count
        enable(view.btn_load, self.phase in (PHASE_IDLE, PHASE_ROI))
        if self.phase == PHASE_REROI:
            enable(view.btn_start, self.bbox is not None)
            view.btn_start.configure(text='選択したROIで再開')
        else:
            enable(view.btn_start, self.phase in (PHASE_IDLE, PHASE_ROI) and selected > 0)
            view.btn_start.configure(
                text=f'一括追跡開始（{selected}本）' if selected else '一括追跡開始')
        enable(view.btn_pause, self.phase in (PHASE_RUNNING, PHASE_PAUSED))
        enable(view.btn_reroi, self.phase in (PHASE_PAUSED, PHASE_REROI))
        enable(view.btn_stop, self.phase in (PHASE_RUNNING, PHASE_PAUSED, PHASE_REROI))
        enable(view.btn_retry, loaded and self.phase != PHASE_RUNNING)
        view.btn_pause.configure(
            text='再開' if self.phase in (PHASE_PAUSED, PHASE_REROI) else '一時停止')
        view.seek_scale.configure(state='normal' if self.phase == PHASE_ROI else 'disabled')
        self.canvas.selectable = self.phase in (PHASE_ROI, PHASE_REROI)

    # ------------------------------------------------------------ 入出力選択
    def on_mode_change(self):
        self.settings.input_path.set('')
        self.queue = []
        self.queue_index = -1
        self._refresh_queue_list()
        self._update_buttons()

    def browse_input(self):
        if self.settings.is_single:
            path = filedialog.askopenfilename(
                title='動画ファイルを選択',
                filetypes=[('Video', '*.mp4 *.avi *.mov *.mkv'), ('All files', '*.*')])
        else:
            path = filedialog.askdirectory(title='動画フォルダを選択')
        if path:
            self.settings.input_path.set(path)

    def browse_output(self):
        path = filedialog.askdirectory(title='出力先フォルダを選択')
        if path:
            self.settings.output_dir.set(path)

    def browse_move_dir(self):
        path = filedialog.askdirectory(title='移動先フォルダを選択')
        if path:
            self.settings.move_dir.set(path)

    def pick_color(self):
        rgb, hex_color = colorchooser.askcolor(color=self.settings.line_hex(), title='線の色')
        if rgb:
            self.settings.line_color = tuple(int(v) for v in rgb)
            self.canvas.line_color = self.settings.line_color
            self.view.color_swatch.configure(background=hex_color)

    # -------------------------------------------------------------- キュー処理
    def load_input(self):
        path = self.settings.input_value()
        if not path:
            messagebox.showwarning('入力なし', '入力の動画またはフォルダを指定してください。')
            return

        if self.settings.is_single:
            if not os.path.isfile(path):
                messagebox.showerror('エラー', f'ファイルが見つかりません: {path}')
                return
            files = [path]
        else:
            if not os.path.isdir(path):
                messagebox.showerror('エラー', f'フォルダが見つかりません: {path}')
                return
            files = find_videos(path)
            if not files:
                messagebox.showwarning('動画なし', 'フォルダ内に対応する動画が見つかりません。')
                return

        self.queue = build_queue(files)
        self.queue_index = -1
        self._refresh_queue_list()
        self.log(f'{len(files)} 本の動画を読み込みました。順にROIを選択してください。')
        self._load_video_at(0)

    def _refresh_queue_list(self):
        self.suppress_queue_event = True
        listbox = self.view.queue_list
        listbox.delete(0, 'end')
        for i, item in enumerate(self.queue):
            listbox.insert('end', item.label(current=(i == self.queue_index)))
        if 0 <= self.queue_index < len(self.queue):
            listbox.selection_clear(0, 'end')
            listbox.selection_set(self.queue_index)
            listbox.see(self.queue_index)
        self.suppress_queue_event = False

    def on_queue_select(self, _event):
        """キューの項目をクリックしたら、その動画を読み込んでROI選択に入る。"""
        if self.suppress_queue_event:
            return
        selection = self.view.queue_list.curselection()
        if not selection or selection[0] == self.queue_index:
            return
        if self.phase in (PHASE_RUNNING, PHASE_PAUSED, PHASE_REROI):
            self.set_status('追跡中は動画を切り替えられません。中止するか完了を待ってください。')
            self._refresh_queue_list()  # 選択を現在の動画に戻す
            return
        self._load_video_at(selection[0])

    def _load_video_at(self, index):
        """キューの index の動画を読み込み、ROI選択の状態にする。"""
        self._release_session()
        if not 0 <= index < len(self.queue):
            self.phase = PHASE_IDLE
            self._update_buttons()
            return False

        item = self.queue[index]
        try:
            session = VideoSession(item.path)
        except VideoOpenError:
            item.status = STATUS_LOAD_FAILED
            self.log(f'読み込みに失敗しました: {item.name}')
            self._refresh_queue_list()
            self._update_buttons()
            return False

        self.queue_index = index
        self.session = session
        self.start_frame = item.start_frame
        self.bbox = item.bbox
        self.phase = PHASE_ROI
        if item.is_pending:
            item.status = STATUS_SELECTING
        self._refresh_queue_list()

        # 選択済みの動画は、そのとき選んだフレームまで戻して表示する
        frame = session.current_frame
        if self.start_frame:
            seeked = session.seek(self.start_frame)
            if seeked is not None:
                frame = seeked
            else:
                self.start_frame = 0

        self.view.set_seek_range(session.last_frame_index, self.start_frame)
        self.view.set_progress(0, maximum=max(session.total_frames, 1))

        if self.bbox is None:
            self.set_status(f'{item.name}: 追跡したい対象をドラッグで囲んでください。')
        else:
            x, y, w, h = self.bbox
            self.set_status(f'{item.name}: 選択済み (x={x}, y={y}, w={w}, h={h})'
                            ' — 選び直すには再度ドラッグしてください。')
        self.log(f'読み込み: {item.name} ({session.describe()})')

        self._update_buttons()   # canvas.selectable を先に更新してから描画する
        self.canvas.show_frame(frame)
        self.canvas.draw_bbox(self.bbox)
        return True

    def _advance_to_next_unselected(self):
        """ROI未選択の動画へ自動で進む。無ければ選択フェーズの完了を知らせる。"""
        order = (list(range(self.queue_index + 1, len(self.queue)))
                 + list(range(self.queue_index)))
        for index in order:
            if self.queue[index].is_pending and self._load_video_at(index):
                return True

        selected = self.selected_count
        self.set_status(f'ROI選択が完了しました（{selected}本）。'
                        '「一括追跡開始」を押すとまとめて処理します。')
        self.log(f'ROI選択フェーズ完了: {selected} 本')
        self._update_buttons()
        return False

    def _cancel_pending_step(self):
        if self.after_id is not None:
            self.after_cancel(self.after_id)
            self.after_id = None

    def _close_writer(self):
        if self.writer is not None:
            self.writer.release()
            self.writer = None

    def _release_session(self):
        self._cancel_pending_step()
        self._close_writer()
        if self.session is not None:
            self.session.release()
            self.session = None

    # ------------------------------------------------------------ 表示とROI
    def on_canvas_resize(self):
        if self.session is not None and self.phase in (PHASE_ROI, PHASE_PAUSED, PHASE_REROI):
            self.canvas.show_frame(self.session.current_frame)
            self.canvas.draw_bbox(self.bbox)  # 表示倍率が変わるのでROIを引き直す

    def on_roi_drag(self, width, height):
        self.set_status(f'選択中: {width} x {height} px')

    def on_roi_select(self, bbox):
        self.bbox = bbox
        if bbox is None:
            self.set_status('選択範囲が小さすぎます。もう一度ドラッグしてください。')
            self._update_buttons()
            return

        x, y, w, h = bbox
        center = f'中心 ({x + w // 2}, {y + h // 2})'
        if self.phase == PHASE_REROI:
            self.set_status(f'ROI: x={x}, y={y}, w={w}, h={h} / {center}'
                            ' — 「選択したROIで再開」を押してください。')
        else:
            item = self.current_item
            item.select(bbox, self.start_frame)
            self._refresh_queue_list()
            self.set_status(f'{item.name}: 選択済み (x={x}, y={y}, w={w}, h={h} / {center})')
            if self.settings.auto_next.get():
                # 少し見せてから次の動画へ
                self.after(250, self._advance_to_next_unselected)
        self._update_buttons()

    # --------------------------------------------------------------- シーク
    def on_seek_move(self, value):
        if self.phase != PHASE_ROI or self.session is None:
            return
        self.view.set_seek_label(int(float(value)), self.session.last_frame_index)

    def on_seek_release(self, _event):
        if self.phase != PHASE_ROI or self.session is None:
            return
        target = int(float(self.view.seek_scale.get()))
        frame = self.session.seek(target)
        if frame is None:
            target = 0
            frame = self.session.seek(0)
        if frame is not None:
            self.start_frame = target
            self.bbox = None
            item = self.current_item
            item.start_frame = target
            item.bbox = None                 # フレームが変わったのでROIは選び直し
            item.status = STATUS_SELECTING
            self._refresh_queue_list()
            self.canvas.show_frame(frame)
            self.set_status(f'開始フレーム: {target} — 対象をドラッグで囲んでください。')
        self._update_buttons()

    # ------------------------------------------------------------- 追跡制御
    def _create_tracker(self):
        return self.trackers[self.settings.tracker_name.get()]()

    def on_start_button(self):
        if self.phase == PHASE_REROI:
            self._resume_with_new_roi()
        else:
            self._start_batch()

    def _start_batch(self):
        """ROI選択済みの動画をキューの順に、まとめて処理する。"""
        selected = self.selected_count
        if not selected:
            messagebox.showwarning('未選択', 'ROIを選択した動画がありません。')
            return
        self.log(f'=== 一括追跡を開始します（{selected} 本 / '
                 f'{self.settings.tracker_name.get()}）===')
        self._start_next_queued()

    def _start_next_queued(self):
        """選択済みの次の動画の追跡を始める。無ければ待機状態に戻る。"""
        for index, item in enumerate(self.queue):
            if item.is_selected and self._begin_video_tracking(index):
                return True

        self._release_session()
        self.phase = PHASE_IDLE
        self.set_status('選択済みの動画をすべて処理しました。')
        self.log('=== すべての処理が完了しました ===')
        self._refresh_queue_list()
        self._update_buttons()
        return False

    def _begin_video_tracking(self, index):
        if self.queue[index].bbox is None or not self._load_video_at(index):
            return False

        item = self.queue[index]
        frame = self.session.seek(self.start_frame)
        if frame is None:
            self.log(f'開始フレームを読み込めませんでした: {item.name}')
            item.status = STATUS_LOAD_FAILED
            self._refresh_queue_list()
            return False

        self.session.start_tracking(self._create_tracker(), frame, self.bbox, self.start_frame)
        self.view.set_progress(self.session.frame_idx,
                               maximum=max(self.session.total_frames, 1))
        if self.settings.save_video.get():
            self._open_writer()

        item.status = STATUS_TRACKING
        self._refresh_queue_list()
        self.log(f'追跡開始: {item.name}（フレーム {self.start_frame} から / '
                 f'{self.settings.tracker_name.get()}）')

        self.canvas.clear_overlay()
        self.phase = PHASE_RUNNING
        self._update_buttons()
        self._schedule_step()
        return True

    def _resume_with_new_roi(self):
        """一時停止中に選び直したROIでトラッカーを作り直し、続きから追跡する。"""
        if self.bbox is None or self.session is None:
            return
        self.session.restart_tracking(self._create_tracker(), self.bbox)
        self.log(f'ROIを再選択しました（フレーム {self.session.frame_idx}）')

        self.canvas.clear_overlay()
        self.phase = PHASE_RUNNING
        self._update_buttons()
        self._schedule_step()

    def _open_writer(self):
        try:
            path = os.path.join(self._video_output_dir(), 'tracked.mp4')
            self.writer = open_video_writer(path, self.session.fps, self.session.size)
        except OSError as e:
            self.writer = None
            self.log(f'警告: 出力フォルダを作成できませんでした: {e}')
            return
        if self.writer is None:
            self.log('警告: 追跡動画の書き出しを開始できませんでした。')

    def _schedule_step(self):
        speed = self.settings.speed_factor()
        if speed > 0:
            delay = max(int(1000.0 / (self.session.fps * speed)), 1)
        else:
            delay = 1
        self.after_id = self.after(delay, self._step)

    def toggle_pause(self):
        if self.phase == PHASE_RUNNING:
            self._cancel_pending_step()
            self.phase = PHASE_PAUSED
            self.set_status(f'一時停止中（フレーム {self.session.frame_idx}）')
            if self.session.current_frame is not None:
                self.canvas.show_frame(self._overlay(self.session.current_frame.copy()))
        elif self.phase in (PHASE_PAUSED, PHASE_REROI):
            self.canvas.clear_overlay()
            self.phase = PHASE_RUNNING
            self.set_status('追跡中...')
            self._schedule_step()
        self._update_buttons()

    def begin_reroi(self):
        if self.phase not in (PHASE_PAUSED, PHASE_REROI):
            return
        self.phase = PHASE_REROI
        self.bbox = None
        self._update_buttons()
        self.canvas.show_frame(self.session.current_frame)
        self.set_status('新しい追跡対象をドラッグで囲み、「選択したROIで再開」を押してください。')

    def stop_and_save(self):
        self._cancel_pending_step()
        self._finish_video(STATUS_ABORTED)

    def retry_video(self):
        item = self.current_item
        if item is None:
            return
        self._cancel_pending_step()
        self._close_writer()
        item.reset()
        self.log(f'{item.name} をROI選択からやり直します。')
        self._load_video_at(self.queue_index)

    # ------------------------------------------------------------- 追跡本体
    def _overlay(self, frame):
        return overlay_trajectory(frame, self.session.positions,
                                  self.settings.line_bgr(), self.settings.line_thickness())

    def _step(self):
        if self.phase != PHASE_RUNNING or self.session is None:
            return

        speed = self.settings.speed_factor()
        batch = FAST_BATCH if speed < 0 else 1
        display_frame = None

        for _ in range(batch):
            frame = self.session.read()
            if frame is None:
                self._finish_video(STATUS_DONE)
                return

            self.session.update(frame)
            if self.writer is not None or speed >= 0:
                display_frame = self._overlay(frame.copy())
                if self.writer is not None:
                    self.writer.write(display_frame)

        if speed >= 0 and display_frame is not None:
            self.canvas.show_frame(display_frame)
        self.view.set_progress(self.session.frame_idx)
        if self.session.total_frames:
            self.set_status(f'追跡中... {self.session.frame_idx} / '
                            f'{self.session.total_frames} フレーム')
        else:
            self.set_status(f'追跡中... {self.session.frame_idx} フレーム')
        self._schedule_step()

    # --------------------------------------------------------------- 保存
    def _video_output_dir(self):
        """現在の動画の出力フォルダを用意して返す。"""
        return ensure_output_dir(self.settings.output_root(), self.current_item.name)

    def _finish_video(self, reason):
        self._cancel_pending_step()
        self._close_writer()

        item = self.current_item
        session = self.session
        settings = self.settings

        self.log(f'{reason}: {item.name}（{session.frame_idx} フレーム / '
                 f'追跡成功 {session.tracked_count}）')

        try:
            out_dir = self._video_output_dir()
        except OSError as e:
            self.log(f'出力フォルダを作成できませんでした: {e}')
            self._abandon_video(item, reason)
            return

        if settings.save_csv.get():
            try:
                path = write_csv(os.path.join(out_dir, 'track.csv'), session.records)
                self.log(f'CSV保存: {path}')
            except OSError as e:
                self.log(f'CSVの保存に失敗しました: {e}')

        color, thickness = settings.line_bgra(), settings.line_thickness()

        if settings.save_png.get():
            path = write_trajectory_png(os.path.join(out_dir, 'full.png'), session.size,
                                        session.positions, color, thickness)
            if path:
                self.log(f'軌跡PNG保存: {path}')
            else:
                self.log(f'軌跡PNGの保存に失敗しました: '
                         f'{os.path.join(out_dir, "full.png")}')

        if settings.save_interval.get():
            interval = settings.interval_seconds()
            if write_interval_pngs(out_dir, session.size, session.positions,
                                   session.fps, interval, color, thickness):
                self.log(f'区間PNG保存: {out_dir}（{interval}秒ごと）')

        if settings.save_video.get():
            self.log(f'追跡動画保存: {os.path.join(out_dir, "tracked.mp4")}')

        source_path = item.path
        self._release_session()

        item.status = reason
        self._refresh_queue_list()

        if settings.move_source.get():
            self._move_source(source_path)

        self.phase = PHASE_IDLE
        self._update_buttons()
        self._start_next_queued()   # 選択済みの次の動画へ

    def _abandon_video(self, item, reason):
        """出力できなかったときでも、後始末して次の動画へ進む。"""
        self._release_session()
        item.status = reason
        self._refresh_queue_list()
        self.phase = PHASE_IDLE
        self._update_buttons()
        self._start_next_queued()

    def _move_source(self, path):
        move_dir = self.settings.move_target()
        if not move_dir:
            return
        try:
            self.log(f'動画を移動: {move_video(path, move_dir)}')
        except OSError as e:
            self.log(f'動画の移動に失敗しました: {e}')

    # --------------------------------------------------------------- 終了
    def on_close(self):
        self._release_session()
        self.destroy()


def main():
    app = TrackerApp()
    if app.ready:
        app.mainloop()
