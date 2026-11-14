import math
import random

import pygame

from .config import *
from .assets import ASSETS, get_avatar
from . import registry


# ==========================================
# SHARED DRAWING HELPERS
# ==========================================
def draw_outlined_text(surf, font, text, color, outline_color, center_pos, thickness=2):
    base = font.render(text, True, color)
    out = font.render(text, True, outline_color)
    cx, cy = int(center_pos[0]), int(center_pos[1])
    for ox in range(-thickness, thickness + 1):
        for oy in range(-thickness, thickness + 1):
            if ox != 0 or oy != 0:
                surf.blit(out, out.get_rect(center=(cx + ox, cy + oy)))
    surf.blit(base, base.get_rect(center=(cx, cy)))


def draw_gradient_bar(surf, rect, col_left, col_right):
    if rect.width <= 0 or rect.height <= 0:
        return
    grad = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
    for x in range(rect.width):
        t = x / max(1, rect.width - 1)
        r = int(col_left[0] + (col_right[0] - col_left[0]) * t)
        g = int(col_left[1] + (col_right[1] - col_left[1]) * t)
        b = int(col_left[2] + (col_right[2] - col_left[2]) * t)
        pygame.draw.line(grad, (r, g, b), (x, 0), (x, rect.height))
    mask = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
    pygame.draw.rect(mask, (255, 255, 255, 255), mask.get_rect(), border_radius=4)
    grad.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    surf.blit(grad, rect.topleft)


def draw_dashed_circle(surf, color, center, radius, width=2, dash_count=24):
    cx, cy = center
    for i in range(dash_count):
        a1 = (i * 2) * math.pi / dash_count
        a2 = (i * 2 + 1) * math.pi / dash_count
        pts = [
            (cx + math.cos(a1) * radius, cy + math.sin(a1) * radius),
            (cx + math.cos((a1 + a2) * 0.5) * radius, cy + math.sin((a1 + a2) * 0.5) * radius),
            (cx + math.cos(a2) * radius, cy + math.sin(a2) * radius),
        ]
        pygame.draw.lines(surf, color, False, pts, width)


def draw_dashed_arrow(surf, color, start, end, width=3):
    x1, y1 = start
    x2, y2 = end
    dist = math.hypot(x2 - x1, y2 - y1)
    if dist < 12:
        return
    dx, dy = (x2 - x1) / dist, (y2 - y1) / dist
    step = 14
    for d in range(0, int(dist - 14), step * 2):
        p1 = (x1 + dx * d, y1 + dy * d)
        p2 = (x1 + dx * min(dist - 14, d + step), y1 + dy * min(dist - 14, d + step))
        pygame.draw.line(surf, color, p1, p2, width)
    ang = math.atan2(y2 - y1, x2 - x1)
    p_tip = (x2, y2)
    p_l = (x2 - math.cos(ang - 0.5) * 13, y2 - math.sin(ang - 0.5) * 13)
    p_r = (x2 - math.cos(ang + 0.5) * 13, y2 - math.sin(ang + 0.5) * 13)
    pygame.draw.polygon(surf, color, [p_tip, p_l, p_r])


def draw_sasumata(surf, cx, cy, angle, color, length=38, scale=1.0):
    asset_key = "SASUMATA_PINK" if color == CHIIKAWA_PINK else "SASUMATA_BLUE"
    sprite = ASSETS.get(asset_key)
    if sprite:
        deg = -math.degrees(angle)
        scaled = pygame.transform.smoothscale(sprite, (int(64 * scale), int(28 * scale)))
        rotated = pygame.transform.rotate(scaled, deg)
        offset_dist = 28 * scale
        rx = cx + math.cos(angle) * offset_dist
        ry = cy + math.sin(angle) * offset_dist
        surf.blit(rotated, rotated.get_rect(center=(int(rx), int(ry))))
        return

    sx = cx + math.cos(angle) * 18
    sy = cy + math.sin(angle) * 18
    ex = cx + math.cos(angle) * (18 + length * scale)
    ey = cy + math.sin(angle) * (18 + length * scale)
    pygame.draw.line(surf, (70, 70, 80), (sx, sy), (ex, ey), int(6 * scale) + 2)
    pygame.draw.line(surf, color, (sx, sy), (ex, ey), int(4 * scale) + 1)

    perp = angle + math.pi / 2
    fork_w = 11 * scale
    fork_l = 13 * scale
    b1 = (ex + math.cos(perp) * fork_w, ey + math.sin(perp) * fork_w)
    b2 = (ex - math.cos(perp) * fork_w, ey - math.sin(perp) * fork_w)
    t1 = (b1[0] + math.cos(angle) * fork_l, b1[1] + math.sin(angle) * fork_l)
    t2 = (b2[0] + math.cos(angle) * fork_l, b2[1] + math.sin(angle) * fork_l)
    for p_start, p_end in [((ex, ey), b1), ((ex, ey), b2), (b1, t1), (b2, t2)]:
        pygame.draw.line(surf, (70, 70, 80), p_start, p_end, 5)
        pygame.draw.line(surf, color, p_start, p_end, 3)


