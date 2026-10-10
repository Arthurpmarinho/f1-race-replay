import arcade
from typing import List, Literal, Tuple, Optional
from typing import Sequence, Optional, Tuple
from src.lib.time import format_time
from src.lib.team_logos import team_logo_path
from src.lib.fonts import display_font_family
from src.lib import hud
import numpy as np
import pandas as pd
import fastf1.plotting
import os
from collections import OrderedDict
from src.tyre_degradation_integration import (
    format_tyre_health_bar, 
    format_degradation_text
)

# Building an arcade.Text (or changing its font, size or colour) re-lays out
# the whole label, which is by far the most expensive part of drawing a frame.
# Most HUD labels are identical from one frame to the next, so keep the
# objects around and reuse them for the same text, position and style.
_TEXT_CACHE = OrderedDict()
_TEXT_CACHE_SIZE = 2048


def cached_text(text, x, y, color=arcade.color.WHITE, font_size=12, **style):
    """Drop-in for ``arcade.Text(...)`` when the label is drawn right away."""
    if not isinstance(color, tuple):
        color = tuple(color)
    key = (str(text), x, y, color, font_size, tuple(sorted(style.items())))
    label = _TEXT_CACHE.get(key)
    if label is None:
        label = arcade.Text(text, x, y, color, font_size, **style)
        _TEXT_CACHE[key] = label
        if len(_TEXT_CACHE) > _TEXT_CACHE_SIZE:
            _TEXT_CACHE.popitem(last=False)
    else:
        _TEXT_CACHE.move_to_end(key)
    return label

def _format_wind_direction(degrees: Optional[float]) -> str:
  if degrees is None:
      return "N/A"
  deg_norm = degrees % 360
  dirs = [
      "N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
      "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW",
  ]
  idx = int((deg_norm / 22.5) + 0.5) % len(dirs)
  return dirs[idx]

class BaseComponent:
    def on_resize(self, window): pass
    def draw(self, window): pass
    def on_mouse_press(self, window, x: float, y: float, button: int, modifiers: int) -> bool: return False

class LegendComponent(BaseComponent):
    def __init__(self, x: int = 20, y: int = 220, visible=True): # Increased y to 220 to fit all lines
        self.x = x
        self.y = y
        self._control_icons_textures = {}
        self._visible = visible
        # Load control icons from images/icons folder (all files)
        icons_folder = os.path.join("images", "controls")
        if os.path.exists(icons_folder):
            for filename in os.listdir(icons_folder):
                if filename.lower().endswith(('.png', '.jpg', '.jpeg')):
                    texture_name = os.path.splitext(filename)[0]
                    texture_path = os.path.join(icons_folder, filename)
                    self._control_icons_textures[texture_name] = arcade.load_texture(texture_path)
        self.lines = ["Help (Click or 'H')"]
        
        self.controls_text_offset = 180
        self._text = arcade.Text("", self.x, self.y, arcade.color.CYAN, 14)
    
    @property
    def visible(self) -> bool:
        return self._visible
    
    @visible.setter
    def visible(self, value: bool):
        self._visible = value
    
    def toggle_visibility(self) -> bool:
        """
        Toggle the visibility of the legend
        """
        self._visible = not self._visible
        return self._visible
    
    def set_visible(self):
        """
        Set visibility of legend to True
        """
        self._visible = True


    def _help_pill_rect(self):
        """(left, bottom, right, top) of the help pill in the bottom-left corner."""
        cy = self.y - getattr(self, "controls_text_offset", 0)
        return (self.x, cy - 15, self.x + 116, cy + 15)

    def on_mouse_press(self, window, x: float, y: float, button: int, modifiers: int):
        left, bottom, right, top = self._help_pill_rect()

        if left <= x <= right and bottom <= y <= top:
            popup = getattr(window, "controls_popup_comp", None)
            if popup:
                # popup anchored to bottom left, small margin (20px)
                margin_x = 20
                margin_y = 20
                left_pos = float(margin_x)
                top_pos = float(margin_y + popup.height)
                desired_cx = left_pos + popup.width / 2
                desired_cy = top_pos - popup.height / 2
                if popup.visible and popup.cx == desired_cx and popup.cy == desired_cy:
                    popup.hide()
                else:
                    popup.show_over(left_pos, top_pos)
            return True
        return False

    def draw(self, window):
        # Skip rendering entirely if hidden
        if not self._visible:
            return
        left, bottom, right, top = self._help_pill_rect()
        cy = (bottom + top) / 2
        hud.draw_panel(left, bottom, right - left, top - bottom, radius=(top - bottom) / 2,
                       fill=hud.CONTROL_FILL, border=hud.CONTROL_BORDER)
        # "H" keycap followed by the label
        hud.draw_panel(left + 6, cy - 10, 22, 20, radius=6, fill=(255, 255, 255, 34), border=None)
        cached_text("H", left + 17, cy, hud.TEXT, 10, font_name=hud.DISPLAY_FONT,
                    anchor_x="center", anchor_y="center").draw()
        cached_text("Controls", left + 38, cy, hud.TEXT_DIM, 12, anchor_x="left", anchor_y="center").draw()

class WeatherComponent(BaseComponent):
    def __init__(self, left=20, width=300, height=130, top_offset=170, visible=True):
        self.left = left
        self.width = width
        self.height = height
        self.top_offset = top_offset
        self.info = None
        self._weather_icon_textures = {}
        self._visible: bool = visible
        # Load weather icons from images/weather folder (all files)
        weather_folder = os.path.join("images", "weather")
        if os.path.exists(weather_folder):
            for filename in os.listdir(weather_folder):
                if filename.lower().endswith(('.png', '.jpg', '.jpeg')):
                    texture_name = os.path.splitext(filename)[0]
                    texture_path = os.path.join(weather_folder, filename)
                    self._weather_icon_textures[texture_name] = arcade.load_texture(texture_path)

        self._text = arcade.Text("", self.left + 12, 0, arcade.color.LIGHT_GRAY, 14, anchor_y="top")

    def set_info(self, info: Optional[dict]):
        self.info = info
    
    @property
    def visible(self) -> bool:
        return self._visible
    
    @visible.setter
    def visible(self, value: bool):
        self._visible = value
    
    def toggle_visibility(self) -> bool:
        """
        Toggle the visibility of the weather
        """
        self._visible = not self._visible
        return self._visible
    
    def set_visible(self):
        """
        Set visibility of weather to True
        """
        self._visible = True

    def draw(self, window):
        # Skip rendering entirely if hidden
        if not self._visible or (not self.info and not getattr(window, "has_weather", False)):
            window.weather_bottom = None
            return
        panel_top = window.height - self.top_offset
        def _fmt(val, suffix="", precision=1):
            return f"{val:.{precision}f}{suffix}" if val is not None else "N/A"
        info = self.info or {}
        # Map each weather line to its corresponding icon
        weather_lines = [
            ("Track", f"{_fmt(info.get('track_temp'), '°C')}", "thermometer"),
            ("Air", f"{_fmt(info.get('air_temp'), '°C')}", "thermometer"),
            ("Humidity", f"{_fmt(info.get('humidity'), '%', precision=0)}", "drop"),
            ("Wind", f"{_fmt(info.get('wind_speed'), ' km/h', precision=0)} {_format_wind_direction(info.get('wind_direction'))}", "wind"),
            ("Rain", f"{info.get('rain_state','N/A')}", "rain"),
        ]

        # Two-column grid inside a glass card
        row_h = 34
        rows = (len(weather_lines) + 1) // 2
        height = 34 + rows * row_h + 6
        bottom = panel_top - height
        hud.draw_panel(self.left, bottom, self.width, height)
        hud.draw_section_title("WEATHER", self.left + 16, panel_top - 14)

        col_w = (self.width - 32) / 2
        for idx, (label, value, icon_key) in enumerate(weather_lines):
            col, row = idx % 2, idx // 2
            x = self.left + 16 + col * col_w
            cy = round(panel_top - 34 - row * row_h - row_h / 2)
            weather_texture = self._weather_icon_textures.get(icon_key)
            if weather_texture:
                arcade.draw_texture_rect(weather_texture, arcade.XYWH(x + 8, cy, 16, 16), alpha=200)
            cached_text(label, x + 24, cy + 7, hud.TEXT_DIM, 10, anchor_y="center").draw()
            cached_text(value, x + 24, cy - 8, hud.TEXT, 13, bold=True, anchor_y="center").draw()

        # Track the bottom of the weather panel so info boxes can stack below it
        window.weather_bottom = bottom

