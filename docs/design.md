# Design — Motion Game Console

This is a living document. It explains *why* the code is shaped the way it is, so the
project stays understandable as we add games.

## The core constraint: a Raspberry Pi 3B

The Pi 3B is a quad-core 1.2 GHz with 1 GB RAM. That single fact drives every design
decision.

We originally considered **MediaPipe pose tracking** (which gives precise body
landmarks — wrist, hip, knee, etc.). Measured reality:

- Pi 5 ≈ 6 FPS, Pi 4 ≈ 10–12 FPS with full MediaPipe pose.
- A Pi 3B would land around **1–3 FPS** — a slideshow. For a 4-year-old who needs
  *instant* feedback, that kills the fun.

So we **dropped MediaPipe** and use lightweight **OpenCV motion detection** instead,
which runs at **20–30 FPS** on a Pi 3B.

## The key idea: motion *zones*, not body parts

We don't know "that's the left wrist." We only know "a lot changed in this region of
the picture." That turns out to be enough.

We divide the camera frame into regions and measure how much **motion energy** is in
each one per frame:

```
        +---------------------------+
        |           TOP             |   top    -> Jump
        +---------------------------+
        |  LEFT    |     |   RIGHT   |   left   -> Punch left
        |          |     |           |   right  -> Punch right
        +---------------------------+
                 (whole frame: total -> Dance energy)
```

Each game reads these signals and decides what happened. Because the signals are just
numbers (0–1), every game shares the same input layer.

## How motion energy is computed

Standard, cheap OpenCV pipeline on a small frame (320×240):

1. Capture frame, downscale to 320×240.
2. Convert to grayscale.
3. Gaussian blur (kills sensor noise — also why camera focus is irrelevant).
4. Background subtraction (`cv2.createBackgroundSubtractorMOG2`) → foreground mask of
   what's *moving*.
5. Threshold the mask to binary.
6. For each zone, motion energy = fraction of pixels that are "on" in that zone (0–1).

A short calibration at game start lets the background model settle so a still child
doesn't register as motion.

## Architecture: decouple camera from rendering

The camera and the game run at different natural rates, and we never want camera work
to stutter the animation. So:

```
[Camera thread]                         [Pygame main loop ~30 FPS]
 capture 320x240 frame                   read latest zone signals
 grayscale + blur                        run game logic (state machine)
 MOG2 background subtraction             draw big colorful visuals
 threshold + per-zone energy             play sounds
 publish {top,left,right,total} ───────► react (jump / punch / etc.)
```

- A **background thread** captures and processes frames, then publishes the latest
  `{top, left, right, total}` to a shared, lock-protected object.
- The **Pygame main loop** reads whatever the latest values are each frame. It never
  blocks on the camera.

## Debouncing: one move = one trigger

Raw motion is noisy and a single jump spans several frames. Each game applies a
**refractory period**: after a trigger fires, it ignores new triggers for ~0.4–0.6 s.
This stops one jump from registering as ten.

## Game → signal mapping

| Game        | Signal used        | Trigger |
|-------------|--------------------|---------|
| Jump!       | `top`              | spike above threshold (debounced) |
| Punch it    | `left` / `right`   | spike in that side |
| Dance Along | `total`            | sustained energy over a window |
| Simon Says  | direction of motion| mapped to "go left / right / jump / wave" |

Note: precise poses like "touch your head" need landmarks we don't have, so Simon Says
is adapted to *movement directions* instead.

## Code layout

| File              | Responsibility |
|-------------------|----------------|
| `src/config.py`   | All tunables: resolution, zone boxes, thresholds, debounce times |
| `src/camera.py`   | Capture abstraction (Pi Camera *or* USB webcam) + motion detection + threaded publisher. Runnable standalone for testing. |
| `src/game_jump.py`| The Jump! game (MVP) |
| `src/assets/`     | Images + sounds |

The capture abstraction tries `picamera2` (Pi Camera) first and falls back to
`cv2.VideoCapture` (USB webcam / laptop), so the same code runs on the Pi and on a dev
machine.

## Build order

1. **Phase 0** — repo + docs scaffold. *(done)*
2. **Phase 1** — Pi from scratch (`setup-pi.md`).
3. **Phase 2** — `camera.py` + `config.py`, verified standalone.
4. **Phase 3** — `game_jump.py` end-to-end.
5. **Phase 4** — tune thresholds for a real child; document how to add the next game.

## Tuning notes

_(to be filled in Phase 4 once tested with a real child and camera)_
