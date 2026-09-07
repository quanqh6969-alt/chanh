"""
image_saver.py — Vẽ kết quả lên ảnh và lưu ra file ở thread riêng.

Lưu ảnh là I/O chậm (ảnh 2448x2048 ghép 2 tấm), không được để nó chặn
luồng xử lý slot. Vì vậy dùng queue + worker thread.
"""

import queue
import threading
from datetime import datetime

import cv2
import numpy as np

from config import Config
from logger_setup import logger


class ImageSaver:
    def __init__(self):
        self._queue = queue.Queue()
        self._thread = None

    def start(self):
        if not Config.SAVE_IMAGES:
            return
        Config.IMAGE_SAVE_DIR.mkdir(parents=True, exist_ok=True)
        self._thread = threading.Thread(target=self._worker, daemon=True)
        self._thread.start()
        logger.info(f"Image saver started -> {Config.IMAGE_SAVE_DIR}")

    def submit(
        self, images, results, slot_idx, obj_id, size_final, good_final
    ):
        self._queue.put(
            (images, results, slot_idx, obj_id, size_final, good_final)
        )

    def _worker(self):
        while True:
            try:
                data = self._queue.get()
                self._save_image_multi(*data)
                self._queue.task_done()
            except Exception as e:
                logger.error(f"Save worker error: {e}")

    def _draw_result_on_image(self, image, size_class, is_good, conf, polygon):
        if image is None:
            return None
        try:
            img = image.copy()
            if polygon is not None:
                contour = np.asarray(
                    polygon, dtype=np.float32
                ).astype(np.int32)
                color = (0, 255, 0) if is_good else (0, 0, 255)
                cv2.polylines(img, [contour], True, color, 3)
                m = cv2.moments(contour)
                if m["m00"] != 0:
                    cx = int(m["m10"] / m["m00"])
                    cy = int(m["m01"] / m["m00"])
                else:
                    pts = contour.reshape(-1, 2)
                    cx = int(np.mean(pts[:, 0]))
                    cy = int(np.mean(pts[:, 1]))
                label = (
                    f"{'PASS' if is_good else 'DEFECT'}"
                    f" S{size_class} {conf:.2f}"
                )
                cv2.putText(
                    img, label,
                    (max(cx - 100, 10), max(cy - 20, 30)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.65, color, 2,
                    cv2.LINE_AA,
                )
            return img
        except Exception:
            return image

    def _save_image_multi(
        self, images, results, slot_idx, obj_id, size_final, good_final
    ):
        """Ghép các shot của cùng 1 vật thành 1 ảnh ngang rồi lưu."""
        if not Config.SAVE_IMAGES or not images:
            return
        try:
            drawn = []
            for i, (img, res) in enumerate(zip(images, results)):
                scls, isgood, conf, poly = res
                d = self._draw_result_on_image(
                    img, scls, isgood, conf, poly
                )
                if d is not None:
                    cv2.putText(
                        d, f"Shot {i+1}", (10, 40),
                        cv2.FONT_HERSHEY_SIMPLEX, 1.0,
                        (255, 255, 0), 2, cv2.LINE_AA,
                    )
                    drawn.append(d)
            if not drawn:
                return
            if len(drawn) == 1:
                combined = drawn[0]
            else:
                h_max = max(im.shape[0] for im in drawn)
                resized = []
                for im in drawn:
                    if im.shape[0] != h_max:
                        sc = h_max / im.shape[0]
                        wn = int(im.shape[1] * sc)
                        im = cv2.resize(im, (wn, h_max))
                    resized.append(im)
                combined = np.hstack(resized)

            ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            dec = "pass" if good_final else "reject"

            fp = (
                Config.IMAGE_SAVE_DIR
                / f"slot{slot_idx}_obj_{obj_id:06d}_{ts}_size{size_final}_{dec}.jpg"
            )
            cv2.imwrite(str(fp), combined)
            logger.info(f"Saved: {fp.name}")
        except Exception as e:
            logger.error(f"Save image error: {e}")