class LeaderboardComponent(BaseComponent):
    def __init__(self, x: int, right_margin: int = 260, width: int = 240, visible=True):
        self.x = x
        self.width = width
        self.entries = []  # list of tuples (code, color, pos, progress_m)
        self.rects = []    # clickable rects per entry
        self.selected = []  # Changed to list for multiple selection
        self.row_height = 25
        self.show_gaps = False
        self.show_neighbor_gaps = False
        self.gap_toggle_rect = None
        self.neighbor_toggle_rect = None
        # Reuse a single Text object for gap rendering to avoid reallocating each frame
        self._gap_text = arcade.Text("", 0, 0, arcade.color.LIGHT_GRAY, 12, anchor_x="right", anchor_y="top")
        self._tyre_textures = {}
        self._visible: bool = visible
        # Import the tyre textures from the images/tyres folder (all files)
        tyres_folder = os.path.join("images", "tyres")
        if os.path.exists(tyres_folder):
            for filename in os.listdir(tyres_folder):
                if filename.lower().endswith(('.png', '.jpg', '.jpeg')):
                    texture_name = os.path.splitext(filename)[0]
                    texture_path = os.path.join(tyres_folder, filename)
                    self._tyre_textures[texture_name] = arcade.load_texture(texture_path)
        self.computed_gaps = {}
        self.computed_neighbor_gaps = {}
        self._team_logos = None  # driver code -> texture, filled on first draw
        self._display_font = (display_font_family(), "calibri", "arial")

    def _load_team_logos(self, window):
        self._team_logos = {}
        results = getattr(getattr(window, "session", None), "results", None)
        if results is None:
            return
        textures = {}
        for _, row in results.iterrows():
            path = team_logo_path(row.get("TeamName"))
            if path:
                if path not in textures:
                    textures[path] = arcade.load_texture(path)
                self._team_logos[row.get("Abbreviation")] = textures[path]

    @property
    def visible(self) -> bool:
        return self._visible
    
    @visible.setter
    def visible(self, value: bool):
        self._visible = value
    
    def toggle_visibility(self) -> bool:
        """
        Toggle the visibility of the leaderboard
        """
        self._visible = not self._visible
        return self._visible
    
    def set_visible(self):
        """
        Set visibility of leaderboard to True
        """
        self._visible = True

    def set_entries(self, entries: List[Tuple[str, Tuple[int,int,int], dict, float]]):
        # entries sorted as expected
        self.entries = entries
        self._calculate_gaps()

    def _calculate_gaps(self):
        self.computed_gaps = {}
        self.computed_neighbor_gaps = {}
        if not self.entries:
            return

        leader_progress_val = self.entries[0][3]

        for idx, (code, _, pos, progress_m) in enumerate(self.entries):
            # Leader gap
            try:
                raw_to_leader = abs(leader_progress_val - (progress_m or 0.0))
                dist_to_leader = raw_to_leader / 10.0
                time_to_leader = dist_to_leader / 55.56
                self.computed_gaps[code] = 0.0 if idx == 0 else time_to_leader
            except Exception:
                self.computed_gaps[code] = None

            # Neighbor gap
            ahead_info = None
            try:
                if idx > 0:
                    code_ahead, _, _, progress_ahead = self.entries[idx - 1]
                    raw = abs((progress_m or 0.0) - (progress_ahead or 0.0))
                    dist_m = raw / 10.0
                    time_s = dist_m / 55.56
                    ahead_info = (code_ahead, dist_m, time_s)
            except Exception:
                ahead_info = None
            
            self.computed_neighbor_gaps[code] = {"ahead": ahead_info}

    def draw(self, window):
        # Skip rendering entirely if hidden
        if not self._visible:
            return
        self.selected = getattr(window, "selected_drivers", [])
        leaderboard_y = window.height - 40
        # sync with window state if present
        self.show_gaps = getattr(window, "leaderboard_show_gaps", self.show_gaps)
        self.show_neighbor_gaps = getattr(window, "leaderboard_show_neighbor_gaps", self.show_neighbor_gaps)

        # If both were set externally, prefer neighbor (interval) gaps and clear leader gaps.
        if self.show_gaps and self.show_neighbor_gaps:
            self.show_gaps = False

        if self._team_logos is None:
            self._load_team_logos(window)

        # Sort entries by lap number an distance progressed
        # If any of the entries have lap > 1, then sort

        if any(e[2].get("lap", 0) > 1 for e in self.entries):
            new_entries = sorted(
                self.entries,
                key=lambda e: (
                    -e[2].get("lap", 0),  # Descending lap number
                    -e[2].get("dist")                 # Descending distance progressed
                )
            )
        else:
            new_entries = self.entries

        lap_one = bool(new_entries) and new_entries[0][2].get("lap", 0) == 1
        rows_top = leaderboard_y - 30
        panel_bottom = rows_top - len(new_entries) * self.row_height - (34 if lap_one else 10)
        panel_top = window.height - 20
        hud.draw_panel(self.x - 10, panel_bottom, self.width + 20, panel_top - panel_bottom)
        hud.draw_section_title("LEADERBOARD", self.x + 4, panel_top - 14)

        # Interval / leader gap toggles as small pills to the right of the title
        toggle_y = panel_top - 20
        toggle_w, toggle_h = 34, 18
        for name, label, active, cx in (
            ("neighbor", "INT", self.show_neighbor_gaps, self.x + self.width - toggle_w * 1.5 - 4),
            ("gap", "LDR", self.show_gaps, self.x + self.width - toggle_w / 2),
        ):
            rect = (cx - toggle_w / 2, toggle_y - toggle_h / 2, cx + toggle_w / 2, toggle_y + toggle_h / 2)
            if name == "neighbor":
                self.neighbor_toggle_rect = rect
            else:
                self.gap_toggle_rect = rect
            if active:
                hud.draw_pill(cx, toggle_y, toggle_w, toggle_h, fill=(*hud.F1_RED, 200), border=(255, 120, 110, 120))
            else:
                hud.draw_pill(cx, toggle_y, toggle_w, toggle_h)
            cached_text(label, cx, toggle_y, hud.TEXT if active else hud.TEXT_DIM, 9, bold=True,
                        anchor_x="center", anchor_y="center").draw()

        has_logos = bool(self._team_logos)
        left_x = self.x
        right_x = self.x + self.width
        name_x = left_x + (58 if has_logos else 34)

        # Row backgrounds (team colour bars, selection highlight, separators) only change
        # when the order or the selection does, so they are cached as one shape list.
        order = tuple(code for code, _, _, _ in new_entries)
        row_colors = tuple(tuple(color) for _, color, _, _ in new_entries)
        selected = tuple(c for c in order if c in self.selected)

        def build_rows():
            for i, code in enumerate(order):
                top_y = rows_top - i * self.row_height
                cy = top_y - self.row_height / 2
                if code in selected:
                    points = hud._rounded_points(left_x - 4, top_y - self.row_height + 1, self.width + 8, self.row_height - 2, 6)
                    yield arcade.shape_list.create_polygon(points, (*hud.F1_RED, 70))
                    yield arcade.shape_list.create_line_loop(points, (*hud.F1_RED, 170), 1)
                elif i > 0:
                    yield arcade.shape_list.create_line(left_x + 4, top_y, right_x - 4, top_y, (255, 255, 255, 12), 1)
                yield arcade.shape_list.create_rectangle_filled(left_x + 25, cy, 3, 14, row_colors[i])

        hud.cached_shapes(("lb-rows", order, row_colors, selected, left_x, rows_top, self.width, self.row_height), build_rows).draw()

        self.rects = []
        for i, (code, color, pos, progress_m) in enumerate(new_entries):
            current_pos = i + 1
            top_y = rows_top - i * self.row_height
            bottom_y = top_y - self.row_height
            cy = round(top_y - self.row_height / 2)
            self.rects.append((code, left_x, bottom_y, right_x, top_y))

            cached_text(str(current_pos), left_x + 16, cy, hud.TEXT_DIM, 12, bold=True,
                        anchor_x="right", anchor_y="center").draw()

            # Team logo in front of the name, scaled to fit a 22x14 box
            logo = self._team_logos.get(code)
            if logo:
                scale = min(22 / logo.width, 14 / logo.height)
                arcade.draw_texture_rect(logo, arcade.XYWH(left_x + 43, cy, logo.width * scale, logo.height * scale))

            cached_text(code, name_x, cy, hud.TEXT, 11, font_name=hud.DISPLAY_FONT,
                        anchor_x="left", anchor_y="center").draw()

            # OUT (retired) in red, PIT in amber
            if pos.get("rel_dist", 0) == 1:
                cached_text("OUT", name_x + 56, cy, (255, 90, 80), 11, bold=True, anchor_x="left", anchor_y="center").draw()
            elif pos.get("in_pit"):
                cached_text("PIT", name_x + 56, cy, hud.AMBER, 11, bold=True, anchor_x="left", anchor_y="center").draw()

            # Gap display (if enabled)
            gap_text = ""
            if getattr(self, "show_neighbor_gaps", False):
                neighbor_info = self.computed_neighbor_gaps.get(code)

                if i == 0:
                    gap_text = "-"
                elif neighbor_info and neighbor_info.get("ahead"):
                    _, dist_m, time_s = neighbor_info.get("ahead")
                    gap_text = f"+{time_s:.1f}s"

            elif getattr(self, "show_gaps", False):
                gap_val = self.computed_gaps.get(code)
                if gap_val is None:
                    gap_val = pos.get("gap") or pos.get("gap_to_leader")
                if gap_val is not None:
                    try:
                        # expect seconds (float)
                        s = float(gap_val)
                        # leader (zero) gets dash
                        if abs(s) < 1e-6:
                            gap_text = "-"
                        else:
                            sign = "+" if s > 0 else "-"
                            gap_text = f"{sign}{abs(s):.1f}s"
                    except Exception:
                        gap_text = str(gap_val)

            if gap_text:
                cached_text(gap_text, right_x - 36, cy, hud.TEXT_DIM, 11, anchor_x="right", anchor_y="center").draw()

            # Tyre Icons
            tyre_val = pos.get("tyre", "?")
            tyre_texture = self._tyre_textures.get(str(tyre_val).upper())
            if tyre_texture:
                # position tyre icon inside the leaderboard area so it doesn't collide with track
                tyre_icon_x = left_x + self.width - 10
                tyre_icon_y = cy
                icon_size = 16
                rect = arcade.XYWH(tyre_icon_x, tyre_icon_y, icon_size, icon_size)

                current_life = pos.get("tyre_life", 0)
                tyre_health_ratio = 1.0
                if window.degradation_integrator:
                    idx = min(int(window.frame_index), len(window.frames) - 1)
                    health_data = window.degradation_integrator.get_health_for_frame(code, window.frames[idx])
                    if health_data:
                        tyre_health_ratio = health_data['health'] / 100.0
                else:
                    max_tyre_life = getattr(window, "max_tyre_life", {})
                    try:
                        tyre_key = int(tyre_val)
                    except (TypeError, ValueError):
                        max_life = 30
                    else:
                        max_life = max_tyre_life.get(tyre_key, 30)
                    if max_life > 0:
                        tyre_health_ratio = max(0.0, min(1.0, 1.0 - (current_life / max_life)))
                    else:
                        tyre_health_ratio = 1.0

                arcade.draw_texture_rect(rect=rect, texture=tyre_texture, alpha=80)
                bright_height = icon_size * tyre_health_ratio
                if bright_height > 0:
                    window.ctx.scissor = (int(tyre_icon_x - 8), int(tyre_icon_y - 8), int(icon_size), int(bright_height))
                    arcade.draw_texture_rect(rect=rect, texture=tyre_texture, alpha=255)
                    window.ctx.scissor = None

                try:
                    life_display = str(int(current_life)) if pd.notna(current_life) else "0"
                except (ValueError, TypeError):
                    life_display = "0"
                cached_text(
                    life_display,
                    tyre_icon_x + 8,
                    tyre_icon_y - 8,
                    hud.TEXT,
                    8,
                    bold=True,
                    anchor_x="center",
                    anchor_y="center"
                ).draw()

                # DRS Indicator: dot to the left of the tyre icon, green while DRS is open
                drs_val = pos.get("drs", 0)
                is_drs_on = drs_val and int(drs_val) >= 10
                drs_color = hud.GREEN if is_drs_on else (255, 255, 255, 40)
                arcade.draw_circle_filled(tyre_icon_x - icon_size - 4, tyre_icon_y, 3.5, drs_color)

        # Add text at the bottom of the leaderboard during lap 1 to alert the user to potential mis-ordering
        if lap_one:
            cached_text("May be inaccurate during Lap 1",
                        self.x + 4, rows_top - (len(new_entries) * self.row_height) - 8,
                        hud.AMBER, 10, anchor_x="left", anchor_y="top").draw()

    def on_mouse_press(self, window, x: float, y: float, button: int, modifiers: int):
        # interval toggle (radio type)
        if self.neighbor_toggle_rect:
            n_left, n_bottom, n_right, n_top = self.neighbor_toggle_rect
            if n_left <= x <= n_right and n_bottom <= y <= n_top:
                if self.show_neighbor_gaps:
                    # currently selected -> deselect
                    self.show_neighbor_gaps = False
                    setattr(window, "leaderboard_show_neighbor_gaps", False)
                else:
                    # select interval gaps and deselect leader gaps
                    self.show_neighbor_gaps = True
                    self.show_gaps = False
                    setattr(window, "leaderboard_show_neighbor_gaps", True)
                    setattr(window, "leaderboard_show_gaps", False)
                return True
        # leader toggle (radio type)
        if self.gap_toggle_rect:
            g_left, g_bottom, g_right, g_top = self.gap_toggle_rect
            if g_left <= x <= g_right and g_bottom <= y <= g_top:
                if self.show_gaps:
                    self.show_gaps = False
                    setattr(window, "leaderboard_show_gaps", False)
                else:
                    self.show_gaps = True
                    self.show_neighbor_gaps = False
                    setattr(window, "leaderboard_show_gaps", True)
                    setattr(window, "leaderboard_show_neighbor_gaps", False)
                return True

        for code, left, bottom, right, top in self.rects:
            if left <= x <= right and bottom <= y <= top:
                # Detect multi-select modifiers
                is_multi = (modifiers & arcade.key.MOD_SHIFT)

                if is_multi:
                    if code in self.selected:
                        self.selected.remove(code)
                    else:
                        self.selected.append(code)
                else:
                    # Single click: clear others and toggle selection
                    if len(self.selected) == 1 and self.selected[0] == code:
                        self.selected = []
                    else:
                        self.selected = [code]

                # Propagate both list and single reference for compatibility
                window.selected_drivers = self.selected
                window.selected_driver = self.selected[-1] if self.selected else None
                return True
        return False

