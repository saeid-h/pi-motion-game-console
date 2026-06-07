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
4. **Frame differencing** (`cv2.absdiff` of this frame vs the previous) → a mask of
   pixels that *changed* since the last frame.
5. Threshold the mask to binary.
6. For each zone, motion energy = fraction of pixels that are "on" in that zone (0–1).

> **Why frame differencing, not MOG2 background subtraction?** We originally used
> MOG2. Testing on the real Pi showed it failed: a child standing between jumps fades
> into MOG2's learned background, and the signal flatlined near zero through actual
> jumping (measured — see the capture analysis). Frame differencing has no memory: a
> still child reads ~0, any movement spikes immediately. On a real single-player clip
> the whole-frame signal swung from ~0.006 at rest to ~0.14 mid-jump.

A short "get ready" countdown at game start gives the child time to get set (frame
differencing needs no background-model warm-up).

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
| Jump!       | `total`            | spike above threshold (debounced) |
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

## Tuning (do this on the Pi, with your child)

The thresholds in `config.py` are sensible defaults but **must be dialed in for your
room, lighting, camera placement, and how big your son's movements are**. The logic and
mechanics are verified; only these real-world numbers remain.

Procedure:

1. **Run the camera test first** (headless/over SSH it prints values; with a display it
   shows a window): `python3 src/camera.py`. Have your son stand where he'll play and
   watch the live values:
   - When he stands still, `total` should read near **0.00–0.01**. If it idles higher,
     raise `DIFF_THRESHOLD` and/or improve lighting (avoid a bright window behind him).
   - When he **jumps**, note the peak `total` value. When he **punches**, note `left`/`right`.
2. **Set `JUMP_THRESHOLD` to ~40–60% of the jump peak** you observed, well above the
   still-idle value. e.g. a jump peaking `total` ≈ 0.14 → `JUMP_THRESHOLD ≈ 0.05–0.07`.
   High enough to ignore fidgeting, low enough that a real jump always fires.
3. **Debounce:** if one jump registers as several in-game jumps, raise `DEBOUNCE_S`
   (try 0.6–0.8). If quick repeated jumps feel unresponsive, lower it.
4. **Camera framing:** mount at roughly chest height, far enough back that his **whole
   body is in frame** and he fills a good portion of it. Crucially, **only the player
   should be in frame** — frame differencing can't tell people apart, so a sibling or
   adult moving in view will trigger jumps too.
5. **Berry reach:** if the highest raspberries feel unreachable, lower the spawn heights
   in `GameState._spawn` (`game_jump.py`) or raise `JUMP_V`. Measured airtime peak is
   ~154 px at the current `JUMP_V`/`GRAVITY`.

Record the values you land on here once tested:

| Knob | Default | Tuned for our room |
|------|---------|--------------------|
| `JUMP_THRESHOLD` | 0.05 | _tbd_ |
| `DIFF_THRESHOLD` | 20 | _tbd_ |
| `DEBOUNCE_S` | 0.5 | _tbd_ |

## How to add the next game

Every game reuses the same input layer, so a new game is small:

1. Create `src/game_<name>.py`.
2. Start a tracker: `import camera; tracker = camera.MotionTracker().start()`.
3. Each frame, read `signals = tracker.get()` and use the relevant zone(s):
   - **Punch it** → `signals["left"]` / `signals["right"]` with a `JumpTrigger`-style
     debounce per side (reuse `JumpTrigger` from `game_jump.py`).
   - **Dance Along** → `signals["total"]`, averaged over a short window, drives a
     "dance meter."
   - **Simon Says** → compare which side/zone has the most motion to the current prompt.
4. Reuse the pattern from `game_jump.py`: a pygame-free state class + a `draw()` function
   + the same calibration warm-up and main loop.

A later `src/main.py` will be a simple menu that launches the chosen game.
