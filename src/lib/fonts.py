"""App fonts: Formula1 Display when its files are in fonts/, otherwise the bundled OFL fonts
(Titillium Web for text, Michroma for titles and the leaderboard)."""

import glob
import os

FONT_DIR = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..", "fonts"))

F1_FAMILY = "Formula1 Display"
TEXT_FAMILY = "Titillium Web"
DISPLAY_FAMILY = "Michroma"


def font_files():
    return sorted(glob.glob(os.path.join(FONT_DIR, "*.ttf")) + glob.glob(os.path.join(FONT_DIR, "*.otf")))


def _has_f1_font():
    return any(os.path.basename(f).lower().startswith("formula1") for f in font_files())


def font_family():
    return F1_FAMILY if _has_f1_font() else TEXT_FAMILY


def display_font_family():
    return F1_FAMILY if _has_f1_font() else DISPLAY_FAMILY


def use_app_font_in_arcade():
    """Register the font files with pyglet and make the text font the default for every arcade.Text."""
    import arcade

    for path in font_files():
        arcade.load_font(path)

    family = font_family()
    base_text = arcade.Text

    class AppText(base_text):
        def __init__(self, *args, font_name=(family, "calibri", "arial"), **kwargs):
            super().__init__(*args, font_name=font_name, **kwargs)

    arcade.Text = AppText
