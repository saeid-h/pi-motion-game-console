"""Jump! — the first game.

A friendly character auto-runs. Rocks roll in along the ground (jump over them)
and raspberries float at jump height (jump to grab them for points). The child
makes the character jump by *physically jumping* in front of the camera, which
spikes overall motion (the `total` zone). The spacebar also works, for testing
without a camera.

    python3 src/game_jump.py

Quit with ESC or Q. After game over, jump / press SPACE to play again.
"""

import math
import random

import pygame

import config

# --- Physics (logical pixels; screen is a fixed logical surface, scaled to display) ---
GRAVITY = 1800.0     # px/s^2
JUMP_V = 760.0       # initial upward speed -> ~0.84 s airtime, ~160 px peak
START_SPEED = 240.0  # world scroll speed (px/s)
SPEED_RAMP = 5.0     # speed gained per second (gentle difficulty)


# --------------------------------------------------------------------------- #
# Pure logic (no pygame) — unit-testable
# --------------------------------------------------------------------------- #
def _overlap(a, b):
    """AABB overlap. Rects are (x, y, w, h)."""
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    return ax < bx + bw and ax + aw > bx and ay < by + bh and ay + ah > by


class JumpTrigger:
    """Debounced rising-edge detector with hysteresis + refractory period.

    Fires once when `value` crosses above `threshold`, then won't fire again
    until the signal falls back down (re-arm) AND `debounce_s` has elapsed.
    Keeps one physical jump from registering many times.
    """

    def __init__(self, threshold, debounce_s):
        self.threshold = threshold
        self.debounce_s = debounce_s
        self._armed = True
        self._last_fire = -1e9

    def update(self, value, now):
        # Re-arm whenever the signal falls back down (hysteresis), independent
        # of the refractory timer.
        if value < self.threshold * 0.5:
            self._armed = True
        # Fire only if armed, above threshold, and past the refractory period.
        if self._armed and value >= self.threshold and now - self._last_fire >= self.debounce_s:
            self._armed = False
            self._last_fire = now
            return True
        return False


class GameState:
    """All game logic. update(dt, jump) advances one step. No pygame here."""

    def __init__(self, w, h, seed=None):
        self.w, self.h = w, h
        self.ground_y = int(h * 0.80)
        self.player_w, self.player_h = 48, 64
        self.player_x = int(w * 0.18)
        self._rng = random.Random(seed)
        self.reset()

    def reset(self):
        self.player_y = float(self.ground_y)   # feet (bottom of player)
        self.player_vy = 0.0
        self.on_ground = True
        self.obstacles = []     # rocks on the ground
        self.berries = []       # floating collectibles
        self.speed = START_SPEED
        self.score = 0
        self.lives = 3
        self.spawn_t = 0.8
        self.invuln = 0.0
        self.over = False

    def player_rect(self):
        return (self.player_x, self.player_y - self.player_h, self.player_w, self.player_h)

    def _obstacle_rect(self, o):
        return (o["x"], self.ground_y - o["h"], o["w"], o["h"])

    def _berry_rect(self, b):
        return (b["x"], b["y"], b["w"], b["h"])

    def _spawn(self):
        if self._rng.random() < 0.55:
            h = self._rng.choice([40, 55, 70])
            self.obstacles.append({"x": float(self.w), "w": 34, "h": h})
        else:
            y = self.ground_y - self._rng.choice([95, 125, 155])
            self.berries.append({"x": float(self.w), "y": y, "w": 30, "h": 30})

    def update(self, dt, jump):
        if self.over:
            return

        jumped = False
        if jump and self.on_ground:
            self.player_vy = -JUMP_V
            self.on_ground = False
            jumped = True

        self.player_vy += GRAVITY * dt
        self.player_y += self.player_vy * dt
        if self.player_y >= self.ground_y:
            self.player_y = float(self.ground_y)
            self.player_vy = 0.0
            self.on_ground = True

        self.speed += SPEED_RAMP * dt

        self.spawn_t -= dt
        if self.spawn_t <= 0:
            self._spawn()
            self.spawn_t = self._rng.uniform(1.1, 1.8)

        for o in self.obstacles:
            o["x"] -= self.speed * dt
        for b in self.berries:
            b["x"] -= self.speed * dt
        self.obstacles = [o for o in self.obstacles if o["x"] + o["w"] > 0]
        self.berries = [b for b in self.berries if b["x"] + b["w"] > 0]

        self.invuln = max(0.0, self.invuln - dt)
        pr = self.player_rect()

        hit_obstacle = False
        for o in self.obstacles:
            if self.invuln <= 0 and _overlap(pr, self._obstacle_rect(o)):
                hit_obstacle = True
        if hit_obstacle:
            self.lives -= 1
            self.invuln = 1.2
            if self.lives <= 0:
                self.over = True

        kept = []
        got_berry = False
        for b in self.berries:
            if _overlap(pr, self._berry_rect(b)):
                self.score += 1
                got_berry = True
            else:
                kept.append(b)
        self.berries = kept

        # Report events for sound/effects (consumed by the render loop).
        return {"jumped": jumped, "hit": hit_obstacle, "berry": got_berry}


