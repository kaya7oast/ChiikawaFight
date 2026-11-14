"""Team cards, HP bars, VS badge, winner banner, footer."""
import math

import pygame

from .config import WIDTH, ARENA_RECT, WHITE, DARK_SLATE, HP_GREEN, HP_GREEN_SHINE, DEKATSUYO_GOLD
from .fonts import get_font, fit_font
from .drawing import draw_ball_avatar, draw_outlined_text, draw_gradient_bar

CARD_W = 200
CARD_TOP = 34
CARD_H = 156
INK = (78, 66, 92)
TRAIL = (255, 120, 120)
HP_LOW = (240, 110, 95)
HP_MID = (245, 196, 80)


def card_rect(side):
    x = ARENA_RECT.left if side == "LEFT" else ARENA_RECT.right - CARD_W
    return pygame.Rect(x, CARD_TOP, CARD_W, CARD_H)


_PANEL_CACHE = {}


def _panel(surf, rect, accent):
    """Card background; built once per size/colour then reused (much faster in the browser)."""
    key = (rect.size, tuple(accent))
    if key not in _PANEL_CACHE:
        w, h = rect.size
        p = pygame.Surface((w, h + 5), pygame.SRCALPHA)
        pygame.draw.rect(p, (60, 40, 80, 40), (0, 5, w, h), border_radius=16)
        body = pygame.Surface((w, h), pygame.SRCALPHA)
        pygame.draw.rect(body, (255, 255, 255, 225), body.get_rect(), border_radius=16)
        p.blit(body, (0, 0))
        pygame.draw.rect(p, accent, (14, 0, w - 28, 5), border_bottom_left_radius=4, border_bottom_right_radius=4)
        pygame.draw.rect(p, (235, 225, 240), (0, 0, w, h), 2, border_radius=16)
        _PANEL_CACHE[key] = p
    surf.blit(_PANEL_CACHE[key], rect.topleft)


def _hp_color(ratio):
    if ratio > 0.5:
        return HP_GREEN, HP_GREEN_SHINE
    if ratio > 0.25:
        return HP_MID, (252, 222, 140)
    return HP_LOW, (250, 160, 150)


