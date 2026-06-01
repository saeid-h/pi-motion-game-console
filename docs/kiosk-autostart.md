# Boot straight into the game (kiosk setup)

Make the Pi power on, log in, and launch the game automatically — no keyboard
needed. Do this after the game already runs manually (see `setup-pi.md`).

> Assumes username `pi` and the repo cloned at `~/raspberry-games`. If yours
> differ, adjust the paths below (especially in the `.desktop` file).

## 1. Auto-login to the desktop

```bash
sudo raspi-config
```

Go to **1 System Options → S5 Boot / Auto Login → B4 Desktop Autologin**, then
finish and reboot when prompted. Now the Pi boots to the desktop without a login
prompt.

## 2. Make the launch script executable

```bash
chmod +x ~/raspberry-games/scripts/start-game.sh
```

Test it from a terminal first — it should open the game fullscreen:

```bash
~/raspberry-games/scripts/start-game.sh
```

Press **ESC** or **Q** to quit back to the desktop.

## 3. Install the autostart entry

The `~/.config/autostart/*.desktop` mechanism runs after desktop login and works
on both X11 (Pi 3B's default) and Wayland.

```bash
mkdir -p ~/.config/autostart
cp ~/raspberry-games/scripts/raspberry-game.desktop ~/.config/autostart/
```

Open `~/.config/autostart/raspberry-game.desktop` and confirm the `Exec=` path
matches your username and clone location (default `/home/pi/raspberry-games/...`).

## 4. Reboot and test

```bash
sudo reboot
```

The Pi should boot to the desktop and the game should appear fullscreen a few
seconds later.

## Turn it into a true kiosk (optional)

By default the game runs once; quitting returns to the desktop. To make it a
console that relaunches itself, uncomment the auto-relaunch loop at the bottom of
`scripts/start-game.sh`. The loop has a crash-guard (stops after 3 fast exits) so
a misconfigured camera can't trap the Pi in a relaunch loop.

## Switching what launches

When you add a menu (`src/main.py`) or another game, just change the last line of
`scripts/start-game.sh` (e.g. `python3 src/main.py`).

## Disabling autostart

Remove the entry and reboot:

```bash
rm ~/.config/autostart/raspberry-game.desktop
```

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| Boots to desktop, game doesn't start | Check the `Exec=` path in the `.desktop` file; make sure `start-game.sh` is executable |
| Game starts then immediately closes | Run `start-game.sh` from a terminal to see the error (camera/audio not ready — see `setup-pi.md`) |
| Screen goes black mid-game | The script disables X11 blanking; on Wayland set screen blanking off in Screen Configuration / `raspi-config` Display options |
| Can't get back to desktop | If you enabled the relaunch loop: SSH in and `pkill -f game_jump.py`, or remove the autostart entry |