class LapTimeLeaderboardComponent(BaseComponent):
    def __init__(self, x: int, right_margin: int = 260, width: int = 240):
        self.x = x
        self.width = width
        self.entries = []  # list of dicts: {'pos', 'code', 'color', 'time'}
        self.rects = []    # clickable rects per entry
        self.selected = []  # Changed to list
        self.row_height = 25
        self._visible = True
        self.title = "Lap Times"

    def set_entries(self, entries: List[dict]):
        """Accept a list of dicts with keys: pos, code, color, time"""
        self.entries = entries or []
    
    @property
    def visible(self) -> bool:
        return self._visible
    
    @visible.setter
    def visible(self, value: bool):
        self._visible = value
    
    def toggle_visibility(self) -> bool:
        """
        Toggle the visibility of the progress bar
        """
        self._visible = not self._visible
        return self._visible

    def draw(self, window):
        # Skip rendering entirely if hidden
        if not self._visible:
            return
        self.selected = getattr(window, "selected_drivers", [])
        leaderboard_y = window.height - 40
        cached_text(self.title, self.x, leaderboard_y, arcade.color.WHITE, 20, bold=True, anchor_x="left", anchor_y="top").draw()
        self.rects = []
        for i, entry in enumerate(self.entries):
            pos = entry.get('pos', i + 1)
            code = entry.get('code', '')
            color = entry.get('color', arcade.color.WHITE)
            time_str = entry.get('time', '')
            current_pos = i + 1
            top_y = leaderboard_y - 30 - ((current_pos - 1) * self.row_height)
            bottom_y = top_y - self.row_height
            left_x = self.x
            right_x = self.x + self.width
            # store clickable rect (code, left, bottom, right, top)
            self.rects.append((code, left_x, bottom_y, right_x, top_y))

            # selection highlight
            if code in self.selected:
                rect = arcade.XYWH((left_x + right_x) / 2, (top_y + bottom_y) / 2, right_x - left_x, top_y - bottom_y)
                arcade.draw_rect_filled(rect, arcade.color.LIGHT_GRAY)
                text_color = arcade.color.BLACK
            else:
                # accept tuple rgb or fallback to white
                text_color = tuple(color) if isinstance(color, (list, tuple)) else arcade.color.WHITE

            # Draw position and driver name on left, time on right with more padding
            driver_name = entry.get('driver_name', code)
            cached_text(f"{pos}. {driver_name}", left_x + 12, top_y, text_color, 16, anchor_x="left", anchor_y="top").draw()
            if time_str:
                cached_text(time_str, right_x - 12, top_y, text_color, 14, anchor_x="right", anchor_y="top").draw()

    def on_mouse_press(self, window, x: float, y: float, button: int, modifiers: int):
        for code, left, bottom, right, top in self.rects:
            if left <= x <= right and bottom <= y <= top:
                is_multi = (modifiers & arcade.key.MOD_SHIFT)

                if is_multi:
                    if code in self.selected:
                        self.selected.remove(code)
                    else:
                        self.selected.append(code)
                else:
                    if len(self.selected) == 1 and self.selected[0] == code:
                        self.selected = []
                    else:
                        self.selected = [code]

                window.selected_drivers = self.selected
                window.selected_driver = self.selected[-1] if self.selected else None
                return True
        return False

class QualifyingSegmentSelectorComponent(BaseComponent):
    def __init__(self, width=400, height=300):
        self.width = width
        self.height = height
        self.driver_result = None
        self.selected_segment = None
        
    def draw(self, window):
        if not getattr(window, "selected_driver", None):
            return
        
        code = window.selected_driver
        results = window.data['results']
        driver_result = next((res for res in results if res['code'] == code), None)
        # Calculate modal position (centered)
        center_x = window.width // 2
        center_y = window.height // 2
        left = center_x - self.width // 2
        right = center_x + self.width // 2
        top = center_y + self.height // 2
        bottom = center_y - self.height // 2
        
        # Draw modal background
        modal_rect = arcade.XYWH(center_x, center_y, self.width, self.height)
        arcade.draw_rect_filled(modal_rect, (40, 40, 40, 230))
        arcade.draw_rect_outline(modal_rect, arcade.color.WHITE, 2)
        
        # Draw title
        title = f"Qualifying Sessions - {driver_result.get('code','')}"
        cached_text(title, left + 20, top - 30, arcade.color.WHITE, 18, 
               bold=True, anchor_x="left", anchor_y="center").draw()
        
        # Draw segments
        segment_height = 50
        start_y = top - 80

        segments = []

        if driver_result.get('Q1') is not None:
            segments.append({
                'time': driver_result['Q1'],
                'segment': 1
            })
        if driver_result.get('Q2') is not None:
            segments.append({
                'time': driver_result['Q2'],
                'segment': 2
            })
        if driver_result.get('Q3') is not None:
            segments.append({
                'time': driver_result['Q3'],
                'segment': 3
            })
        
        for i, data in enumerate(segments):
            segment = f"Q{data['segment']}"
            segment_top = start_y - (i * (segment_height + 10))
            segment_bottom = segment_top - segment_height
            
            # Highlight if selected
            segment_rect = arcade.XYWH(center_x, segment_top - segment_height//2, 
                                     self.width - 40, segment_height)
            
            if segment == self.selected_segment:
                arcade.draw_rect_filled(segment_rect, arcade.color.LIGHT_GRAY)
                text_color = arcade.color.BLACK
            else:
                arcade.draw_rect_filled(segment_rect, (60, 60, 60))
                text_color = arcade.color.WHITE
                
            arcade.draw_rect_outline(segment_rect, arcade.color.WHITE, 1)
            
            # Draw segment info
            segment_text = f"{segment.upper()}"
            time_text = format_time(float(data.get('time', 'No Time')))
            
            cached_text(segment_text, left + 30, segment_top - 20, 
                       text_color, 16, bold=True, anchor_x="left", anchor_y="center").draw()
            cached_text(time_text, right - 30, segment_top - 20, 
                       text_color, 14, anchor_x="right", anchor_y="center").draw()
        
        # Draw close button
        close_btn_rect = arcade.XYWH(right - 30, top - 30, 20, 20)
        arcade.draw_rect_filled(close_btn_rect, arcade.color.RED)
        cached_text("×", right - 30, top - 30, arcade.color.WHITE, 16, 
               bold=True, anchor_x="center", anchor_y="center").draw()

    def on_mouse_press(self, window, x: float, y: float, button: int, modifiers: int):        
        if not getattr(window, "selected_driver", None):
            return False
        
        # Calculate modal position (same as in draw)
        center_x = window.width // 2
        center_y = window.height // 2
        left = center_x - self.width // 2
        right = center_x + self.width // 2
        top = center_y + self.height // 2
        bottom = center_y - self.height // 2
        
        # Check close button (match the rect from draw method)
        close_btn_left = right - 30 - 10  # center - half width
        close_btn_right = right - 30 + 10  # center + half width
        close_btn_bottom = top - 30 - 10  # center - half height
        close_btn_top = top - 30 + 10     # center + half height
        
        if close_btn_left <= x <= close_btn_right and close_btn_bottom <= y <= close_btn_top:
            window.selected_driver = None
            window.selected_drivers = []
            # Also clear leaderboard selection state so UI highlight is removed
            if hasattr(window, "leaderboard"):
                window.leaderboard.selected = []
            self.selected_segment = None
            return True

        # Check segment clicks
        code = window.selected_driver
        results = window.data['results']
        driver_result = next((res for res in results if res['code'] == code), None)
        
        if driver_result:
            segments = []
            if driver_result.get('Q1') is not None:
                segments.append({'time': driver_result['Q1'], 'segment': 1})
            if driver_result.get('Q2') is not None:
                segments.append({'time': driver_result['Q2'], 'segment': 2})
            if driver_result.get('Q3') is not None:
                segments.append({'time': driver_result['Q3'], 'segment': 3})

            segment_height, start_y = 50, top - 80
            left, right = center_x - self.width // 2, center_x + self.width // 2

            for i, data in enumerate(segments):
                s_top = start_y - (i * (segment_height + 10))
                s_bottom = s_top - segment_height
                if left + 20 <= x <= right - 20 and s_bottom <= y <= s_top:
                    try:
                        if hasattr(window, "load_driver_telemetry"):
                            window.load_driver_telemetry(code, f"Q{data['segment']}")
                        window.selected_driver = None
                        window.selected_drivers = []
                        if hasattr(window, "leaderboard"):
                            window.leaderboard.selected = []
                    except Exception as e:
                        print("Error starting telemetry load:", e)
                    return True
        return True # Consume all clicks when visible

class DriverInfoComponent(BaseComponent):
    def __init__(self, left=20, width=220, min_top=220):
        self.left = left
        self.width = width
        self.min_top = min_top
        self.degradation_integrator = None

    def draw(self, window):
        # Support multiple selection via window.selected_drivers
        codes = getattr(window, "selected_drivers", [])
        if not codes:
            # Fallback to single selection compatibility
            single = getattr(window, "selected_driver", None)
            codes = [single] if single else []

        if not codes or not window.frames:
            return

        idx = min(int(window.frame_index), window.n_frames - 1)
        frame = window.frames[idx]

        box_width, box_height, gap = self.width, 210, 10
        weather_bottom = getattr(window, "weather_bottom", None)
        current_top = weather_bottom - 20 if weather_bottom else window.height - 200

        for code in codes:
            if code not in frame["drivers"]: continue
            if current_top - box_height < self.min_top: break

            driver_pos = frame["drivers"][code]
            center_y = current_top - (box_height / 2)
            self._draw_info_box(window, code, driver_pos, center_y, box_width, box_height)
            current_top -= (box_height + gap)

    def _draw_info_box(self, window, code, driver_pos, center_y, box_width, box_height):
        center_x = self.left + box_width / 2
        top, bottom = center_y + box_height / 2, center_y - box_height / 2
        left, right = center_x - box_width / 2, center_x + box_width / 2

        team_color = tuple(window.driver_colors.get(code, arcade.color.GRAY))
        hud.draw_panel(left, bottom, box_width, box_height, accent=team_color)

        lb = getattr(window, "leaderboard", None) or \
             getattr(window, "leaderboard_ui", None) or \
             getattr(window, "leaderboard_comp", None)

        if not lb and hasattr(window, "ui_components"):
            for comp in window.ui_components:
                if isinstance(comp, LeaderboardComponent):
                    lb = comp
                    break

        # Header: team logo, driver code and current position
        header_cy = top - 24
        name_x = left + 16
        logo = (getattr(lb, "_team_logos", None) or {}).get(code)
        if logo:
            scale = min(28 / logo.width, 18 / logo.height)
            arcade.draw_texture_rect(logo, arcade.XYWH(left + 30, header_cy, logo.width * scale, logo.height * scale))
            name_x = left + 52
        cached_text(code, name_x, header_cy, hud.TEXT, 15, font_name=hud.DISPLAY_FONT, anchor_y="center").draw()

        lb_index = None
        if lb and hasattr(lb, "entries") and lb.entries:
            lb_index = next((i for i, e in enumerate(lb.entries) if e[0] == code), None)
        if lb_index is not None:
            cached_text(f"P{lb_index + 1}", right - 16, header_cy, hud.TEXT_DIM, 13,
                        font_name=hud.DISPLAY_FONT, anchor_x="right", anchor_y="center").draw()

        # Speed and gear as large numbers
        stat_y = top - 72
        speed = driver_pos.get('speed', 0)
        hud.draw_section_title("SPEED", left + 16, stat_y + 30)
        speed_text = cached_text(f"{speed:.0f}", left + 16, stat_y, hud.TEXT, 22,
                                 font_name=hud.DISPLAY_FONT, anchor_y="center")
        speed_text.draw()
        cached_text("km/h", left + 20 + speed_text.content_width, stat_y - 6, hud.TEXT_DIM, 11, anchor_y="center").draw()

        hud.draw_section_title("GEAR", left + 150, stat_y + 30)
        cached_text(f"{driver_pos.get('gear', '-')}", left + 150, stat_y, hud.TEXT, 22,
                    font_name=hud.DISPLAY_FONT, anchor_y="center").draw()

        # DRS state as a pill
        drs_val = driver_pos.get('drs', 0)
        drs_str, drs_color = ("DRS ON", hud.GREEN) if drs_val in [10, 12, 14] else \
            ("DRS AVAIL", hud.AMBER) if drs_val == 8 else ("DRS OFF", hud.TEXT_DIM)
        pill_cy = top - 108
        hud.draw_pill(left + 16 + 40, pill_cy, 80, 20, fill=(*drs_color[:3], 36), border=(*drs_color[:3], 100))
        cached_text(drs_str, left + 56, pill_cy, drs_color, 10, bold=True,
                    anchor_x="center", anchor_y="center").draw()

        cursor_y = top - 138
        left_text_x = left + 16

        # Gaps (Calculated from Leaderboard)
        gap_ahead, gap_behind = "Ahead: N/A", "Behind: N/A"
        if lb_index is not None:
            try:
                curr_pos = lb.entries[lb_index][3]

                def get_gap_str(neighbor_idx, prefix, sign):
                    n_code, _, _, n_pos = lb.entries[neighbor_idx]
                    dist = abs(curr_pos - n_pos) / 10.0
                    time = dist / 55.56  # 200 km/h reference speed
                    return f"{prefix} ({n_code}): {sign}{time:.2f}s ({dist:.1f}m)"

                if lb_index > 0:
                    gap_ahead = get_gap_str(lb_index - 1, "Ahead", "+")
                if lb_index < len(lb.entries) - 1:
                    gap_behind = get_gap_str(lb_index + 1, "Behind", "-")

            except IndexError:
                pass

        cached_text(gap_ahead, left_text_x, cursor_y, hud.TEXT_DIM, 11, anchor_y="center").draw()
        cursor_y -= 20
        cached_text(gap_behind, left_text_x, cursor_y, hud.TEXT_DIM, 11, anchor_y="center").draw()

        if self.degradation_integrator and hasattr(window, 'frames'):
            try:
                idx = min(int(window.frame_index), window.n_frames - 1)
                frame = window.frames[idx]
                health_data = self.degradation_integrator.get_health_for_frame(code, frame)

                if health_data:
                    cursor_y -= 24  # Space before health bar

                    # Tyre health bar: rounded track with a coloured fill
                    bar_params = format_tyre_health_bar(health_data['health'], width=180, height=8)
                    bar_x = left + 16
                    bar_h = bar_params['height']
                    hud.draw_panel(bar_x, cursor_y - bar_h / 2, bar_params['width'], bar_h, radius=bar_h / 2,
                                   fill=(255, 255, 255, 26), border=None)
                    if bar_params['fill_width'] > 0:
                        arcade.draw_lrbt_rectangle_filled(bar_x, bar_x + bar_params['fill_width'],
                                                          cursor_y - bar_h / 2, cursor_y + bar_h / 2, bar_params['color'])

                    cursor_y -= 16

                    # Tyre info text
                    tyre_text = format_degradation_text(health_data)
                    cached_text(tyre_text, left_text_x, cursor_y,
                               hud.TEXT_DIM, 10, anchor_y="center").draw()

            except (KeyError, AttributeError, TypeError) as e:
                print(f"Error displaying driver info: {e}")

        # Throttle and brake as slim vertical gauges on the right
        thr, brk = driver_pos.get('throttle', 0), driver_pos.get('brake', 0)
        t_r, b_r = max(0.0, min(1.0, thr / 100.0)), max(0.0, min(1.0, brk / 100.0 if brk > 1.0 else brk))
        bar_w, bar_h, b_y = 10, 76, top - 168
        for i, (label, ratio, color) in enumerate((("THR", t_r, hud.GREEN), ("BRK", b_r, hud.F1_RED))):
            bx = right - 54 + i * 30
            hud.draw_panel(bx - bar_w / 2, b_y, bar_w, bar_h, radius=bar_w / 2, fill=(255, 255, 255, 22), border=None)
            if ratio > 0:
                arcade.draw_lrbt_rectangle_filled(bx - bar_w / 2, bx + bar_w / 2, b_y, b_y + bar_h * ratio, color)
            cached_text(label, bx, b_y - 12, hud.TEXT_FAINT, 9, bold=True,
                        anchor_x="center", anchor_y="center").draw()

    def _get_driver_color(self, window, code):
        return window.driver_colors.get(code, arcade.color.GRAY)

    def _get_team_color(self, window, code):
        return window.team_colors.get(code, arcade.color.GRAY)


