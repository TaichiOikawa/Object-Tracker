"""CSV / PNG / 追跡動画の書き出しと、処理済み動画の移動。"""

import csv
import os
import shutil

import cv2
import numpy as np

from .constants import CSV_HEADER
from .drawing import draw_trajectory


def open_video_writer(path, fps, size):
    """追跡動画の VideoWriter を開く。開けなければ None。"""
    os.makedirs(os.path.dirname(path) or '.', exist_ok=True)
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    writer = cv2.VideoWriter(path, fourcc, fps, size)
    if not writer.isOpened():
        writer.release()
        return None
    return writer


def write_csv(path, records):
    with open(path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(CSV_HEADER)
        writer.writerows(records)
    return path


def write_trajectory_png(path, size, positions, color, thickness):
    """透過PNGに軌跡だけを描いて保存する。"""
    width, height = size
    canvas = np.zeros((height, width, 4), dtype=np.uint8)
    draw_trajectory(canvas, positions, color, thickness)
    cv2.imwrite(path, canvas)
    return path


def write_interval_pngs(out_dir, size, positions, fps, interval, color, thickness):
    """interval 秒ごとに、その時点までの軌跡を <秒>.png として書き出す。"""
    if not positions:
        return 0
    sec = interval
    count = 0
    while int(sec * fps) <= len(positions):
        write_trajectory_png(os.path.join(out_dir, f'{sec}.png'), size,
                             positions[:int(sec * fps)], color, thickness)
        sec += interval
        count += 1
    return count


def move_video(path, dest_dir):
    """処理し終えた動画を dest_dir へ移動し、移動先のパスを返す。"""
    os.makedirs(dest_dir, exist_ok=True)
    dest = os.path.join(dest_dir, os.path.basename(path))
    shutil.move(path, dest)
    return dest
