#!/bin/bash
# Launches the motion game console fullscreen on the Raspberry Pi.
# Called by the desktop autostart entry (see docs/kiosk-autostart.md).

# Run from the repo root regardless of where this script is invoked from.
cd "$(dirname "$0")/.." || exit 1

# Keep the screen awake during play (X11 only; harmless/no-op on Wayland).
xset s off 2>/dev/null
xset -dpms 2>/dev/null
xset s noblank 2>/dev/null

# Launch the game. The game has its own "play again" screen, and ESC/Q quits
# back to the desktop.
python3 src/game_jump.py

# --- Optional: auto-relaunch (uncomment to make it a true kiosk) -------------
# Turns it into a console that restarts itself if the child quits. Note: this
# removes the easy "quit to desktop" escape hatch — to stop it you'd SSH in and
# kill python3, or disable the autostart entry. The guard stops a crash loop.
#
# fails=0
# while true; do
#     start=$(date +%s)
#     python3 src/game_jump.py
#     # If it died in under 5s, count it as a crash; bail after 3 in a row.
#     [ $(( $(date +%s) - start )) -lt 5 ] && fails=$((fails+1)) || fails=0
#     [ "$fails" -ge 3 ] && { echo "game keeps crashing; stopping"; break; }
#     sleep 2
# done