class ControlsPopupComponent(BaseComponent):
    def __init__(
        self,
        width: int = 430,
        height: int = 260,
        header_font_size: int = 18,
        body_font_size: int = 16,
        lines: Optional[list[str]] = None,
    ):

        self.width = width
        self.height = height
        self.visible = False
        
        self.cx: Optional[float] = None
        self.cy: Optional[float] = None
        
        self.header_font_size = header_font_size
        self.body_font_size = body_font_size
        self.lines = lines
        
        self._header_text = arcade.Text("", 0, 0, arcade.color.BLACK, self.header_font_size, anchor_x="left", anchor_y="center")
        self._body_text = arcade.Text("", 0, 0, arcade.color.LIGHT_GRAY, self.body_font_size, anchor_x="left", anchor_y="center")

    def _default_lines(self) -> list[str]:
        return [
            ("SPACE", "Pause/Resume"),
            ("← / →", "Jump back/forward"),
            ("↑ / ↓", "Speed +/-"),
            ("1-4", "Set speed: 0.5x / 1x / 2x / 4x"),
            ("R", "Restart"),
            ("D", "Toggle DRS Zones"),
            ("B", "Toggle Progress Bar"),
            ("L", "Toggle Driver Labels"),
            ("H", "Toggle Help Popup"),
            ("C", "Toggle Drivers points table"),
            ("A", "Toggle Constructors points table")
        ]

    def set_lines(self, lines: Optional[list[str]]):
        self.lines = lines

    def set_size(self, width: int, height: int):
        
        self.width = width
        self.height = height

    def set_font_sizes(self, header_font_size: int = None, body_font_size: int = None):
        
        if header_font_size is not None:
            self.header_font_size = header_font_size
            self._header_text.font_size = header_font_size
        if body_font_size is not None:
            self.body_font_size = body_font_size
            self._body_text.font_size = body_font_size

    def show_center(self):
        """Show popup centered in the window."""
        self.cx = None
        self.cy = None
        self.visible = True

    def show_over(self, left: float, top: float):
        
        self.cx = float(left + self.width / 2)
        self.cy = float(top - self.height / 2)
        self.visible = True

    def hide(self):
        self.visible = False
        self.cx = None
        self.cy = None

    def draw(self, window):
        if not self.visible:
            return
        cx = self.cx if self.cx is not None else window.width / 2
        cy = self.cy if self.cy is not None else window.height / 2
        left, top = round(cx - self.width / 2), round(cy + self.height / 2)
        hud.draw_panel(left, top - self.height, self.width, self.height, radius=16,
                       fill=(20, 22, 29, 245), accent=hud.F1_RED)
        hud.draw_section_title("CONTROLS", left + 18, top - 18, color=hud.TEXT, size=11)

        controls = self.lines if self.lines is not None else self._default_lines()

        line_spacing = max(18, int(self.body_font_size + 8))
        key_x = left + 18
        y = top - 54

        def key_name(key):
            # The text font has no arrow glyphs, so arrows are spelled out
            for arrow, name in (("←", "Left"), ("→", "Right"), ("↑", "Up"), ("↓", "Down")):
                key = key.replace(arrow, name)
            return key.replace(" / ", "/")

        key_labels = [
            cached_text(key_name(key), key_x + 8, y - i * line_spacing, hud.TEXT, self.body_font_size - 2,
                        bold=True, anchor_x="left", anchor_y="center")
            for i, (key, _) in enumerate(controls)
        ]
        # Descriptions line up just after the widest keycap
        desc_x = round(key_x + max([label.content_width for label in key_labels] + [40]) + 28)

        for key_label, (_, desc) in zip(key_labels, controls):
            hud.draw_panel(key_x, y - 10, key_label.content_width + 16, 20, radius=6,
                           fill=(255, 255, 255, 26), border=(255, 255, 255, 36))
            key_label.draw()

            cached_text(desc, desc_x, y, hud.TEXT_DIM, self.body_font_size, bold=False,
                        anchor_x="left", anchor_y="center").draw()

            y -= line_spacing

    def on_mouse_press(self, window, x: float, y: float, button: int, modifiers: int):
        
        if not self.visible:
            return False
        cx = self.cx if self.cx is not None else window.width / 2
        cy = self.cy if self.cy is not None else window.height / 2
        left = cx - self.width / 2
        right = cx + self.width / 2
        bottom = cy - self.height / 2
        top = cy + self.height / 2

        # If click inside the box, do nothing
        if left <= x <= right and bottom <= y <= top:
            return True

        # Click outside closes popup
        self.hide()
        return True
    
class ConstructorsChampionshipOverlay:

    def __init__(self, live_constructors_standings=None, current_constructors_standings=None,
                 x=20, y=300, visible=True, session=None):

        self.live_constructors_standings = live_constructors_standings or {}
        self.current_constructors_standings = current_constructors_standings or {}
        self.team_colors = {}
        self.visible = visible
        self.session = session

        self.x = x
        self.y = y
        self.current_lap = 1
        self.cached_lap_standings = {}

    def update(self, lap):
        """Update standings for current lap"""
        self.current_lap = lap
        self.cached_lap_standings = self.live_constructors_standings.get(lap, {})

    def draw(self):

        if not self.visible:
            return

        if not self.team_colors and self.session is not None:
            for driver in self.session.drivers:
                team = self.session.get_driver(driver)["TeamName"]

                if team not in self.team_colors:
                    try:
                        color_hex = fastf1.plotting.get_team_color(team, self.session)
                        hex_color = color_hex.lstrip("#")
                        rgb = tuple(int(hex_color[i:i+2], 16) for i in (0,2,4))
                        self.team_colors[team] = rgb
                    except:
                        self.team_colors[team] = (200,200,200)

        rows = list(self.cached_lap_standings.items())[:11]
        previous_order = list(self.current_constructors_standings.keys())
        _draw_standings_panel("CONSTRUCTORS STANDINGS", self.x, self.y, 300, [
            (team, self.team_colors.get(team, (200, 200, 200)), pts,
             pts - self.current_constructors_standings.get(team, 0),
             (previous_order.index(team) + 1 if team in previous_order else pos) - pos)
            for pos, (team, pts) in enumerate(rows, start=1)
        ], name_font=None)


def _draw_standings_panel(title, x, y, width, rows, name_font=hud.DISPLAY_FONT):
    """Glass table of (name, colour, points, gained, places_moved) rows with its title at (x, y)."""
    row_h = 20
    top = y + 30
    height = 44 + len(rows) * row_h
    hud.draw_panel(x - 16, top - height, width + 32, height, fill=(20, 22, 29, 235))
    hud.draw_section_title(title, x, top - 14)
    for pos, (name, color, pts, gained, delta) in enumerate(rows, start=1):
        cy = top - 38 - (pos - 1) * row_h - row_h / 2
        arcade.draw_lrbt_rectangle_filled(x + 22, x + 25, cy - 7, cy + 7, color)
        cached_text(str(pos), x + 14, cy, hud.TEXT_DIM, 12, bold=True,
                    anchor_x="right", anchor_y="center").draw()
        style = {"font_name": name_font} if name_font else {}
        cached_text(str(name), x + 32, cy, hud.TEXT, 10 if name_font else 12, anchor_y="center", **style).draw()
        cached_text(f"{pts:.0f}", x + width - 70, cy, hud.TEXT, 12, bold=True, anchor_x="right", anchor_y="center").draw()
        if gained > 0:
            cached_text(f"+{gained:.0f}", x + width - 30, cy, hud.GREEN, 11, anchor_x="right", anchor_y="center").draw()
        arrow, arrow_color = ("▲", hud.GREEN) if delta > 0 else ("▼", hud.F1_RED) if delta < 0 else ("•", hud.TEXT_FAINT)
        cached_text(arrow, x + width - 4, cy, arrow_color, 10, anchor_x="right", anchor_y="center").draw()


