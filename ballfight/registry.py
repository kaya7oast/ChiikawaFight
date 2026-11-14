"""
Character registry.

SPRITES  - every individual ball (e.g. CHIIKAWA, HACHIWARE, MOMONGA): colour + image file name.
ROSTER   - every selectable team in the [1]/[2] cycle (e.g. the Chiikawa+Hachiware duo, or a solo boss).

Fighter modules call register_sprite / register_roster at import time, so adding a new
character never requires touching the game loop or UI. See fighters/_template.py.
"""

SPRITES = {}
ROSTER = {}
EXTRA_IMAGES = {}  # e.g. {"YOROI": ["yoroi", "yoroisan"]} for summons that aren't playable


def register_image(key, *names):
    EXTRA_IMAGES[key] = list(names)


def register_sprite(char_type, color, image=None, name=None):
    """image = file name in assets/ WITHOUT extension (png/webp/jpg all work, any case)."""
    SPRITES[char_type] = {
        "color": color,
        "image": image or char_type.lower(),
        "name": name or char_type.title(),
    }


def register_roster(key, title_parts, build, bar_colors=None, portraits=None):
    """
    key         - unique id, e.g. "MOMONGA"
    title_parts - [(text, colour), ...] shown at the top of the team card
    build       - callable(side) -> team object (needs .fighters, .update(), .cooldown_ratio)
    bar_colors  - (left, right) gradient colours for the attack-cooldown bar
    portraits   - sprite keys shown on the select screen (default: [key])
    """
    first_col = title_parts[0][1]
    ROSTER[key] = {
        "key": key,
        "title_parts": title_parts,
        "name": "".join(t for t, _ in title_parts),
        "build": build,
        "bar_colors": bar_colors or (first_col, first_col),
        "portraits": portraits or [key],
    }


def roster_keys():
    return list(ROSTER.keys())