def _hp_bar(surf, rect, hero, dt, font):
    # lagging "damage trail" so hits are readable
    trail = getattr(hero, "_ui_trail", hero.hp)
    if trail > hero.hp:
        trail = max(hero.hp, trail - max(20.0, (trail - hero.hp) * 2.5) * dt)
    else:
        trail = hero.hp
    hero._ui_trail = trail

    pygame.draw.rect(surf, DARK_SLATE, rect, border_radius=rect.height // 2)
    inner = rect.inflate(-4, -4)
    tw = int(inner.width * trail / hero.max_hp)
    if tw > 0:
        pygame.draw.rect(surf, TRAIL, (inner.x, inner.y, tw, inner.height), border_radius=inner.height // 2)
    ratio = hero.hp / hero.max_hp
    fw = int(inner.width * ratio)
    if fw > 0:
        base, shine = _hp_color(ratio)
        pygame.draw.rect(surf, base, (inner.x, inner.y, fw, inner.height), border_radius=inner.height // 2)
        pygame.draw.rect(surf, shine, (inner.x + 3, inner.y + 2, max(0, fw - 6), max(2, inner.height // 3)), border_radius=3)
    draw_outlined_text(surf, font, f"{int(math.ceil(hero.hp))} / {int(hero.max_hp)}", WHITE, DARK_SLATE, rect.center, thickness=1)


def draw_team_ui(surf, team, side, dt):
    info = team.info
    card = card_rect(side)
    _panel(surf, card, info["bar_colors"][0])
    pad = 12

    # Title (auto-shrinks to fit)
    font = fit_font(info["name"], card.width - pad * 2, 22, 9)
    x = card.x + (card.width - font.size(info["name"])[0]) // 2
    for text, col in info["title_parts"]:
        t = font.render(text, True, col)
        o = font.render(text, True, INK)
        surf.blit(o, (x + 1, card.y + 14 + 1))
        surf.blit(t, (x, card.y + 14))
        x += t.get_width()

    fighters = [f for f in team.fighters if f.hud]
    if len(fighters) == 1:
        hero = fighters[0]
        pr = 25
        pc = (card.x + pad + pr, card.y + 84)
        draw_ball_avatar(surf, hero.type, pc[0], pc[1], pr)
        if not hero.alive:
            _ko(surf, pc, pr)
        bar = pygame.Rect(pc[0] + pr + 8, pc[1] - 15, card.right - pad - (pc[0] + pr + 8), 30)
        _hp_bar(surf, bar, hero, dt, get_font(17))
    else:
        top = card.y + 44                      # just under the title
        avail = (card.bottom - 32) - top       # stop above the ATTACK bar
        row_h = min(34, avail // len(fighters))
        for i, hero in enumerate(fighters):
            pr = max(9, row_h // 2 - 2)
            cy = top + i * row_h + row_h // 2
            pc = (card.x + pad + pr, cy)
            draw_ball_avatar(surf, hero.type, pc[0], pc[1], pr)
            if not hero.alive:
                _ko(surf, pc, pr)
            bx = pc[0] + pr + 8
            bh = min(20, row_h - 3)
            bar = pygame.Rect(bx, cy - bh // 2, card.right - pad - bx, bh)
            _hp_bar(surf, bar, hero, dt, get_font(12 if bh >= 18 else 10))

    # Attack cooldown
    lbl = get_font(11).render("ATTACK", True, (160, 150, 170))
    surf.blit(lbl, (card.x + pad, card.bottom - 26))
    cd = pygame.Rect(card.x + pad + lbl.get_width() + 6, card.bottom - 24, card.width - pad * 2 - lbl.get_width() - 6, 9)
    pygame.draw.rect(surf, (238, 232, 240), cd, border_radius=5)
    fw = int(cd.width * team.cooldown_ratio)
    if fw > 0:
        draw_gradient_bar(surf, pygame.Rect(cd.x, cd.y, fw, cd.height), *info["bar_colors"])
    if team.cooldown_ratio >= 0.98:
        pygame.draw.rect(surf, WHITE, cd, 2, border_radius=5)


def _ko(surf, center, r):
    s = pygame.Surface((r * 2 + 4, r * 2 + 4), pygame.SRCALPHA)
    pygame.draw.circle(s, (40, 30, 50, 150), (r + 2, r + 2), r + 1)
    surf.blit(s, s.get_rect(center=center))
    draw_outlined_text(surf, get_font(max(10, r // 2 + 6)), "KO", (255, 120, 120), WHITE, center, 1)


def draw_vs_badge(surf, match_time):
    c = (WIDTH // 2, CARD_TOP + 62)
    pygame.draw.circle(surf, (205, 190, 220), (c[0], c[1] + 4), 21)
    pygame.draw.circle(surf, DARK_SLATE, c, 21)
    pygame.draw.circle(surf, DEKATSUYO_GOLD, c, 21, 3)
    draw_outlined_text(surf, get_font(17), "VS", WHITE, DARK_SLATE, c, 1)
    mins, secs = int(match_time) // 60, int(match_time) % 60
    t = get_font(13).render(f"{mins:02d}:{secs:02d}", True, INK)
    surf.blit(t, t.get_rect(center=(c[0], c[1] + 36)))


def draw_winner(surf, team, side, anim):
    """anim: seconds since the match ended (for the pop-in)."""
    shade = pygame.Surface(ARENA_RECT.size, pygame.SRCALPHA)
    shade.fill((40, 30, 60, min(120, int(anim * 300))))
    surf.blit(shade, ARENA_RECT)

    scale = min(1.0, anim / 0.25)
    pop = 1.0 + 0.12 * math.sin(min(1.0, anim / 0.35) * math.pi)
    w, h = int((ARENA_RECT.width - 70) * scale * pop), int(150 * scale * pop)
    if w < 10 or h < 10:
        return
    box = pygame.Rect(0, 0, w, h)
    box.center = ARENA_RECT.center
    pygame.draw.rect(surf, (60, 40, 80), box.move(0, 6), border_radius=22)
    pygame.draw.rect(surf, WHITE, box, border_radius=22)
    pygame.draw.rect(surf, team.info["bar_colors"][0], box, 5, border_radius=22)
    if scale < 1.0:
        return

    shown = [f for f in team.fighters if f.hud]
    n = len(shown)
    r = 30 if n <= 3 else 24
    start = box.centerx - (n - 1) * (r * 2 + 8) // 2
    bob = int(math.sin(anim * 5) * 4)
    for i, f in enumerate(shown):
        draw_ball_avatar(surf, f.type, start + i * (r * 2 + 8), box.top + 46 + bob, r)
    name = team.info["name"]
    font = fit_font(name, box.width - 30, 26, 11)
    draw_outlined_text(surf, font, name, team.info["bar_colors"][0], INK, (box.centerx, box.top + 98), 2)
    draw_outlined_text(surf, get_font(20), "WINS!", DEKATSUYO_GOLD, INK, (box.centerx, box.top + 126), 2)


# Big tap targets under the arena (also used for mouse clicks)
_BY = ARENA_RECT.bottom + 22
_BW = (ARENA_RECT.width - 32) // 3
BUTTONS = {
    "MENU": pygame.Rect(ARENA_RECT.left, _BY, _BW, 60),
    "REMATCH": pygame.Rect(ARENA_RECT.left + _BW + 16, _BY, _BW, 60),
    "RANDOM": pygame.Rect(ARENA_RECT.right - _BW, _BY, _BW, 60),
}
_BTN_STYLE = {
    "MENU": ("MENU", "pick fighters", (255, 160, 185)),
    "REMATCH": ("REMATCH", "go again", (250, 205, 90)),
    "RANDOM": ("RANDOM", "new matchup", (140, 180, 235)),
}


def _arrow(surf, cx, cy, flip, col):
    d = -1 if flip else 1
    pygame.draw.polygon(surf, col, [(cx - 5 * d, cy - 7), (cx + 6 * d, cy), (cx - 5 * d, cy + 7)])


def draw_footer(surf, pressed=None):
    pressed = pressed or {}
    for name, rect in BUTTONS.items():
        big, small, col = _BTN_STYLE[name]
        down = name in pressed
        r = rect.move(0, 4 if down else 0)
        if not down:
            pygame.draw.rect(surf, (90, 76, 104), rect.move(0, 5), border_radius=16)
        pygame.draw.rect(surf, col, r, border_radius=16)
        pygame.draw.rect(surf, (255, 255, 255), (r.x + 6, r.y + 4, r.width - 12, 10), border_radius=6)
        pygame.draw.rect(surf, INK, r, 3, border_radius=16)
        draw_outlined_text(surf, get_font(19), big, WHITE, INK, (r.centerx, r.centery - 6), 2)
        t = get_font(11).render(small, True, INK)
        surf.blit(t, t.get_rect(center=(r.centerx, r.centery + 15)))

    y = _BY + 60
    draw_outlined_text(surf, get_font(30), "CHIIKAWA BALL FIGHT", (255, 150, 180), INK, (WIDTH // 2, y + 44), 2)
    sub = get_font(12, bold=False).render("tap MENU (or a team card) to pick who fights", True, (130, 120, 145))
    surf.blit(sub, sub.get_rect(center=(WIDTH // 2, y + 72)))
