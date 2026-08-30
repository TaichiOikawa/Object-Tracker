# Object Tracker

動画内の対象をドラッグで囲んで追跡し、CSV / 軌跡PNG / 区間PNG / 追跡動画 を書き出す Tkinter GUI。

## 実行

```sh
uv run main.py
```

`uv run` が依存関係（opencv-contrib-python / numpy / pillow）を自動で同期する。
依存だけ入れ直したいときは `uv sync`、追加は `uv add <package>`。

> OpenCV 5 では `cv2.legacy` の CSRT / MOSSE / MedianFlow などが無くなるため、
> `opencv-contrib-python` を 4.x に固定している。

## 使い方

2フェーズ制:

1. **ROI選択** — 「読み込み」でキューに動画を並べ、順に対象をドラッグで囲む。
   開始フレームはスライダで変更でき、変更するとROIは選び直しになる。
   キューの項目をクリックすればいつでも読み込み直せる。
2. **一括追跡** — 「一括追跡開始」で `[選択済み]` の動画をまとめて処理する。
   追跡中は 一時停止 / ROI再選択して再開 / 中止して保存 / やり直し が使える。

出力は `出力先/<動画ファイル名>/` に `track.csv`・`full.png`・`<秒>.png`・`tracked.mp4`。

## 構成

| ファイル | 役割 |
| --- | --- |
| `main.py` | 起動スクリプト |
| `tracker/constants.py` | 定数（拡張子・トラッカー一覧・状態・フェーズ） |
| `tracker/trackers.py` | 利用できるOpenCVトラッカーの選別 |
| `tracker/drawing.py` | 軌跡の描画と色変換 |
| `tracker/queue_model.py` | 処理キューの1項目（動画1本） |
| `tracker/session.py` | 動画のキャプチャと追跡状態（GUI非依存） |
| `tracker/exporters.py` | CSV / PNG / 追跡動画の書き出し、動画の移動 |
| `tracker/settings.py` | GUIの設定値（tk変数） |
| `tracker/video_canvas.py` | フレーム表示とドラッグによるROI選択 |
| `tracker/widgets.py` | 小さな共通ウィジェット（ログ） |
| `tracker/ui.py` | 画面レイアウト |
| `tracker/app.py` | コントローラ `TrackerApp` |
