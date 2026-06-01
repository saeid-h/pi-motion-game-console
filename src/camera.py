"""Camera capture + lightweight motion-zone detection.

Provides one thing the games need: the latest motion energy in each zone, as
numbers in 0..1, published from a background thread so the game loop never blocks
on the camera.

Works on both the Raspberry Pi (Pi Camera via picamera2) and a dev laptop / USB
webcam (cv2.VideoCapture), auto-detected.

Run standalone to verify the camera and watch live zone values + FPS:

    python3 src/camera.py
"""

import threading
import time

import cv2
import numpy as np

import config


# --------------------------------------------------------------------------- #
# Zones
# --------------------------------------------------------------------------- #
def zone_rects(width, height):
    """Convert the normalized ZONES in config to pixel rectangles for a frame."""
    return {
        name: (int(x0 * width), int(y0 * height), int(x1 * width), int(y1 * height))
        for name, (x0, y0, x1, y1) in config.ZONES.items()
    }


# --------------------------------------------------------------------------- #
# Capture sources (Pi Camera or USB webcam) — both expose read() / release()
# --------------------------------------------------------------------------- #
class _PiCamSource:
    def __init__(self, picam):
        self._picam = picam

    def read(self):
        # picamera2 returns an RGB array; convert to BGR for OpenCV consistency.
        rgb = self._picam.capture_array()
        return cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)

    def release(self):
        self._picam.stop()


class _CvCamSource:
    def __init__(self, cap):
        self._cap = cap

    def read(self):
        ok, frame = self._cap.read()
        return frame if ok else None

    def release(self):
        self._cap.release()


def open_capture():
    """Open the best available camera. Pi Camera first, then USB/laptop."""
    try:
        from picamera2 import Picamera2

        picam = Picamera2()
        cfg = picam.create_preview_configuration(
            main={"format": "RGB888", "size": (config.PROC_WIDTH, config.PROC_HEIGHT)}
        )
        picam.configure(cfg)
        picam.start()
        time.sleep(0.5)  # let auto-exposure settle
        return _PiCamSource(picam)
    except Exception:
        pass  # no Pi Camera (or not on a Pi) — fall back

    cap = cv2.VideoCapture(config.CAMERA_INDEX)
    if not cap.isOpened():
        raise RuntimeError(
            "No camera found (tried Pi Camera and USB index %d)" % config.CAMERA_INDEX
        )
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, config.PROC_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config.PROC_HEIGHT)
    return _CvCamSource(cap)


# --------------------------------------------------------------------------- #
# Motion detection
# --------------------------------------------------------------------------- #
class MotionDetector:
    """Turns a frame into per-zone motion energy via MOG2 background subtraction."""

    def __init__(self):
        self._bg = cv2.createBackgroundSubtractorMOG2(
            history=config.MOG2_HISTORY,
            varThreshold=config.MOG2_VAR_THRESHOLD,
            detectShadows=config.MOG2_DETECT_SHADOWS,
        )

    def process(self, frame):
        """Return (signals dict, small BGR frame, binary mask)."""
        if config.MIRROR:
            frame = cv2.flip(frame, 1)
        small = cv2.resize(frame, (config.PROC_WIDTH, config.PROC_HEIGHT))

        gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
        k = config.BLUR_KERNEL
        gray = cv2.GaussianBlur(gray, (k, k), 0)

        fg = self._bg.apply(gray)
        _, mask = cv2.threshold(fg, config.FG_THRESHOLD, 255, cv2.THRESH_BINARY)

        h, w = mask.shape
        signals = {}
        for name, (x0, y0, x1, y1) in zone_rects(w, h).items():
            roi = mask[y0:y1, x0:x1]
            signals[name] = float(np.count_nonzero(roi)) / max(1, roi.size)
        return signals, small, mask


# --------------------------------------------------------------------------- #
# Threaded tracker — the public interface the games use
# --------------------------------------------------------------------------- #
class MotionTracker:
    """Captures + processes frames in a background thread, publishes latest signals."""

    def __init__(self):
        self._detector = MotionDetector()
        self._lock = threading.Lock()
        self._signals = {name: 0.0 for name in config.ZONES}
        self._frame = None
        self._mask = None
        self._fps = 0.0
        self._running = False
        self._thread = None
        self._source = None

    def start(self):
        self._source = open_capture()
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        return self

    def _loop(self):
        last = time.time()
        fps_ema = None
        while self._running:
            frame = self._source.read()
            if frame is None:
                time.sleep(0.005)
                continue
            signals, small, mask = self._detector.process(frame)

            now = time.time()
            dt = now - last
            last = now
            if dt > 0:
                inst = 1.0 / dt
                fps_ema = inst if fps_ema is None else 0.9 * fps_ema + 0.1 * inst

            with self._lock:
                self._signals = signals
                self._frame = small
                self._mask = mask
                self._fps = fps_ema or 0.0

    def get(self):
        """Latest per-zone motion energy as a dict (thread-safe copy)."""
        with self._lock:
            return dict(self._signals)

    def snapshot(self):
        """Latest (signals, frame, mask, fps) for debugging/preview."""
        with self._lock:
            frame = None if self._frame is None else self._frame.copy()
            mask = None if self._mask is None else self._mask.copy()
            return dict(self._signals), frame, mask, self._fps

    def stop(self):
        self._running = False
        if self._thread is not None:
            self._thread.join(timeout=1.0)
        if self._source is not None:
            self._source.release()


# --------------------------------------------------------------------------- #
# Standalone test harness
# --------------------------------------------------------------------------- #
def _run_test():
    tracker = MotionTracker().start()
    print("Camera test — move in front of the camera. Press 'q' in the window to quit.")
    try:
        while True:
            signals, frame, mask, fps = tracker.snapshot()
            if frame is None:
                time.sleep(0.01)
                continue

            vis = frame.copy()
            h, w = vis.shape[:2]
            for name, (x0, y0, x1, y1) in zone_rects(w, h).items():
                if name == "total":
                    continue
                val = signals[name]
                color = (0, 255, 0) if val > 0.05 else (120, 120, 120)
                cv2.rectangle(vis, (x0, y0), (x1, y1), color, 2)
                cv2.putText(vis, "%s:%.2f" % (name, val), (x0 + 3, y0 + 16),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
            cv2.putText(vis, "FPS:%4.1f  total:%.2f" % (fps, signals["total"]),
                        (5, h - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)

            mask_bgr = cv2.cvtColor(mask, cv2.COLOR_GRAY2BGR) if mask is not None else vis
            combo = np.hstack([vis, mask_bgr])
            cv2.imshow("motion test  (left = camera, right = motion mask)", combo)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break
    finally:
        tracker.stop()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    _run_test()