# --------------------------------------------------------------------------- #
# Sound — simple generated tones, no asset files needed
# --------------------------------------------------------------------------- #
class Sfx:
    def __init__(self):
        self.ok = False
        try:
            import numpy as np
            self._np = np
            self.jump = self._tone(660, 0.12)
            self.berry = self._tone(990, 0.10)
            self.hit = self._tone(160, 0.25, square=True)
            self.ok = True
        except Exception as e:
            print("Sound disabled (%s)" % e)

    def _tone(self, freq, dur, square=False):
        np = self._np
        rate = 44100
        n = int(rate * dur)
        t = np.linspace(0, dur, n, endpoint=False)
        wave = np.sign(np.sin(2 * math.pi * freq * t)) if square else np.sin(2 * math.pi * freq * t)
        env = np.minimum(1.0, np.linspace(1.0, 0.0, n) * 3)  # quick fade-out
        samples = (wave * env * 0.3 * 32767).astype(np.int16)
        stereo = np.column_stack([samples, samples])
        return pygame.sndarray.make_sound(np.ascontiguousarray(stereo))

    def play(self, snd):
        if self.ok and snd is not None:
            snd.play()


# --------------------------------------------------------------------------- #
# Rendering
# --------------------------------------------------------------------------- #
SKY = (135, 206, 235)
GROUND = (110, 170, 90)
PLAYER = (60, 90, 200)
ROCK = (120, 110, 100)
BERRY = (200, 40, 90)
LEAF = (60, 160, 70)
WHITE = (255, 255, 255)
DARK = (40, 40, 60)