class DriversChampionshipOverlay:

    def __init__(self, live_standings=None, current_driver_standings=None,driver_colors=None,
                 x=20, y=300, visible=True):

        self.live_standings = live_standings or {}
        self.current_driver_standings = current_driver_standings or {}
        self.driver_colors = driver_colors or {}
        self.visible = visible

        self.x = x
        self.y = y
        self.current_lap = 1
        self.cached_lap_standings = {}

    def update(self, lap):
        """Update standings for current lap"""
        self.current_lap = lap
        self.cached_lap_standings = self.live_standings.get(lap, {})

    def draw(self):

        if not self.visible:
            return

        rows = list(self.cached_lap_standings.items())[:22]
        previous_order = list(self.current_driver_standings.keys())
        _draw_standings_panel("DRIVER STANDINGS", self.x, self.y, 200, [
            (driver, tuple(self.driver_colors.get(driver, (200, 200, 200))), pts,
             pts - self.current_driver_standings.get(driver, 0),
             (previous_order.index(driver) + 1 if driver in previous_order else pos) - pos)
            for pos, (driver, pts) in enumerate(rows, start=1)
        ])

class RaceStatusComponent(BaseComponent):
    """Top-left glass card: current lap, race clock, playback speed and track status."""

    TRACK_STATUS = {
        "2": ("YELLOW FLAG", (255, 214, 10)),
        "4": ("SAFETY CAR", (255, 140, 0)),
        "5": ("RED FLAG", hud.F1_RED),
        "6": ("VIRTUAL SC", (255, 186, 90)),
        "7": ("VSC ENDING", (255, 186, 90)),
    }

    def __init__(self, left=20, width=300, height=120):
        self.left = left
        self.width = width
        self.height = height

    def draw(self, window, lap, total_laps, time_str, playback_speed, track_status):
        top = window.height - 20
        left = self.left
        hud.draw_panel(left, top - self.height, self.width, self.height)

        # Lap counter
        hud.draw_section_title("LAP", left + 16, top - 14)
        lap_label = cached_text(str(lap), left + 16, top - 54, hud.TEXT, 26,
                                font_name=hud.DISPLAY_FONT, anchor_y="center")
        lap_label.draw()
        if total_laps:
            cached_text(f"/{total_laps}", left + 22 + lap_label.content_width, top - 60, hud.TEXT_DIM, 13,
                        font_name=hud.DISPLAY_FONT, anchor_y="center").draw()

        # Race clock
        clock_x = left + 160
        hud.draw_section_title("RACE TIME", clock_x, top - 14)
        cached_text(time_str, clock_x, top - 52, hud.TEXT, 15, font_name=hud.DISPLAY_FONT, anchor_y="center").draw()

        # Bottom row: playback speed and track status pills
        row_y = round(top - self.height + 22)
        speed_text = f"{playback_speed}x"
        hud.draw_pill(left + 16 + 28, row_y, 56, 22)
        cached_text(speed_text, left + 44, row_y, hud.TEXT, 11, bold=True,
                    anchor_x="center", anchor_y="center").draw()

        label, color = self.TRACK_STATUS.get(str(track_status), ("GREEN FLAG", hud.GREEN))
        flagged = str(track_status) in self.TRACK_STATUS
        pill_w = 132
        pill_cx = left + 16 + 56 + 10 + pill_w / 2
        hud.draw_pill(pill_cx, row_y, pill_w, 22,
                      fill=(*color[:3], 200 if flagged else 36), border=(*color[:3], 220 if flagged else 90))
        text_color = (20, 20, 24) if flagged and str(track_status) != "5" else (hud.TEXT if flagged else color)
        cached_text(label, pill_cx, row_y, text_color, 11, bold=True,
                    anchor_x="center", anchor_y="center").draw()


class SessionInfoComponent(BaseComponent):
    """
    Displays session information banner at the top-center of the screen.
    Shows: Circuit name, Country, Event name, Year, Round, Date, Total laps
    """
    def __init__(self, visible=True):
        self.visible = visible
        self.session_info = {}
        self._text = arcade.Text("", 0, 0, arcade.color.WHITE, 14)
        
    def set_info(self, event_name: str = "", circuit_name: str = "", country: str = "",
                 year: int = None, round_num: int = None, date: str = "", total_laps: int = None):
        """Set session information to display"""
        self.session_info = {
            'event_name': event_name,
            'circuit_name': circuit_name,
            'country': country,
            'year': year,
            'round': round_num,
            'date': date,
            'total_laps': total_laps
        }
    
    def toggle_visibility(self) -> bool:
        """Toggle visibility of session info banner"""
        self.visible = not self.visible
        return self.visible
    
    def draw(self, window):
        if not self.visible or not self.session_info:
            return
        
        # Glass banner between the lap card (left) and the leaderboard (right)
        banner_height = 56
        banner_width = max(320, min(760, window.width - 2 * 360))
        center_x = window.width / 2
        top_y = window.height - 20
        hud.draw_panel(center_x - banner_width / 2, top_y - banner_height, banner_width, banner_height)

        # Get info
        event = self.session_info.get('event_name', '')
        circuit = self.session_info.get('circuit_name', '')
        country = self.session_info.get('country', '')
        year = self.session_info.get('year', '')
        round_num = self.session_info.get('round', '')
        date = self.session_info.get('date', '')
        total_laps = self.session_info.get('total_laps', '')

        # Line 1: event name, with the country flag (or a red accent mark) in front
        title = str(event or circuit).upper()
        flag = hud.flag_texture(country)
        mark_w = flag.width / 2 if flag else 4
        title_label = cached_text(title, round(center_x + (mark_w + 10) / 2), top_y - 20, hud.TEXT, 12,
                                  font_name=hud.DISPLAY_FONT, anchor_x="center", anchor_y="center")
        mark_right = center_x - title_label.content_width / 2 + (mark_w + 10) / 2 - 10
        if flag:
            arcade.draw_texture_rect(flag, arcade.LBWH(round(mark_right - mark_w), top_y - 29, mark_w, flag.height / 2))
        else:
            arcade.draw_lrbt_rectangle_filled(mark_right - 4, mark_right, top_y - 27, top_y - 13, hud.F1_RED)
        title_label.draw()

        # Line 2: Circuit · Country · Year Round X · Date · X Laps
        parts = []
        if circuit and circuit != event:
            parts.append(circuit)
        if country:
            parts.append(str(country))
        if year and round_num:
            parts.append(f"{year} Round {round_num}")
        elif year:
            parts.append(str(year))
        if date:
            parts.append(str(date))
        if total_laps:
            parts.append(f"{total_laps} Laps")

        cached_text("  ·  ".join(parts), center_x, top_y - 41, hud.TEXT_DIM, 12,
                    anchor_x="center", anchor_y="center").draw()


