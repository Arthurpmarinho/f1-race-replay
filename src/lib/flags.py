"""Country flag lookup for the event countries FastF1 reports. Flags: images/flags (flag-icons, MIT)."""

import os

FLAG_DIR = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..", "images", "flags"))

_COUNTRY_CODES = {
    "abu dhabi": "ae", "united arab emirates": "ae", "uae": "ae",
    "argentina": "ar", "australia": "au", "austria": "at", "azerbaijan": "az",
    "bahrain": "bh", "belgium": "be", "brazil": "br", "canada": "ca", "china": "cn",
    "france": "fr", "germany": "de", "great britain": "gb", "united kingdom": "gb", "uk": "gb",
    "hungary": "hu", "india": "in", "italy": "it", "japan": "jp", "korea": "kr", "south korea": "kr",
    "malaysia": "my", "mexico": "mx", "monaco": "mc", "netherlands": "nl", "portugal": "pt",
    "qatar": "qa", "russia": "ru", "saudi arabia": "sa", "singapore": "sg", "south africa": "za",
    "spain": "es", "turkey": "tr", "united states": "us", "usa": "us",
}


def flag_path(country):
    """SVG path for a country name, or None when there is no flag for it."""
    code = _COUNTRY_CODES.get(str(country or "").strip().lower())
    if not code:
        return None
    path = os.path.join(FLAG_DIR, code + ".svg")
    return path if os.path.exists(path) else None