def draw(screen, state, font, big, fps, camera_on):
    screen.fill(SKY)
    pygame.draw.rect(screen, GROUND, (0, state.ground_y, state.w, state.h - state.ground_y))

    for o in state.obstacles:
        x, y, w, h = state._obstacle_rect(o)
        pygame.draw.rect(screen, ROCK, (x, y, w, h), border_radius=6)

    for b in state.berries:
        x, y, w, h = state._berry_rect(b)
        cx, cy = int(x + w / 2), int(y + h / 2)
        pygame.draw.circle(screen, BERRY, (cx, cy), w // 2)
        pygame.draw.line(screen, LEAF, (cx, y), (cx, y - 8), 3)

    # Player: a friendly blob with a face. Blink while invulnerable.
    if not (state.invuln > 0 and int(state.invuln * 10) % 2 == 0):
        px, py, pw, ph = state.player_rect()
        pygame.draw.rect(screen, PLAYER, (px, py, pw, ph), border_radius=14)
        eye_y = int(py + ph * 0.35)
        pygame.draw.circle(screen, WHITE, (int(px + pw * 0.32), eye_y), 6)
        pygame.draw.circle(screen, WHITE, (int(px + pw * 0.68), eye_y), 6)
        pygame.draw.circle(screen, DARK, (int(px + pw * 0.32), eye_y), 3)
        pygame.draw.circle(screen, DARK, (int(px + pw * 0.68), eye_y), 3)

    # HUD
    screen.blit(font.render("Score: %d" % state.score, True, DARK), (12, 10))
    for i in range(state.lives):
        cx = state.w - 28 - i * 30
        pygame.draw.circle(screen, BERRY, (cx, 22), 10)
    if not camera_on:
        screen.blit(font.render("(keyboard mode — SPACE to jump)", True, DARK), (12, state.h - 26))

    if state.over:
        overlay = pygame.Surface((state.w, state.h), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 130))
        screen.blit(overlay, (0, 0))
        msg = big.render("Great job!", True, WHITE)
        sub = font.render("Score: %d   —   jump or press SPACE to play again" % state.score, True, WHITE)
        screen.blit(msg, msg.get_rect(center=(state.w // 2, state.h // 2 - 24)))
        screen.blit(sub, sub.get_rect(center=(state.w // 2, state.h // 2 + 24)))


def draw_calibration(screen, state, big, font, seconds_left):
    screen.fill(SKY)
    pygame.draw.rect(screen, GROUND, (0, state.ground_y, state.w, state.h - state.ground_y))
    msg = big.render("Stand still...", True, DARK)
    sub = font.render("Get ready to JUMP in %d" % int(math.ceil(seconds_left)), True, DARK)
    screen.blit(msg, msg.get_rect(center=(state.w // 2, state.h // 2 - 20)))
    screen.blit(sub, sub.get_rect(center=(state.w // 2, state.h // 2 + 24)))


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #
def main():
    pygame.mixer.pre_init(44100, -16, 2, 512)
    pygame.init()

    flags = 0
    if config.FULLSCREEN:
        flags = pygame.FULLSCREEN | pygame.SCALED
    screen = pygame.display.set_mode((config.SCREEN_WIDTH, config.SCREEN_HEIGHT), flags)
    pygame.display.set_caption("Jump!")
    pygame.mouse.set_visible(False)
    clock = pygame.time.Clock()
    font = pygame.font.SysFont(None, 30)
    big = pygame.font.SysFont(None, 72)

    sfx = Sfx()

    # Try the camera; fall back to keyboard-only if unavailable.
    tracker = None
    camera_on = False
    try:
        import camera
        tracker = camera.MotionTracker().start()
        camera_on = True
    except Exception as e:
        print("Camera unavailable (%s) — keyboard-only mode (SPACE to jump)." % e)

    state = GameState(config.SCREEN_WIDTH, config.SCREEN_HEIGHT)
    trigger = JumpTrigger(config.JUMP_THRESHOLD, config.DEBOUNCE_S)

    # Short "get ready" countdown before play begins (frame differencing needs
    # no background settling, but the pause gives the child time to get set).
    calib_left = config.CALIBRATION_S if camera_on else 0.0

    running = True
    now = 0.0
    while running:
        dt = clock.tick(60) / 1000.0
        now += dt

        key_jump = False
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_ESCAPE, pygame.K_q):
                    running = False
                elif event.key == pygame.K_SPACE:
                    key_jump = True

        cam_jump = False
        if camera_on:
            cam_jump = trigger.update(tracker.get()["total"], now)
        jump = key_jump or cam_jump

        if calib_left > 0:
            calib_left -= dt
            draw_calibration(screen, state, big, font, calib_left)
            pygame.display.flip()
            continue

        if state.over:
            if jump:
                state.reset()
        else:
            events = state.update(dt, jump)
            if events["jumped"]:
                sfx.play(sfx.jump)
            if events["berry"]:
                sfx.play(sfx.berry)
            if events["hit"]:
                sfx.play(sfx.hit)

        draw(screen, state, font, big, clock.get_fps(), camera_on)
        pygame.display.flip()

    if tracker is not None:
        tracker.stop()
    pygame.quit()


if __name__ == "__main__":
    main()
