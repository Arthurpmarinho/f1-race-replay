"""Screen transitions for the arcade replay windows: a quick lights-out reveal when a replay
opens and a short fade to black on exit, so switching windows feels fast instead of frozen.

Both run for well under a second; once finished they draw nothing.
"""

import random

import arcade

from src.lib.settings import animations_enabled

F1_RED = (225, 6, 0)
INTRO_S = 0.75
OUTRO_S = 0.28
MAX_STEP_S = 1 / 30  # a slow first frame shouldn't skip the whole intro


def _ease_out(t):
    return 1 - (1 - t) ** 3


def _ease_in(t):
    return t ** 3


class _SpeedLines:
    """Horizontal streaks racing across the screen, each a head with a fading tail."""

    def __init__(self, count, seed):
        rng = random.Random(seed)
        self.lines = [
            (
                rng.uniform(0.04, 0.96),          # height on screen (fraction)
                rng.uniform(0.0, 0.35),           # start delay (fraction of the transition)
                rng.uniform(0.18, 0.5),           # tail length (fraction of the width)
                rng.choice((2, 2, 3, 4)),         # thickness in px
                F1_RED if rng.random() < 0.35 else (255, 255, 255),
            )
            for _ in range(count)
        ]

    def draw(self, width, height, progress, alpha):
        for y_frac, delay, length_frac, thickness, color in self.lines:
            t = (progress - delay) / (1 - delay)
            if t <= 0 or t >= 1:
                continue
            length = width * length_frac
            head = -length + (width + 2 * length) * _ease_out(t)
            y = y_frac * height
            segments = 4
            for i in range(segments):
                left = head - length * (segments - i) / segments
                right = head - length * (segments - i - 1) / segments
                a = int(alpha * (i + 1) / segments * (1 - t * 0.5))
                arcade.draw_lrbt_rectangle_filled(left, right, y, y + thickness, (*color, a))


class ScreenTransitions:
    def __init__(self, window):
        self.window = window
        self.mode = "intro" if animations_enabled() else None
        self.elapsed = 0.0
        self.lines = _SpeedLines(14, seed=7)

    @property
    def active(self):
        return self.mode is not None

    def exit(self):
        """Fade to black, then close the window."""
        if not animations_enabled():
            arcade.close_window()
            return
        if self.mode != "outro":
            self.mode = "outro"
            self.elapsed = 0.0

    def update(self, delta_time):
        if self.mode is None:
            return
        self.elapsed += min(delta_time, MAX_STEP_S)
        if self.mode == "intro" and self.elapsed >= INTRO_S:
            self.mode = None
        elif self.mode == "outro" and self.elapsed >= OUTRO_S:
            self.mode = None
            arcade.close_window()

    def draw(self):
        if self.mode is None:
            return
        w, h = self.window.width, self.window.height
        if self.mode == "intro":
            p = min(self.elapsed / INTRO_S, 1.0)
            cover = int(255 * (1 - _ease_out(p)))
            lines_alpha = 255
        else:
            p = min(self.elapsed / OUTRO_S, 1.0)
            cover = int(255 * _ease_in(p))
            lines_alpha = 180
        if cover > 0:
            arcade.draw_lrbt_rectangle_filled(0, w, 0, h, (8, 9, 12, cover))
        self.lines.draw(w, h, p, lines_alpha)


def attach_transitions(window):
    """Play the intro on this arcade window and let exit_with_fade() fade it out."""
    transitions = ScreenTransitions(window)
    draw, update = window.on_draw, window.on_update

    # pyglet looks handlers up on the instance, so these wrap the class methods.
    def on_draw():
        result = draw()
        transitions.draw()
        return result

    def on_update(delta_time):
        transitions.update(delta_time)
        return update(delta_time)

    window.on_draw = on_draw
    window.on_update = on_update
    window.transitions = transitions
    return transitions


def exit_with_fade(window):
    transitions = getattr(window, "transitions", None)
    if transitions is None:
        arcade.close_window()
    else:
        transitions.exit()