# Feature: race progress bar with event markers
class RaceProgressBarComponent(BaseComponent):
    """
    A visual progress bar showing race timeline with event markers:
    - DNF markers (red X)
    - Lap transition markers (vertical lines)
    - Flag markers (red/yellow rectangles)
    
    Uses best practices:
    - Single responsibility: only handles progress bar rendering
    - Efficient rendering with cached markers
    - Clear separation of concerns for event detection
    """
    
    # Event type constants for clear identification
    EVENT_DNF = "dnf"
    EVENT_LAP = "lap"
    EVENT_YELLOW_FLAG = "yellow_flag"
    EVENT_RED_FLAG = "red_flag"
    EVENT_SAFETY_CAR = "safety_car"
    EVENT_VSC = "vsc"
    
    # Color palette following F1 conventions
    COLORS = {
        "background": (255, 255, 255, 30),
        "progress_fill": hud.F1_RED,
        "progress_border": (255, 255, 255, 40),
        "dnf": (255, 90, 80),
        "lap_marker": (255, 255, 255, 34),
        "yellow_flag": (255, 214, 10),
        "red_flag": (225, 6, 0),
        "safety_car": (255, 140, 0),
        "vsc": (255, 186, 90),
        "text": hud.TEXT_FAINT,
        "current_position": (255, 255, 255),
    }
    
    def __init__(self, 
                 left_margin: int = 340, 
                 right_margin: int = 260,
                 bottom: int = 30,
                 height: int = 24,
                 marker_height: int = 16):
        """
        Initialize the progress bar component.
        
        Args:
            left_margin: Left margin from window edge
            right_margin: Right margin from window edge
            bottom: Distance from bottom of window
            height: Height of the progress bar
            marker_height: Height of event markers
        """
        self.left_margin = left_margin
        self.right_margin = right_margin
        self.bottom = bottom
        self.height = height
        self.marker_height = marker_height
        
        self._visible: bool = False
        
        # Cached data
        self._events: List[dict] = []
        self._total_frames: int = 0
        self._total_laps: int = 0
        self._bar_left: float = 0
        self._bar_width: float = 0
        
        # Hover state for tooltips
        self._hover_event: Optional[dict] = None
        self._mouse_x: float = 0
        self._mouse_y: float = 0
        
    def set_race_data(self, 
                      total_frames: int, 
                      total_laps: int,
                      events: List[dict]):
        """
        set the race data for the progress bar so the calc for markers can be done once time
        
        - total_frames: Total number of frames in the race
        - total_laps: Total number of laps in the race
        - events: List of event dictionaries with keys
        """
        self._total_frames = max(1, total_frames)
        self._total_laps = total_laps or 1
        self._events = sorted(events, key=lambda e: e.get("frame", 0))
    
    @property
    def visible(self) -> bool:
        return self._visible
    
    @visible.setter
    def visible(self, value: bool):
        self._visible = value
    
    def toggle_visibility(self) -> bool:
        """
        Toggle the visibility of the progress bar
        """
        self._visible = not self._visible
        
        # Also hide/show related components
        for comp in getattr(self, "_related_components", []):
            if isinstance(comp, BaseComponent):
                comp.visible = self._visible
                
        return self._visible
        
    def _calculate_bar_dimensions(self, window):
        self._bar_left = self.left_margin
        self._bar_width = max(100, window.width - self.left_margin - self.right_margin)
        
    def _frame_to_x(self, frame: int, clamp: bool = True) -> float:
        """
        well here convert a frame number to an X position on the bar
        this must receive clamp=True to prevent out-of-bounds rendering
        Args:
            frame: Frame number to convert
            clamp: Whether to clamp frame to valid range [0, total_frames]
        """
        if self._total_frames <= 0:
            return self._bar_left
        
        # here we use Clamp frame to valid range to prevent rendering outside bar bounds
        if clamp:
            frame = max(0, min(frame, self._total_frames))
        
        progress = frame / self._total_frames
        return self._bar_left + (progress * self._bar_width)
    
    def _x_to_frame(self, x: float) -> int:
        # reverse of _frame_to_x
        if self._bar_width <= 0:
            return 0
        progress = (x - self._bar_left) / self._bar_width
        return int(progress * self._total_frames)
        
    def on_resize(self, window):
        self._calculate_bar_dimensions(window)
        
    def draw(self, window):
        """Render the progress bar with all markers"""
        # Skip rendering entirely if hidden
        if not self._visible:
            return

        self._calculate_bar_dimensions(window)

        current_frame = int(getattr(window, 'frame_index', 0))

        bar_center_y = self.bottom + self.height / 2
        track_h = 6

        # 1. Glass panel, track, lap ticks and event markers only change on resize,
        #    so they are built once as a shape list.
        key = ("progress-static", self._bar_left, self._bar_width, self.bottom, self.height,
               self._total_laps, self._total_frames, len(self._events))
        hud.draw_panel(self._bar_left - 14, self.bottom - 20, self._bar_width + 28, self.height + self.marker_height + 26,
                       radius=12)
        hud.cached_shapes(key, lambda: self._build_static_shapes(bar_center_y, track_h)).draw()

        # Lap numbers for first/last and every 10 laps
        if self._total_laps > 1:
            for lap in range(1, self._total_laps + 1):
                if lap == 1 or lap == self._total_laps or lap % 10 == 0:
                    lap_x = self._frame_to_x(int((lap / self._total_laps) * self._total_frames))
                    cached_text(
                        str(lap),
                        lap_x, self.bottom - 2,
                        self.COLORS["text"], 9,
                        anchor_x="center", anchor_y="top"
                    ).draw()

        # 2. Progress fill
        current_x = self._frame_to_x(current_frame)
        if current_x > self._bar_left:
            arcade.draw_lrbt_rectangle_filled(self._bar_left, current_x,
                                              bar_center_y - track_h / 2, bar_center_y + track_h / 2,
                                              self.COLORS["progress_fill"])

        # 3. Playhead knob
        arcade.draw_circle_filled(current_x, bar_center_y, 8, (*hud.F1_RED, 90))
        arcade.draw_circle_filled(current_x, bar_center_y, 5.5, self.COLORS["current_position"])

        # 4. Draw legend
        self._draw_legend(window)

    def _build_static_shapes(self, bar_center_y, track_h):
        sl = arcade.shape_list
        bar_right = self._bar_left + self._bar_width
        yield sl.create_polygon(
            hud._rounded_points(self._bar_left, bar_center_y - track_h / 2, self._bar_width, track_h, track_h / 2),
            self.COLORS["background"],
        )
        if self._total_laps > 1:
            for lap in range(1, self._total_laps):
                lap_x = self._frame_to_x(int((lap / self._total_laps) * self._total_frames))
                yield sl.create_line(lap_x, bar_center_y - 7, lap_x, bar_center_y + 7, self.COLORS["lap_marker"], 1)
        for event in self._events:
            yield from self._event_marker_shapes(event, self._frame_to_x(event.get("frame", 0)))

    # 7. Draw tooltips and overlays after the main draw to prevent them being occluded
    def draw_overlays(self, window):
        """Draw tooltips and other overlays that should appear on top of all UI elements."""
        if not self._visible:
            return
        # Draw hover tooltip if applicable
        if self._hover_event:
            self._draw_tooltip(window, self._hover_event)
            
    def _event_marker_shapes(self, event: dict, x: float):
        """Shapes for a single event marker based on type."""
        event_type = event.get("type", "")
        marker_top = self.bottom + self.height + self.marker_height

        if event_type == self.EVENT_DNF:
            # Small red X above the bar
            size = 4
            color = self.COLORS["dnf"]
            y = marker_top - size - 2
            yield arcade.shape_list.create_line(x - size, y - size, x + size, y + size, color, 2)
            yield arcade.shape_list.create_line(x - size, y + size, x + size, y - size, color, 2)
            return

        color = {
            self.EVENT_YELLOW_FLAG: self.COLORS["yellow_flag"],
            self.EVENT_RED_FLAG: self.COLORS["red_flag"],
            self.EVENT_SAFETY_CAR: self.COLORS["safety_car"],
            self.EVENT_VSC: self.COLORS["vsc"],
        }.get(event_type)
        if color is not None:
            segment = self._flag_segment_rect(event)
            if segment:
                yield arcade.shape_list.create_rectangle_filled(*segment, color)

    def _flag_segment_rect(self, event: dict):
        """(center_x, center_y, width, height) of a flag period above the bar, or None if not visible."""
        start_frame = event.get("frame", 0)
        end_frame = event.get("end_frame", start_frame + 100)  # default duration

        clamped_start = max(0, min(start_frame, self._total_frames))
        clamped_end = max(0, min(end_frame, self._total_frames))

        if clamped_start >= clamped_end:
            # after clamping, if start >= end, the segment is fully outside the
            # visible race window (e.g., flag ended before frame 0)
            return None

        # Convert clamped frames to X positions, clamped to the bar boundaries
        bar_right = self._bar_left + self._bar_width
        start_x = max(self._bar_left, min(self._frame_to_x(clamped_start), bar_right))
        end_x = max(self._bar_left, min(self._frame_to_x(clamped_end), bar_right))

        segment_width = end_x - start_x
        if segment_width <= 0:
            return None

        # Ensure minimum width for visibility (thin flags are hard to see)
        segment_width = max(4, segment_width)
        return (start_x + segment_width / 2, self.bottom + self.height + 3, segment_width, 4)

    def _draw_tooltip(self, window, event: dict):
        event_type = event.get("type", "")
        label = event.get("label", "")
        lap = event.get("lap", "")
        
        # Build tooltip text
        type_names = {
            self.EVENT_DNF: "DNF",
            self.EVENT_YELLOW_FLAG: "Yellow Flag",
            self.EVENT_RED_FLAG: "Red Flag",
            self.EVENT_SAFETY_CAR: "Safety Car",
            self.EVENT_VSC: "Virtual SC",
        }
        
        tooltip_text = type_names.get(event_type, "Event")
        if label:
            tooltip_text = f"{tooltip_text}: {label}"
        if lap:
            tooltip_text = f"{tooltip_text} (Lap {lap})"
            
        # Calculate position
        event_x = self._frame_to_x(event.get("frame", 0))
        tooltip_x = min(max(event_x, 100), window.width - 100)
        tooltip_y = self.bottom + self.height + self.marker_height + 20
        
        # Tooltip as a glass pill
        label = cached_text(tooltip_text, tooltip_x, tooltip_y, hud.TEXT, 12,
                            anchor_x="center", anchor_y="center")
        width = label.content_width + 24
        hud.draw_panel(tooltip_x - width / 2, tooltip_y - 13, width, 26, radius=13, fill=(20, 22, 29, 240))
        label.draw()

    def _draw_legend(self, window):
        """Draw a small legend explaining the markers."""
        legend_items = [
            (self.COLORS["yellow_flag"], "Yellow"),
            (self.COLORS["red_flag"], "Red"),
            (self.COLORS["safety_car"], "SC"),
            (self.COLORS["vsc"], "VSC"),
        ]

        legend_x = self._bar_left + self._bar_width + 50
        legend_y = self.bottom + self.height / 2

        for i, (color, label) in enumerate(legend_items):
            x = legend_x + (i * 45)
            arcade.draw_circle_filled(x, legend_y + 4, 3.5, color)
            cached_text(
                label,
                x, legend_y - 4,
                self.COLORS["text"], 9,
                anchor_x="center", anchor_y="top"
            ).draw()

    def on_mouse_motion(self, window, x: float, y: float, dx: float, dy: float):
        """Handle mouse motion for hover effects."""
        if not self._visible:
            return
            
        self._mouse_x = x
        self._mouse_y = y
        
        # Check if mouse is over the progress bar area
        if (self._bar_left <= x <= self._bar_left + self._bar_width and
            self.bottom <= y <= self.bottom + self.height + self.marker_height + 10):
            
            # Find nearest event
            mouse_frame = self._x_to_frame(x)
            nearest_event = None
            min_dist = float('inf')
            
            for event in self._events:
                event_frame = event.get("frame", 0)
                dist = abs(event_frame - mouse_frame)
                if dist < min_dist and dist < self._total_frames * 0.02:  # Within 2% of timeline
                    min_dist = dist
                    nearest_event = event
                    
            self._hover_event = nearest_event
        else:
            self._hover_event = None
            
    def on_mouse_press(self, window, x: float, y: float, button: int, modifiers: int):
        """Handle mouse click to seek to position."""
        if not self._visible:
            return False
            
        if (self._bar_left <= x <= self._bar_left + self._bar_width and
            self.bottom - 5 <= y <= self.bottom + self.height + 5):
            
            # Seek to clicked position
            target_frame = self._x_to_frame(x)
            if hasattr(window, 'frame_index'):
                window.frame_index = float(max(0, min(target_frame, self._total_frames - 1)))
            return True
        return False

