# Raspberry Pi Setup — from scratch

This gets a fresh Raspberry Pi 3B ready to run the games. Do it once. Budget ~1 hour
(mostly downloads/updates).

> Throughout, `pi` is the username. If you set a different one in the imager, adjust.

## 1. Flash the SD card

On your laptop:

1. Install **Raspberry Pi Imager** → https://www.raspberrypi.com/software/
2. Insert the SD card (16 GB+).
3. In Imager:
   - **Device:** Raspberry Pi 3
   - **OS:** Raspberry Pi OS (64-bit) — the full **Desktop** version (we need a screen + audio)
   - **Storage:** your SD card
4. Click the **gear / "Edit Settings"** before writing and preset:
   - Hostname: e.g. `gamebox`
   - Enable **SSH** (so you can connect from your laptop)
   - Wi-Fi SSID + password
   - Username `pi` + a password
   - Locale / timezone
5. Write, then put the card in the Pi.

## 2. First boot

1. Connect the Pi to your **TV/monitor via HDMI**, plug in a keyboard, then power.
   - **Plug the camera in BEFORE powering on** (see step 3) — the ribbon connector is
     not hot-pluggable.
2. Let it boot to the desktop.
3. From your laptop you can also SSH in: `ssh pi@gamebox.local`

## 3. Connect the camera (do this with the Pi powered OFF)

For the **Arducam Pi Camera v2 (CSI ribbon)**:

1. Find the camera port on the Pi 3B — the long thin connector between the HDMI and the
   3.5 mm jack (labeled **CAMERA**).
2. Gently lift the black plastic clip.
3. Insert the ribbon so the **blue stripe faces the HDMI/ethernet side** (metal contacts
   face the other way). On a Pi 3B the contacts face toward the HDMI port.
4. Press the clip back down. It should hold the ribbon firmly.
5. Power on.

> Using a **USB webcam** instead? Just plug it in — skip the ribbon steps. The code
> auto-detects it.

## 4. Update the OS

Open a terminal (or SSH) and run:

```bash
sudo apt update && sudo apt full-upgrade -y
sudo reboot
```

## 5. Test the camera

For the **Pi Camera (CSI)** on Bookworm:

```bash
rpicam-hello -t 5000      # shows a 5-second preview window
```

If you see live video, the camera works. If you get "no cameras available":

- Re-seat the ribbon (powered off), stripe orientation as in step 3.
- Make sure you're on a recent Bookworm image (the camera is auto-detected; no
  `raspi-config` toggle needed on current OS).

For a **USB webcam**:

```bash
lsusb                     # should list your camera
v4l2-ctl --list-devices   # shows /dev/video0  (install: sudo apt install v4l-utils)
```

## 6. Install the game dependencies

Use **apt**, not pip — these are prebuilt and avoid slow/failing source builds on a 3B:

```bash
sudo apt install -y python3-opencv python3-pygame python3-picamera2 python3-numpy
```

(`python3-picamera2` is only needed for the CSI camera; harmless to install regardless.)

Quick sanity check:

```bash
python3 -c "import cv2, pygame, numpy; print('cv2', cv2.__version__, '| pygame', pygame.ver)"
```

## 7. Audio

Sound is core to the games. Pick an output and test it:

```bash
# Route audio: right-click the speaker icon on the desktop taskbar and choose
# HDMI (if your TV has speakers) or "Analog" (3.5 mm jack).

speaker-test -t wav -c 2     # you should hear "front left / front right". Ctrl+C to stop.
```

If using HDMI audio and you hear nothing, make sure the TV input/volume is up.

## 8. Get the games

```bash
cd ~
git clone https://github.com/saeid-h/raspberry-games.git
cd raspberry-games
```

## 9. Run

```bash
# Verify the camera + motion detection first (live zone values + FPS overlay):
python3 src/camera.py

# Then play:
python3 src/game_jump.py
```

Stand ~1.5–3 m back so your whole body is in frame, with the camera roughly at chest
height pointing at the play area. Good, even lighting helps a lot.

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `rpicam-hello`: no cameras | Re-seat ribbon (power off), check stripe orientation, update OS |
| Low FPS | Lower light is fine; just ensure nothing else heavy is running. Close the browser. |
| Everything reads as motion | Stand still during the calibration countdown; re-run calibration |
| No sound | Re-check output device (HDMI vs analog) and TV volume; re-run `speaker-test` |
| Game window too small/large | It runs fullscreen by default; see `FULLSCREEN` in `src/config.py` |
