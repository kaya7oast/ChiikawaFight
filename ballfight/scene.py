"""Pre-rendered background + arena floor (drawn once, blitted every frame)."""
import math
import random

import pygame

from .config import WIDTH, HEIGHT, ARENA_RECT

SKY_TOP = (255, 232, 242)
SKY_BOTTOM = (206, 230, 255)
FLOOR_A = (255, 251, 240)
FLOOR_B = (250, 242, 224)
BORDER = (86, 72, 96)
BORDER_INNER = (255, 190, 210)


def _lerp(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def build_background():
    bg = pygame.Surface((WIDTH, HEIGHT))
    for y in range(HEIGHT):
        pygame.draw.line(bg, _lerp(SKY_TOP, SKY_BOTTOM, y / HEIGHT), (0, y), (WIDTH, y))

    deco = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    rng = random.Random(7)
    # soft bokeh dots
    for _ in range(38):
        x, y = rng.randint(0, WIDTH), rng.randint(0, HEIGHT)
        r = rng.randint(6, 26)
        col = rng.choice([(255, 255, 255, 70), (255, 200, 220, 60), (190, 220, 255, 70)])
        pygame.draw.circle(deco, col, (x, y), r)
    # little 4-point sparkles
    for _ in range(26):
        x, y = rng.randint(0, WIDTH), rng.randint(0, HEIGHT)
        s = rng.randint(3, 7)
        pts = [(x, y - s * 2), (x + s // 2, y - s // 2), (x + s * 2, y), (x + s // 2, y + s // 2),
               (x, y + s * 2), (x - s // 2, y + s // 2), (x - s * 2, y), (x - s // 2, y - s // 2)]
        pygame.draw.polygon(deco, (255, 255, 255, 150), pts)
    bg.blit(deco, (0, 0))
    return bg


def build_arena():
    """Returns (surface, topleft) – includes the drop shadow, so blit at the returned position."""
    pad = 14
    w, h = ARENA_RECT.width + pad * 2, ARENA_RECT.height + pad * 2
    surf = pygame.Surface((w, h), pygame.SRCALPHA)

    shadow = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.draw.rect(shadow, (60, 40, 80, 55), (pad + 2, pad + 9, ARENA_RECT.width, ARENA_RECT.height), border_radius=18)
    surf.blit(shadow, (0, 0))

    floor = pygame.Surface(ARENA_RECT.size, pygame.SRCALPHA)
    tile = 46
    for ty in range(0, ARENA_RECT.height, tile):
        for tx in range(0, ARENA_RECT.width, tile):
            col = FLOOR_A if ((tx // tile) + (ty // tile)) % 2 == 0 else FLOOR_B
            pygame.draw.rect(floor, col, (tx, ty, tile, tile))
    # faint centre circle like a little stadium
    c = (ARENA_RECT.width // 2, ARENA_RECT.height // 2)
    pygame.draw.circle(floor, (255, 205, 220), c, 70, 3)
    pygame.draw.line(floor, (255, 215, 228), (0, c[1]), (ARENA_RECT.width, c[1]), 3)
    # vignette at edges
    vig = pygame.Surface(ARENA_RECT.size, pygame.SRCALPHA)
    for i in range(14):
        a = int(26 * (1 - i / 14))
        pygame.draw.rect(vig, (200, 170, 150, a), (i, i, ARENA_RECT.width - i * 2, ARENA_RECT.height - i * 2), 1, border_radius=14)
    floor.blit(vig, (0, 0))

    # round the corners of the floor
    mask = pygame.Surface(ARENA_RECT.size, pygame.SRCALPHA)
    pygame.draw.rect(mask, (255, 255, 255, 255), mask.get_rect(), border_radius=16)
    floor.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
    surf.blit(floor, (pad, pad))

    r = pygame.Rect(pad, pad, ARENA_RECT.width, ARENA_RECT.height)
    pygame.draw.rect(surf, BORDER, r, 5, border_radius=16)
    pygame.draw.rect(surf, BORDER_INNER, r.inflate(-10, -10), 2, border_radius=12)
    return surf, (ARENA_RECT.left - pad, ARENA_RECT.top - pad)


def draw_shadow(surf, x, y, radius):
    w, h = int(radius * 1.7), int(radius * 0.55)
    s = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.draw.ellipse(s, (70, 50, 70, 55), s.get_rect())
    surf.blit(s, s.get_rect(center=(int(x), int(y + radius * 0.82))))


def draw_hit_flash(surf, x, y, radius, t):
    a = int(150 * min(1.0, t / 0.14))
    s = pygame.Surface((radius * 2 + 4, radius * 2 + 4), pygame.SRCALPHA)
    pygame.draw.circle(s, (255, 255, 255, a), (radius + 2, radius + 2), radius + 2)
    surf.blit(s, s.get_rect(center=(int(x), int(y))))


def draw_daze_stars(surf, x, y, t):
    """Little orbiting stars over a dazed fighter."""
    for i in range(3):
        a = t * 5 + i * math.tau / 3
        sx, sy = x + math.cos(a) * 16, y + math.sin(a) * 5
        pts = []
        for k in range(10):
            r = 6 if k % 2 == 0 else 2.6
            ang = k * math.pi / 5 - math.pi / 2
            pts.append((sx + math.cos(ang) * r, sy + math.sin(ang) * r))
        pygame.draw.polygon(surf, (255, 220, 80), pts)
        pygame.draw.polygon(surf, (120, 90, 40), pts, 1)
