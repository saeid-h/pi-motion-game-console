# Raspberry Games — Motion Game Console

A camera-based motion game console for a 4–6 year old, built for a **Raspberry Pi 3B**.
The child moves in front of a camera and on-screen games react with colorful visuals
and sound. No controller — the body is the controller.

## How it works

A cheap single camera feeds frames to lightweight **OpenCV motion detection** (no
MediaPipe — too slow on a Pi 3B). Instead of tracking exact body parts, we measure
**motion energy in zones** of the frame and map that to game actions:

| Zone signal | Game action |
|-------------|-------------|
| `top`       | Jump        |
| `left` / `right` | Punch left / right |
| `total`     | Dance energy |

This runs at ~20–30 FPS on a Pi 3B, so reactions feel instant.

## Games

- **Jump!** — jump to make your character jump (first game / MVP)
- **Punch it** — punch left/right (planned)
- **Dance Along** — move to the music (planned)
- **Simon Says** — follow movement prompts (planned)

## Hardware

- Raspberry Pi 3B
- Arducam Pi Camera Module v2 (8 MP IMX219, **fixed focus**, CSI ribbon) — or any USB webcam
- HDMI display/TV + audio out (HDMI or 3.5 mm speaker)
- 16 GB+ SD card

## Setup

See [`docs/setup-pi.md`](docs/setup-pi.md) for the from-scratch Raspberry Pi setup,
[`docs/kiosk-autostart.md`](docs/kiosk-autostart.md) to boot straight into the game,
and [`docs/design.md`](docs/design.md) for how the code is structured.

## Run

```bash
# Test the camera + motion detection standalone (shows live zone values + FPS)
python3 src/camera.py

# Play Jump!
python3 src/game_jump.py
```

## Project layout

```
src/
  config.py      # tunables: resolution, zones, thresholds, debounce
  camera.py      # capture + motion-zone detection (threaded)
  game_jump.py   # Jump! game
  assets/        # images + sounds
docs/
  design.md      # architecture (living doc)
  setup-pi.md    # Raspberry Pi setup guide
```
