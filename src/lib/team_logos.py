"""Team logo lookup. The logo files live in images/logos and are kept out of git (trademarks)."""

import os

LOGO_DIR = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..", "images", "logos"))

# Substrings of FastF1 TeamName values, checked in order, mapped to a logo file name.
_TEAM_SLUGS = [
    ("red bull", "red-bull"),
    ("racing bulls", "racing-bulls"),
    ("rb f1", "racing-bulls"),
    ("ferrari", "ferrari"),
    ("mercedes", "mercedes"),
    ("mclaren", "mclaren"),
    ("aston martin", "aston-martin"),
    ("alpine", "alpine"),
    ("renault", "renault"),
    ("williams", "williams"),
    ("audi", "audi"),
    ("kick sauber", "sauber"),
    ("stake", "sauber"),
    ("haas", "haas"),
    ("cadillac", "cadillac"),
]


def team_logo_path(team_name):
    """PNG path for a team name, or None when there is no matching file."""
    name = str(team_name or "").lower()
    if name == "rb":
        name = "racing bulls"
    for key, slug in _TEAM_SLUGS:
        if key in name:
            path = os.path.join(LOGO_DIR, slug + ".png")
            return path if os.path.exists(path) else None
    return None
