"""Cached fonts. Creating a SysFont every frame/popup is slow, so everything goes through here."""
import pygame

_FONT_NAMES = "arialroundedmtbold,segoeuisemibold,segoeui,trebuchetms,arial"
_CACHE = {}


def get_font(size, bold=True):
    key = (size, bold)
    if key not in _CACHE:
        _CACHE[key] = pygame.font.SysFont(_FONT_NAMES, size, bold=bold)
    return _CACHE[key]


def fit_font(text, max_width, start_size, min_size=12, bold=True):
    """Largest font (<= start_size) where `text` fits inside max_width."""
    size = start_size
    while size > min_size and get_font(size, bold).size(text)[0] > max_width:
        size -= 1
    return get_font(size, bold)
