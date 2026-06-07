"""All tunable knobs in one place.

Start here when behaviour needs adjusting for a real child / camera / room.
Values are deliberately conservative; Phase 4 tuning will refine them.
"""

# --- Processing resolution (small = fast; plenty for motion zones) ---
PROC_WIDTH = 320
PROC_HEIGHT = 240

# Mirror the image horizontally so it feels like a mirror to the player.
MIRROR = True

# --- Motion pipeline (frame differencing: each frame vs the previous one) ---
BLUR_KERNEL = 11            # odd number; Gaussian blur to suppress sensor noise
DIFF_THRESHOLD = 20         # a pixel must change by this much (0..255) to count as motion

# --- Capture ---
CAMERA_INDEX = 0            # USB webcam / laptop camera index (Pi Camera ignores this)

# --- Zones as normalized rects (x0, y0, x1, y1), origin top-left, range 0..1 ---
ZONES = {
    "top":   (0.00, 0.00, 1.00, 0.40),
    "left":  (0.00, 0.25, 0.35, 1.00),
    "right": (0.65, 0.25, 1.00, 1.00),
    "total": (0.00, 0.00, 1.00, 1.00),
}

# --- Trigger thresholds (fraction of a zone's pixels in motion, 0..1) ---
# Consumed by the games, not by camera.py.
# JUMP_THRESHOLD measured on a real single-player clip: still ~0.006, jump peaks
# ~0.14. 0.05 sits well clear of fidget noise. This is the #1 knob to tune.
JUMP_THRESHOLD = 0.05
PUNCH_THRESHOLD = 0.10
DANCE_THRESHOLD = 0.05

# Refractory period after a trigger fires, so one move = one trigger (seconds).
DEBOUNCE_S = 0.5

# Warm-up to let the background model settle before play (seconds).
CALIBRATION_S = 2.0

# --- Display (games) ---
FULLSCREEN = True
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 480
SHOW_PREVIEW = False        # show a small mirrored camera preview during the game
