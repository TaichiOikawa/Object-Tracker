"""CSV / PNG / 追跡動画の書き出しと、処理済み動画の移動。"""

import csv
import os
import shutil

import cv2
import numpy as np

from .constants import CSV_HEADER
from .drawing import draw_trajectory


def ensure_output_dir(root, video_name):
    """動画1本ぶんの出力フォルダを作って返す。

    フォルダ名は拡張子を除いたファイル名にする。出力先に
    元動画と同名のファイルがあると os.makedirs が FileExistsError に
    なるため。それでも同名のファイルがある場合は連番を付けて避ける。
    """
    stem = os.path.splitext(video_name)[0] or video_name
    candidate = os.path.join(root, stem)
    index = 1
    while os.path.exists(candidate) and not os.path.isdir(candidate):
        candidate = os.path.join(root, f'{stem}_{index}')
        index += 1
    os.makedirs(candidate, exist_ok=True)
    return candidate


def imwrite_unicode(path, image):
    """cv2.imwrite の代わり。日本語などASCII外を含むパスでも書き出せる。"""
    ext = os.path.splitext(path)[1] or '.png'
    ok, buffer = cv2.imencode(ext, image)
    if not ok:
        return False
    try:
        buffer.tofile(path)
    except OSError:
        return False
    return True


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
    """透過PNGに軌跡だけを描いて保存する。書けなければ None を返す。"""
    width, height = size
    canvas = np.zeros((height, width, 4), dtype=np.uint8)
    draw_trajectory(canvas, positions, color, thickness)
    if not imwrite_unicode(path, canvas):
        return None
    return path


def write_interval_pngs(out_dir, size, positions, fps, interval, color, thickness):
    """interval 秒ごとに、その時点までの軌跡を <秒>.png として書き出す。"""
    if not positions:
        return 0
    sec = interval
    count = 0
    while int(sec * fps) <= len(positions):
        if write_trajectory_png(os.path.join(out_dir, f'{sec}.png'), size,
                                positions[:int(sec * fps)], color, thickness):
            count += 1
        sec += interval
    return count


def move_video(path, dest_dir):
    """処理し終えた動画を dest_dir へ移動し、移動先のパスを返す。"""
    os.makedirs(dest_dir, exist_ok=True)
    dest = os.path.join(dest_dir, os.path.basename(path))
    shutil.move(path, dest)
    return dest