def draw_rakko_sword(surf, cx, cy, angle, length=42, scale=1.0):
    sprite = ASSETS.get("RAKKO_SWORD")
    if sprite:
        deg = -math.degrees(angle)
        scaled = pygame.transform.smoothscale(sprite, (int(64 * scale), int(24 * scale)))
        rotated = pygame.transform.rotate(scaled, deg)
        rx = cx + math.cos(angle) * (28 * scale)
        ry = cy + math.sin(angle) * (28 * scale)
        surf.blit(rotated, rotated.get_rect(center=(int(rx), int(ry))))
        return

    sx = cx + math.cos(angle) * 18
    sy = cy + math.sin(angle) * 18
    ex = cx + math.cos(angle) * (18 + length * scale)
    ey = cy + math.sin(angle) * (18 + length * scale)
    pygame.draw.line(surf, (50, 50, 60), (sx, sy), (ex, ey), int(8 * scale))
    pygame.draw.line(surf, (230, 235, 245), (sx, sy), (ex, ey), int(5 * scale))
    perp = angle + math.pi / 2
    gx, gy = sx + math.cos(angle) * 6, sy + math.sin(angle) * 6
    pygame.draw.line(
        surf,
        (215, 175, 65),
        (gx + math.cos(perp) * 10, gy + math.sin(perp) * 10),
        (gx - math.cos(perp) * 10, gy - math.sin(perp) * 10),
        4,
    )


def draw_usagi_stick(surf, cx, cy, angle, length=44, scale=1.0):
    sprite = ASSETS.get("USAGI_STICK")
    if sprite:
        deg = -math.degrees(angle)
        scaled = pygame.transform.smoothscale(sprite, (int(68 * scale), int(26 * scale)))
        rotated = pygame.transform.rotate(scaled, deg)
        rx = cx + math.cos(angle) * (30 * scale)
        ry = cy + math.sin(angle) * (30 * scale)
        surf.blit(rotated, rotated.get_rect(center=(int(rx), int(ry))))
        return

    sx = cx + math.cos(angle) * 18
    sy = cy + math.sin(angle) * 18
    ex = cx + math.cos(angle) * (18 + length * scale)
    ey = cy + math.sin(angle) * (18 + length * scale)
    pygame.draw.line(surf, (80, 65, 35), (sx, sy), (ex, ey), int(8 * scale))
    pygame.draw.line(surf, USAGI_YELLOW, (sx, sy), (ex, ey), int(5 * scale))
    pygame.draw.circle(surf, (235, 105, 145), (int(ex), int(ey)), int(7 * scale))
    pygame.draw.circle(surf, BLACK, (int(ex), int(ey)), int(7 * scale), 2)


def draw_pink_car(surf, cx, cy, angle):
    sprite = ASSETS.get("PINK_CAR")
    if sprite:
        rotated = pygame.transform.rotate(sprite, -math.degrees(angle))
        surf.blit(rotated, rotated.get_rect(center=(cx, cy)))
        return

    car_surf = pygame.Surface((86, 54), pygame.SRCALPHA)
    for wx, wy in [(12, 2), (56, 2), (12, 44), (56, 44)]:
        pygame.draw.rect(car_surf, BLACK, (wx, wy, 18, 8), border_radius=3)
    pygame.draw.rect(car_surf, CAR_PINK, (6, 7, 74, 40), border_radius=12)
    pygame.draw.rect(car_surf, (95, 50, 65), (6, 7, 74, 40), 3, border_radius=12)
    pygame.draw.rect(car_surf, (195, 232, 252), (50, 12, 18, 30), border_radius=5)
    pygame.draw.rect(car_surf, (95, 50, 65), (50, 12, 18, 30), 2, border_radius=5)
    pygame.draw.circle(car_surf, (255, 245, 140), (76, 15), 4)
    pygame.draw.circle(car_surf, (255, 245, 140), (76, 39), 4)

    rotated = pygame.transform.rotate(car_surf, -math.degrees(angle))
    surf.blit(rotated, rotated.get_rect(center=(cx, cy)))




_DISC_CACHE = {}


def _lighten(col, amt):
    return tuple(int(c + (255 - c) * amt) for c in col[:3])


def _get_disc(color, radius):
    """Soft pastel ball with a glossy highlight (cached per colour/size)."""
    key = (tuple(color), radius)
    if key not in _DISC_CACHE:
        d = radius * 2 + 2
        s = pygame.Surface((d, d), pygame.SRCALPHA)
        c = radius + 1
        steps = 10
        for i in range(steps):
            t = i / (steps - 1)
            r = int(radius - t * radius * 0.85)
            col = _lighten(color, 0.55 + 0.4 * t)
            pygame.draw.circle(s, col, (c - int(t * radius * 0.25), c - int(t * radius * 0.25)), max(1, r))
        hl = pygame.Surface((d, d), pygame.SRCALPHA)
        pygame.draw.ellipse(hl, (255, 255, 255, 120), (int(radius * 0.35), int(radius * 0.22), int(radius * 0.8), int(radius * 0.45)))
        s.blit(hl, (0, 0))
        _DISC_CACHE[key] = s
    return _DISC_CACHE[key]


