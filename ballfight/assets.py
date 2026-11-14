"""
Image loading.

Drop any image into the assets/ folder named after the character (chiikawa.png, Usagi.webp,
RAKKO.jpg ... case and extension don't matter). Transparent cut-out PNG/WebP looks best.
Missing images are fine: the game falls back to the hand-drawn balls.
"""
import os

import pygame

from .config import ASSET_DIR, SHOW_BALL_UNDER_PICTURES
from . import registry

ASSETS = {}
_EXTS = (".png", ".webp", ".jpg", ".jpeg", ".bmp")
_INDEX = None
_AVATAR_CACHE = {}


def _norm(name):
    return name.lower().replace(" ", "").replace("_", "").replace("-", "")


def _build_index():
    global _INDEX
    _INDEX = {}
    if not os.path.isdir(ASSET_DIR):
        return
    for fname in os.listdir(ASSET_DIR):
        stem, ext = os.path.splitext(fname)
        ext = ext.lower()
        if ext not in _EXTS:
            continue
        key = _norm(stem)
        # prefer png over other formats when both exist
        if key not in _INDEX or ext == ".png":
            _INDEX[key] = os.path.join(ASSET_DIR, fname)


def find_asset(name):
    if _INDEX is None:
        _build_index()
    return _INDEX.get(_norm(os.path.splitext(name)[0]))


def _trim(img):
    """Crop away fully transparent borders so the character fills its ball."""
    rect = img.get_bounding_rect(min_alpha=8)
    if rect.width and rect.height:
        return img.subsurface(rect).copy()
    return img


def _fit(img, box_w, box_h):
    w, h = img.get_size()
    scale = min(box_w / w, box_h / h)
    return pygame.transform.smoothscale(img, (max(1, int(w * scale)), max(1, int(h * scale))))


def load_image(name, size=None, fit=None):
    """size=(w,h) stretches; fit=(w,h) keeps aspect ratio inside that box."""
    path = find_asset(name)
    if not path:
        return None
    try:
        img = _trim(pygame.image.load(path).convert_alpha())
        if size:
            img = pygame.transform.smoothscale(img, size)
        elif fit:
            img = _fit(img, *fit)
        return img
    except Exception as e:  # bad/unsupported file
        print(f"[Asset Warning] Could not load {path}: {e}")
        return None


def _sticker(img, outline=3, color=(255, 255, 255)):
    """Add a white sticker-style outline around a transparent sprite."""
    w, h = img.get_size()
    out = pygame.Surface((w + outline * 2, h + outline * 2), pygame.SRCALPHA)
    sil = pygame.mask.from_surface(img, 40).to_surface(setcolor=(*color, 255), unsetcolor=(0, 0, 0, 0))
    for dx in range(-outline, outline + 1):
        for dy in range(-outline, outline + 1):
            if dx * dx + dy * dy <= outline * outline:
                out.blit(sil, (outline + dx, outline + dy))
    out.blit(img, (outline, outline))
    return out


def get_avatar(char_type, diameter):
    """Character sprite sized for a ball of this diameter (cached)."""
    base = ASSETS.get(char_type)
    if base is None:
        return None
    key = (char_type, int(diameter))
    if key not in _AVATAR_CACHE:
        box = int(diameter * (0.98 if SHOW_BALL_UNDER_PICTURES else 1.22))
        color = registry.SPRITES.get(char_type, {}).get("color", (255, 255, 255))
        thin = diameter < 50
        sticker = _sticker(_fit(base, box, box), outline=2 if thin else 3)
        _AVATAR_CACHE[key] = _sticker(sticker, outline=2, color=color[:3])
    return _AVATAR_CACHE[key]


def init_assets():
    os.makedirs(ASSET_DIR, exist_ok=True)
    _build_index()

    # Character portraits (raw, trimmed; scaled on demand by get_avatar)
    for char_type, info in registry.SPRITES.items():
        names = info["image"] if isinstance(info["image"], (list, tuple)) else [info["image"]]
        ASSETS[char_type] = next((img for img in (load_image(n) for n in names) if img), None)

    # Extra images used by summons (runners etc.): key -> file names to try
    for key, names in registry.EXTRA_IMAGES.items():
        img = next((i for i in (load_image(n) for n in names) if i), None)
        if img and max(img.get_size()) > 150:  # shrink big ones, never upscale small ones
            img = _fit(img, 150, 150)
        ASSETS[key] = img

    # Optional props / weapons
    ASSETS["SASUMATA_PINK"] = load_image("sasumata_pink", (64, 28))
    ASSETS["SASUMATA_BLUE"] = load_image("sasumata_blue", (64, 28))
    ASSETS["RAKKO_SWORD"] = load_image("rakko_sword", (64, 24))
    ASSETS["USAGI_STICK"] = load_image("usagi_stick", (68, 26))
    ASSETS["PINK_CAR"] = load_image("pink_car", (84, 52))
    ASSETS["WEED"] = load_image("weed", fit=(44, 44))
    ASSETS["FOOD"] = load_image("food", fit=(42, 42))
    dek = load_image("dekatsuyo", fit=(150, 150))
    ASSETS["DEKATSUYO"] = _sticker(dek, 4) if dek else None

    found = [k for k, v in ASSETS.items() if v is not None]
    missing = [k for k in registry.SPRITES if ASSETS.get(k) is None]
    print(f"[Assets] loaded: {', '.join(found) or 'none'}")
    if missing:
        print(f"[Assets] no image for: {', '.join(missing)} (drawn by hand instead)")
