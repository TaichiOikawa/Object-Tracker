"""物体追跡GUI。

エントリポイントは main.py（`uv run main.py`）。
    constants.py     共有する定数
    trackers.py      OpenCVトラッカーの選別
    drawing.py       軌跡の描画と色変換
    queue_model.py   処理キューの1項目（動画1本）
    session.py       動画のキャプチャと追跡状態（GUI非依存）
    exporters.py     CSV / PNG / 追跡動画の書き出し
    settings.py      GUIの設定値（tk変数）
    video_canvas.py  フレーム表示とROI選択
    widgets.py       小さな共通ウィジェット
    ui.py            画面レイアウト
    app.py           コントローラ（TrackerApp）
"""

from .app import TrackerApp, main

__all__ = ['TrackerApp', 'main']