# Feature: control race playback (play/pause, speed control, rewind/fast-forward)
class RaceControlsComponent(BaseComponent):
    """
    A visual component with playback control buttons:
    - Rewind button (left)
    - Play/Pause button (center)
    - Forward button (right)
    """
    
    PLAYBACK_SPEEDS = [0.1, 0.2, 0.5, 1.0, 2.0, 4.0, 8.0, 16.0, 32.0, 64.0, 128.0, 256.0]

    def __init__(self, center_x: int = 100, center_y: int = 60, button_size: int = 40, visible=True):
        self.center_x = center_x
        self.center_y = center_y
        self.button_size = button_size
        self.button_spacing = 70
        self.speed_container_offset = 200
        self._hide_speed_text = False
        self._control_textures = {}
        self._visible = visible
        
        # Button rectangles for hit testing
        self.rewind_rect = None
        self.play_pause_rect = None
        self.forward_rect = None
        self.speed_increase_rect = None
        self.speed_decrease_rect = None
        
        # Hover state
        self.hover_button = None  # 'rewind/forward', 'play/pause', 'speed_increase', 'speed_decrease'
        # Flash feedback state for keyboard shortcuts
        self._flash_button = None
        self._flash_timer = 0.0
        self._flash_duration = 0.3  # seconds

        _controls_folder = os.path.join("images", "controls")
        if os.path.exists(_controls_folder):
            for filename in os.listdir(_controls_folder):
                if filename.lower().endswith(('.png', '.jpg', '.jpeg')):
                    texture_name = os.path.splitext(filename)[0]
                    texture_path = os.path.join(_controls_folder, filename)
                    self._control_textures[texture_name] = arcade.load_texture(texture_path)

    @property
    def visible(self) -> bool:
        return self._visible
    
    @visible.setter
    def visible(self, value: bool):
        self._visible = value
    
    def toggle_visibility(self) -> bool:
        """
        Toggle the visibility of the controls
        """
        self._visible = not self._visible

    def set_visible(self):
        """
        Set visibility of controls to True
        """
        self._visible = True

    def on_resize(self, window):
        """Recalculate control positions on window resize."""
        self.center_x = window.width / 2
        # Scale spacing and offset proportionally to window width (based on 1920px reference)
        self.button_spacing = window.width * (70 / 1920)
        self.speed_container_offset = window.width * (200 / 1920)
        self._hide_speed_text = window.width < 1000
    
    def on_update(self, delta_time: float):
        """Update flash timer for keyboard feedback animation."""
        if self._flash_timer > 0:
            self._flash_timer = max(0, self._flash_timer - delta_time)
            if self._flash_timer == 0:
                self._flash_button = None
    
    def flash_button(self, button_name: str):
        """Trigger a visual flash effect for a button (used for keyboard feedback)."""
        self._flash_button = button_name
        self._flash_timer = self._flash_duration

    def draw(self, window):
        """Draw the three playback control buttons."""
        # Skip rendering entirely if hidden
        if not self._visible:
            return
        is_paused = getattr(window, 'paused', False)

        # Button positions
        rewind_x = self.center_x - self.button_spacing
        play_x = self.center_x
        forward_x = self.center_x + self.button_spacing

        # Glass dock behind the transport buttons
        dock_w = 2 * self.button_spacing + self.button_size + 24
        dock_h = self.button_size + 16
        hud.draw_panel(self.center_x - dock_w / 2, self.center_y - dock_h / 2, dock_w, dock_h, radius=dock_h / 2)

        self._draw_rewind_icon(rewind_x, self.center_y)

        if is_paused:
            self._draw_play_icon(play_x, self.center_y)
        else:
            self._draw_pause_icon(play_x, self.center_y)

        self._draw_forward_icon(forward_x, self.center_y)

        self._draw_speed_comp(forward_x + self.speed_container_offset, self.center_y, getattr(window, 'playback_speed', 1.0))

    def draw_hover_effect(self, button_name: str, x: float, y: float, radius_offset: int = 2, border_width: int = 4):
        """Draw hover outline effect for a button if it's currently hovered."""
        radius = self.button_size // 2 + radius_offset
        if self.hover_button == button_name and getattr(self, f"{button_name}_rect", None):
            arcade.draw_circle_outline(x, y, radius, (255, 255, 255, 150), 2)

        # Show flash effect for keyboard feedback
        if self._flash_button == button_name and self._flash_timer > 0:
            # Fading ring based on timer
            alpha = int(200 * (self._flash_timer / self._flash_duration))
            arcade.draw_circle_outline(x, y, radius + 2, (*hud.F1_RED, alpha), 3)

    def _button_rect(self, x: float, y: float):
        half = self.button_size // 2
        return (x - half, y - half, x + half, y + half)

    def _draw_round_button(self, x: float, y: float, primary: bool = False):
        r = self.button_size / 2
        if primary:
            arcade.draw_circle_filled(x, y, r, hud.F1_RED)
        else:
            arcade.draw_circle_filled(x, y, r - 3, (255, 255, 255, 26))

    def _draw_play_icon(self, x: float, y: float):
        self.play_pause_rect = self._button_rect(x, y)
        self._draw_round_button(x, y, primary=True)
        s = self.button_size * 0.2
        arcade.draw_triangle_filled(x - s * 0.7, y - s, x - s * 0.7, y + s, x + s, y, hud.TEXT)
        self.draw_hover_effect('play_pause', x, self.center_y)

    def _draw_pause_icon(self, x: float, y: float):
        self.play_pause_rect = self._button_rect(x, y)
        self._draw_round_button(x, y, primary=True)
        s = self.button_size * 0.18
        arcade.draw_lrbt_rectangle_filled(x - s, x - s * 0.35, y - s, y + s, hud.TEXT)
        arcade.draw_lrbt_rectangle_filled(x + s * 0.35, x + s, y - s, y + s, hud.TEXT)
        self.draw_hover_effect('play_pause', x, self.center_y)

    def _draw_double_arrow(self, x: float, y: float, direction: int):
        s = self.button_size * 0.15
        for offset in (-s * 0.85, s * 0.85):
            cx = x + offset
            arcade.draw_triangle_filled(cx - direction * s, y - s, cx - direction * s, y + s, cx + direction * s, y, hud.TEXT)

    def _draw_forward_icon(self, x: float, y: float):
        self.forward_rect = self._button_rect(x, y)
        self._draw_round_button(x, y)
        self._draw_double_arrow(x, y, 1)
        self.draw_hover_effect('forward', x, self.center_y)

    def _draw_rewind_icon(self, x: float, y: float):
        self.rewind_rect = self._button_rect(x, y)
        self._draw_round_button(x, y)
        self._draw_double_arrow(x, y, -1)
        self.draw_hover_effect('rewind', x, self.center_y)

    def _draw_speed_comp(self, x: float, y: float, speed: float):
        """Draw the speed multiplier with - / + buttons in a glass pill."""
        small = self.button_size * 0.7
        if self._hide_speed_text:
            container_width = small * 2 + 24
        else:
            container_width = small * 2 + 76
        container_height = self.button_size + 16
        hud.draw_panel(x - container_width / 2, y - container_height / 2, container_width, container_height,
                       radius=container_height / 2)

        # Button positions inside container
        button_offset = container_width / 2 - small / 2 - 8
        minus_x, plus_x = x - button_offset, x + button_offset

        half = self.button_size // 2
        self.speed_decrease_rect = (minus_x - half, y - half, minus_x + half, y + half)
        self.speed_increase_rect = (plus_x - half, y - half, plus_x + half, y + half)

        for bx in (minus_x, plus_x):
            arcade.draw_circle_filled(bx, y, small / 2, (255, 255, 255, 26))
        bar = small * 0.32
        arcade.draw_lrbt_rectangle_filled(minus_x - bar, minus_x + bar, y - 1, y + 1, hud.TEXT)
        arcade.draw_lrbt_rectangle_filled(plus_x - bar, plus_x + bar, y - 1, y + 1, hud.TEXT)
        arcade.draw_lrbt_rectangle_filled(plus_x - 1, plus_x + 1, y - bar, y + bar, hud.TEXT)

        # Speed text in the centre
        if not self._hide_speed_text:
            cached_text(f"{speed}x", x, y, hud.TEXT, 11, font_name=hud.DISPLAY_FONT,
                        anchor_x="center", anchor_y="center").draw()

        # Hover highlights for speed buttons
        self.draw_hover_effect('speed_increase', plus_x, y, radius_offset=-5, border_width=2)
        self.draw_hover_effect('speed_decrease', minus_x, y, radius_offset=-5, border_width=2)

    def on_mouse_motion(self, window, x: float, y: float, dx: float, dy: float):
        """Handle mouse hover effects."""
        if self._point_in_rect(x, y, self.rewind_rect):
            self.hover_button = 'rewind'
        elif self._point_in_rect(x, y, self.play_pause_rect):
            self.hover_button = 'play_pause'
        elif self._point_in_rect(x, y, self.forward_rect):
            self.hover_button = 'forward'
        elif self._point_in_rect(x, y, self.speed_increase_rect):
            self.hover_button = 'speed_increase'
        elif self._point_in_rect(x, y, self.speed_decrease_rect):
            self.hover_button = 'speed_decrease'
        else:
            self.hover_button = None
        return False
    
    def on_mouse_press(self, window, x: float, y: float, button: int, modifiers: int):
        """Handle button clicks."""
        if self._point_in_rect(x, y, self.rewind_rect):
            # Update: Support hold-to-rewind
            if hasattr(window, 'is_rewinding'):
                window.was_paused_before_hold = window.paused
                window.is_rewinding = True
                window.paused = True
            elif hasattr(window, 'frame_index'):
                window.frame_index = int(max(0, window.frame_index - 10))
            return True
        elif self._point_in_rect(x, y, self.play_pause_rect):
            if hasattr(window, 'paused'):
                window.paused = not window.paused
            return True
        elif self._point_in_rect(x, y, self.forward_rect):
            # Update: Support hold-to-forward
            if hasattr(window, 'is_forwarding'):
                window.was_paused_before_hold = window.paused
                window.is_forwarding = True
                window.paused = True
            elif hasattr(window, 'frame_index') and hasattr(window, 'n_frames'):
                window.frame_index = int(min(window.n_frames - 1, window.frame_index + 10))
            return True
        elif self._point_in_rect(x, y, self.speed_increase_rect):
            if hasattr(window, 'playback_speed'):
                # FIX: Use index lookup to increment speed.
                if window.playback_speed < max(self.PLAYBACK_SPEEDS):
                    current_index = self.PLAYBACK_SPEEDS.index(window.playback_speed)
                    window.playback_speed = self.PLAYBACK_SPEEDS[min(current_index + 1, len(self.PLAYBACK_SPEEDS) - 1)]
                    self.flash_button('speed_increase')
            return True
        elif self._point_in_rect(x, y, self.speed_decrease_rect):
            if hasattr(window, 'playback_speed'):
                # FIX: Use index lookup to decrement speed safely within defined PLAYBACK_SPEEDS.
                if window.playback_speed > min(self.PLAYBACK_SPEEDS):
                    current_index = self.PLAYBACK_SPEEDS.index(window.playback_speed)
                    window.playback_speed = self.PLAYBACK_SPEEDS[max(0, current_index - 1)]
                    self.flash_button('speed_decrease')
            return True
        return False
    
    def _point_in_rect(self, x: float, y: float, rect: tuple[float, float, float, float] | None) -> bool:
        """Check if point is inside rectangle."""
        if rect is None:
            return False
        left, bottom, right, top = rect
        return left <= x <= right and bottom <= y <= top

class QualifyingLapTimeComponent(BaseComponent):
    """
    A component to display the qualifying lap time with sector times and current tyre info.
    """
    def __init__(self, x: int = 150, y: int = 60):
        self.x = x
        self.y = y
        self.fastest_driver = None
        self.fastest_driver_sector_times = None
        self._tyre_textures = {}
        self._time_elapsed = 0.0
        self._delta_sector = None
        self._last_completed_sector = -1
        # Import the tyre textures from the images/tyres folder (all files)
        tyres_folder = os.path.join("images", "tyres")
        if os.path.exists(tyres_folder):
            for filename in os.listdir(tyres_folder):
                if filename.lower().endswith(('.png', '.jpg', '.jpeg')):
                    texture_name = os.path.splitext(filename)[0]
                    texture_path = os.path.join(tyres_folder, filename)
                    self._tyre_textures[texture_name] = arcade.load_texture(texture_path)

    def on_update(self, delta_time: float):
        """
        Update logic for time difference in fastest driver and current driver (Delta sector time)
        """
        if self._delta_sector is not None:
            self._time_elapsed += delta_time
            if self._time_elapsed >= 1.0:
                # Reset delta display after 1 second (but keep sector completion tracking)
                self._delta_sector = None
                self._time_elapsed = 0.0

    def reset(self):
        self._delta_sector = None
        self._time_elapsed = 0.0
        self._last_completed_sector = -1

    def draw(self, window):
        if not hasattr(window, 'loaded_telemetry') or not window.loaded_telemetry:
            return
        sector_times = window.loaded_telemetry.get("sector_times") if isinstance(window.loaded_telemetry, dict) else {}
        if not sector_times:
            sector_times = {}
        compound = window.loaded_telemetry.get("compound", "?")
        
        # Get driver info
        driver_full_name = None
        fastest_driver_full_name = None
        driver_color = arcade.color.ANTI_FLASH_WHITE
        driver_code = getattr(window, 'loaded_driver_code', None)
        if driver_code:
            telemetry = window.data.get("telemetry")
            if telemetry:
                driver_full_name = telemetry.get(driver_code, {}).get("full_name")
                if self.fastest_driver:
                    fastest_driver_full_name = telemetry.get(self.fastest_driver.get("code"), {}).get("full_name")
                # Get color from results
                for result in window.data.get("results", []):
                    if result.get("code") == driver_code:
                        driver_color = tuple(result.get("color", arcade.color.ANTI_FLASH_WHITE))
                        break

        # Get current time from window
        frames = window.loaded_telemetry.get("frames") if isinstance(window.loaded_telemetry, dict) else None
        if not frames:
            return
        current_frame = frames[window.frame_index]
        current_t = current_frame.get("t", 0.0)
        formatted_time = format_time(current_t)
        
        rect = arcade.XYWH(self.x + 125, self.y - 65, 250, 120)
        
        arcade.draw_rect_filled(rect, (20, 20, 20, 255))

        cached_text(f"{driver_full_name}", self.x + 10, self.y - 30, driver_color, 16, bold=True).draw()
        
        #Display tyre compound texture
        rect = arcade.XYWH(self.x + 220, self.y - 22, 24, 24)
        texture_key = f"{compound}.0" if isinstance(compound, (int, float)) else None
        tyre_texture = self._tyre_textures.get(texture_key) if texture_key else None
        
        if tyre_texture:
            arcade.draw_texture_rect(
                rect=rect,
                texture=tyre_texture,
                angle=0,
                alpha=255
            )

        arcade.draw_line(self.x, self.y - 40, self.x + 250, self.y - 40, arcade.color.ANTI_FLASH_WHITE, 3)

        cached_text(f"{formatted_time}", self.x + 10, self.y - 70, arcade.color.ANTI_FLASH_WHITE, 18, anchor_x="left", bold=True).draw()

        if self.fastest_driver_sector_times and fastest_driver_full_name and fastest_driver_full_name != driver_full_name:
            fastest_last_name = fastest_driver_full_name.split(" ")[-1]
            cached_text(f"{fastest_last_name}", self.x + 150, self.y - 85, arcade.color.LIGHT_GRAY, 13, anchor_x="left").draw()

        #show sector times over the labels
        sector_configs = [
            ("sector1", self.x + 45, 0),
            ("sector2", self.x + 125, 1),
            ("sector3", self.x + 205, 2)
        ]
        
        cumulative_time = 0
        cumulative_fastest_time = 0
        epsilon = 0.01  # Small tolerance for floating-point comparison
        
        for sector_key, x_pos, sector_idx in sector_configs:
            sector_time = sector_times.get(sector_key)
            fastest_sector_time = None
            delta_sector_time = None
            if self.fastest_driver_sector_times:
                fastest_sector_time = self.fastest_driver_sector_times.get(sector_key)
                cumulative_fastest_time += fastest_sector_time if fastest_sector_time is not None else 0
                delta_sector_time = sector_time - fastest_sector_time if sector_time is not None and fastest_sector_time is not None else None
            
            formatted_fastest_sector_time = format_time(cumulative_fastest_time)
            text_color = arcade.color.ANTI_FLASH_WHITE
            
            # Calculate elapsed time in current sector
            # Sector 1 uses absolute time, others use time relative to cumulative
            elapsed_in_sector = current_t if sector_idx == 0 else current_t - cumulative_time

            # Check if sector has started (only applicable for sectors 2 and 3)
            if sector_idx > 0 and current_t < cumulative_time - epsilon:
                text = "-"

            # Check if sector is completed
            elif sector_time and sector_time <= elapsed_in_sector + epsilon:
                text, text_color = self.show_delta_sector_times(sector_idx, sector_time, delta_sector_time, text_color)
                # Draw green bar below completed sector
                bar_width = 40 if sector_idx == 0 else 45
                arcade.draw_line(x_pos - 45, self.y - 125, x_pos + bar_width, self.y - 125, arcade.color.GREEN, 3)
                if sector_idx == 2 and fastest_sector_time is not None:
                    cached_text(f"{formatted_fastest_sector_time}s", self.x + 150, self.y - 65, arcade.color.LIGHT_GRAY, 13, anchor_x="left").draw()

            # Sector in progress - show current elapsed time
            else:
                text = f"{elapsed_in_sector:.1f}s"
                if fastest_sector_time is not None:
                    cached_text(f"{formatted_fastest_sector_time}s", self.x + 150, self.y - 65, arcade.color.LIGHT_GRAY, 13, anchor_x="left").draw()
            
            # Always draw the sector time text
            cached_text(text, x_pos, self.y - 105, text_color, 12, anchor_x="center", bold=True).draw()
            
            # Always update cumulative time for next sector
            if sector_time is not None:
                cumulative_time += sector_time
        
        # Draw sector labels once after processing all sectors
        self.draw_sector_labels(sector_times, current_t)

    def draw_sector_labels(self, sector_times, current_t):
        s1_time = sector_times.get("sector1") or 0
        s1_color = arcade.color.GREEN if s1_time > 0 and current_t >= s1_time else arcade.color.LIGHT_GRAY
        cached_text("S1", self.x + 35, self.y - 120, s1_color, 9, bold=True).draw()

        s2_val = sector_times.get("sector2") or 0
        s2_time = s1_time + s2_val
        s2_color = arcade.color.GREEN if s2_time > 0 and current_t >= s2_time else arcade.color.LIGHT_GRAY
        cached_text("S2", self.x + 115, self.y - 120, s2_color, 9, bold=True).draw()
        
        s3_val = sector_times.get("sector3") or 0
        s3_time = s2_time + s3_val
        s3_color = arcade.color.GREEN if s3_time > 0 and current_t >= s3_time else arcade.color.LIGHT_GRAY
        cached_text("S3", self.x + 200, self.y - 120, s3_color, 9, bold=True).draw()      
    
    def show_delta_sector_times(self, sector_idx: int, sector_time: float, delta_sector_time: float | None, text_color: tuple):
        if self._delta_sector == sector_idx and self._time_elapsed < 1.0 and delta_sector_time is not None:
            # Show delta for 1 second
            if delta_sector_time < 0:
                text = f"-{abs(delta_sector_time):.3f}s"
                text_color = arcade.color.GREEN
            else:
                text = f"+{delta_sector_time:.3f}s"
                text_color = arcade.color.YELLOW
        else:
            text = f"{sector_time:.1f}s"
            # Detect if sector just completed to trigger delta display (only once)
            if self._last_completed_sector < sector_idx and delta_sector_time is not None:
                self._delta_sector = sector_idx
                self._time_elapsed = 0.0
                self._last_completed_sector = sector_idx
        return text, text_color