def draw_ball_avatar(surf, char_type, cx, cy, radius):
    info = registry.SPRITES.get(char_type, {})
    ring_col = info.get("color", WHITE)
    radius = max(4, int(radius))
    sprite = get_avatar(char_type, radius * 2)

    if sprite:
        # No ball: just the character as a sticker (white + team-colour outline).
        # Set SHOW_BALL_UNDER_PICTURES = True in config.py to bring the ball back.
        if SHOW_BALL_UNDER_PICTURES:
            disc = _get_disc(ring_col, radius)
            surf.blit(disc, disc.get_rect(center=(cx, cy)))
            pygame.draw.circle(surf, ring_col, (cx, cy), radius, 4)
        surf.blit(sprite, sprite.get_rect(center=(cx, cy)))
        return

    face_col = (
        (242, 212, 185)
        if char_type == "RAKKO"
        else (255, 244, 198)
        if char_type == "USAGI"
        else WHITE
    )
    pygame.draw.circle(surf, face_col, (cx, cy), radius - 4)

    if char_type == "CHIIKAWA":
        for ex in (-12, 12):
            pygame.draw.circle(surf, WHITE, (cx + ex, cy - int(radius * 0.48)), 7)
            pygame.draw.circle(surf, BLACK, (cx + ex, cy - int(radius * 0.48)), 7, 2)
    elif char_type == "HACHIWARE":
        l_ear = [(cx - 18, cy - 8), (cx - 12, cy - 23), (cx - 4, cy - 14)]
        r_ear = [(cx + 18, cy - 8), (cx + 12, cy - 23), (cx + 4, cy - 14)]
        for ear in (l_ear, r_ear):
            pygame.draw.polygon(surf, HACHIWARE_BLUE, ear)
            pygame.draw.polygon(surf, BLACK, ear, 2)
        pygame.draw.polygon(
            surf, HACHIWARE_BLUE, [(cx - 18, cy - 6), (cx - 4, cy - 18), (cx - 3, cy - 4)]
        )
        pygame.draw.polygon(
            surf, HACHIWARE_BLUE, [(cx + 18, cy - 6), (cx + 4, cy - 18), (cx + 3, cy - 4)]
        )
    elif char_type == "MOMONGA":
        for ex in (-14, 14):
            pygame.draw.circle(surf, WHITE, (cx + ex, cy - int(radius * 0.48)), 8)
            pygame.draw.circle(surf, BLACK, (cx + ex, cy - int(radius * 0.48)), 8, 2)
    elif char_type == "RAKKO":
        for ex in (-13, 13):
            pygame.draw.circle(surf, RAKKO_BROWN, (cx + ex, cy - int(radius * 0.45)), 6)
            pygame.draw.circle(surf, BLACK, (cx + ex, cy - int(radius * 0.45)), 6, 2)
        pygame.draw.line(surf, BLACK, (cx + 4, cy - 14), (cx + 11, cy - 7), 2)
        pygame.draw.line(surf, BLACK, (cx + 11, cy - 14), (cx + 4, cy - 7), 2)
    elif char_type == "USAGI":
        for ex in (-9, 9):
            ear_rect = pygame.Rect(cx + ex - 5, cy - radius - 12, 10, 22)
            pygame.draw.ellipse(surf, (255, 244, 198), ear_rect)
            pygame.draw.ellipse(surf, BLACK, ear_rect, 2)
    elif char_type == "ANOKO":
        for ex in (-16, 16):
            pygame.draw.circle(surf, WHITE, (cx + ex, cy - int(radius * 0.55)), 9)
            pygame.draw.circle(surf, BLACK, (cx + ex, cy - int(radius * 0.55)), 9, 2)
        horn = [(cx - 6, cy - radius + 8), (cx, cy - radius - 8), (cx + 6, cy - radius + 8)]
        pygame.draw.polygon(surf, (130, 195, 240), horn)
        pygame.draw.polygon(surf, BLACK, horn, 2)

    pygame.draw.circle(surf, ring_col, (cx, cy), radius, 5)
    pygame.draw.circle(surf, (70, 75, 85), (cx, cy), radius, 1)

    eye_sep = 11 if char_type == "ANOKO" else 8
    for ex in (-eye_sep, eye_sep):
        pygame.draw.circle(surf, BLACK, (cx + ex, cy - 2), 3)
        pygame.draw.circle(surf, WHITE, (cx + ex - 1, cy - 3), 1)
        pygame.draw.ellipse(surf, (255, 175, 190), (cx + ex - 5, cy + 2, 10, 5))
    pygame.draw.arc(surf, BLACK, (cx - 5, cy + 1, 5, 5), math.pi, math.tau, 2)
    pygame.draw.arc(surf, BLACK, (cx, cy + 1, 5, 5), math.pi, math.tau, 2)