def extract_race_events(frames: List[dict], track_statuses: List[dict], total_laps: int) -> List[dict]:
    """
    Extract race events from frame data for the progress bar.
    
    This function analyzes the telemetry frames to identify:
    - DNF events (when a driver stops appearing)
    - Leader changes (when the P1 position changes hands)
    - Flag events (from track_statuses)
    
    Args:
        frames: List of frame dictionaries from telemetry
        track_statuses: List of track status events
        total_laps: Total number of laps in the race
        
    Returns:
        List of event dictionaries for the progress bar
    """
    events = []
    
    if not frames:
        return events
        
    n_frames = len(frames)
    
    # Track drivers present in each frame
    prev_drivers = set()
    
    # Sample frames at regular intervals for performance (every 25 frames = 1 second)
    sample_rate = 25
    
    for i in range(0, n_frames, sample_rate):
        frame = frames[i]
        drivers_data = frame.get("drivers", {})
        current_drivers = set(drivers_data.keys())
        
        # Detect DNFs (drivers who disappeared)
        if prev_drivers:
            dnf_drivers = prev_drivers - current_drivers
            for driver_code in dnf_drivers:
                # Get the lap from previous frame if available
                prev_frame = frames[max(0, i - sample_rate)]
                driver_info = prev_frame.get("drivers", {}).get(driver_code, {})
                lap = driver_info.get("lap", "?")
                
                events.append({
                    "type": RaceProgressBarComponent.EVENT_DNF,
                    "frame": i,
                    "label": driver_code,
                    "lap": lap,
                })
        
        prev_drivers = current_drivers
    
    # Add flag events from track_statuses
    for status in track_statuses:
        status_code = str(status.get("status", ""))
        start_time = status.get("start_time", 0)
        end_time = status.get("end_time")
        
        # Convert time to frame (assuming 25 FPS)
        fps = 25
        start_frame = int(start_time * fps)
        end_frame = int(end_time * fps) if end_time else start_frame + 250  # Default 10 seconds
        
        # This prevents rendering artifacts from pre-race track status events
        # that shouldn't appear on the timeline... Events that span frame 0
        # (start < 0 but end > 0) are kept; the drawing code will clamp them
        if end_frame <= 0:
            continue
        
        # Note: The drawing code also clamps, but normalizing here improves data quality
        if n_frames > 0:
            end_frame = min(end_frame, n_frames)
        
        event_type = None
        if status_code == "2":  # Yellow flag
            event_type = RaceProgressBarComponent.EVENT_YELLOW_FLAG
        elif status_code == "4":  # Safety Car
            event_type = RaceProgressBarComponent.EVENT_SAFETY_CAR
        elif status_code == "5":  # Red flag
            event_type = RaceProgressBarComponent.EVENT_RED_FLAG
        elif status_code in ("6", "7"):  # VSC
            event_type = RaceProgressBarComponent.EVENT_VSC
            
        if event_type:
            events.append({
                "type": event_type,
                "frame": start_frame,
                "end_frame": end_frame,
                "label": "",
                "lap": None,
            })
    
    return events

# Build track geometry from example lap telemetry
def build_track_from_example_lap(example_lap, track_width=200):
    drs_zones = plotDRSzones(example_lap)
    plot_x_ref = example_lap["X"]
    plot_y_ref = example_lap["Y"]

    # compute tangents
    dx = np.gradient(plot_x_ref)
    dy = np.gradient(plot_y_ref)

    norm = np.sqrt(dx**2 + dy**2)
    norm[norm == 0] = 1.0
    dx /= norm
    dy /= norm

    nx = -dy
    ny = dx

    x_outer = plot_x_ref + nx * (track_width / 2)
    y_outer = plot_y_ref + ny * (track_width / 2)
    x_inner = plot_x_ref - nx * (track_width / 2)
    y_inner = plot_y_ref - ny * (track_width / 2)

    # world bounds
    x_min = min(plot_x_ref.min(), x_inner.min(), x_outer.min())
    x_max = max(plot_x_ref.max(), x_inner.max(), x_outer.max())
    y_min = min(plot_y_ref.min(), y_inner.min(), y_outer.min())
    y_max = max(plot_y_ref.max(), y_inner.max(), y_outer.max())

    return (plot_x_ref, plot_y_ref, x_inner, y_inner, x_outer, y_outer,
            x_min, x_max, y_min, y_max, drs_zones)

# Plot DRS Zones along the track sides to show DRS Zones on the track
def plotDRSzones(example_lap):
   x_val = example_lap["X"]
   y_val = example_lap["Y"]
   drs_zones = []
   drs_start = None

   for i, val in enumerate(example_lap["DRS"]):
       if val in [10, 12, 14]:
           if drs_start is None:
               drs_start = i
       else:
           if drs_start is not None:
               drs_end = i - 1
               zone = {
                   "start": {"x": x_val.iloc[drs_start], "y": y_val.iloc[drs_start], "index": drs_start},
                   "end": {"x": x_val.iloc[drs_end], "y": y_val.iloc[drs_end], "index": drs_end}
               }
               drs_zones.append(zone)
               drs_start = None
   
   # Handle case where DRS zone extends to end of lap
   if drs_start is not None:
       drs_end = len(example_lap["DRS"]) - 1
       zone = {
           "start": {"x": x_val.iloc[drs_start], "y": y_val.iloc[drs_start], "index": drs_start},
           "end": {"x": x_val.iloc[drs_end], "y": y_val.iloc[drs_end], "index": drs_end}
       }
       drs_zones.append(zone)
   
   return drs_zones

def create_finish_line_shapes(start_inner, start_outer, num_squares=20, extension=20):
    """Chequered finish line across the track as shapes for a ShapeElementList."""
    dx = start_outer[0] - start_inner[0]
    dy = start_outer[1] - start_inner[1]
    length = np.sqrt(dx**2 + dy**2)
    if length <= 0:
        return []
    dx_norm, dy_norm = dx / length, dy / length
    x0, y0 = start_inner[0] - extension * dx_norm, start_inner[1] - extension * dy_norm
    x3, y3 = start_outer[0] + extension * dx_norm, start_outer[1] + extension * dy_norm
    shapes = []
    for i in range(num_squares):
        t1, t2 = i / num_squares, (i + 1) / num_squares
        color = arcade.color.WHITE if i % 2 == 0 else arcade.color.BLACK
        shapes.append(arcade.shape_list.create_line(
            x0 + t1 * (x3 - x0), y0 + t1 * (y3 - y0), x0 + t2 * (x3 - x0), y0 + t2 * (y3 - y0), color, 6))
    return shapes


def draw_finish_line(self, session_type = 'R'):
    if(session_type not in ['R', 'Q']):
        print("Invalid session type for finish line drawing...")
        return

    start_inner = None
    start_outer = None

    if(session_type == 'Q' and len(self.inner_pts) > 0 and len(self.outer_pts) > 0):
        start_inner = self.inner_pts[0]
        start_outer = self.outer_pts[0]
    elif(session_type == 'R' and len(self.screen_inner_points) > 0 and len(self.screen_outer_points) > 0):
        start_inner = self.screen_inner_points[0]
        start_outer = self.screen_outer_points[0]
    else:
        return
    
    # Draw checkered finish line
    if start_inner and start_outer:
        num_squares = 20
        extension = 20
            
        # Calculate direction vector and normalize
        dx = start_outer[0] - start_inner[0]
        dy = start_outer[1] - start_inner[1]
        length = np.sqrt(dx**2 + dy**2)
            
        if length > 0:
            # Normalize direction (unit vector)
            dx_norm = dx / length
            dy_norm = dy / length
                
            # Extend line beyond track limits
            extended_inner = (start_inner[0] - extension * dx_norm, 
                             start_inner[1] - extension * dy_norm)
            extended_outer = (start_outer[0] + extension * dx_norm, 
                             start_outer[1] + extension * dy_norm)
            
            # Draw checkered pattern across extended line
            for i in range(num_squares):
                t1 = i / num_squares # start of segment
                t2 = (i + 1) / num_squares # end of segment
                
                x1 = extended_inner[0] + t1 * (extended_outer[0] - extended_inner[0])
                y1 = extended_inner[1] + t1 * (extended_outer[1] - extended_inner[1])
                x2 = extended_inner[0] + t2 * (extended_outer[0] - extended_inner[0])
                y2 = extended_inner[1] + t2 * (extended_outer[1] - extended_inner[1])
                
                color = arcade.color.WHITE if i % 2 == 0 else arcade.color.BLACK
                arcade.draw_line(x1, y1, x2, y2, color, 6)
