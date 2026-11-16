"""
Pre-match character intro (toggle "INTRO" on the select screen, or press D there).

For every picked team: an angled anime-style CUT-IN panel slams across the screen, then a short
live DEMO where the character spars a training dummy with sped-up cooldowns so you see every move.
Tap = next character, SKIP button (or S) = straight to the fight.
"""
import math

import pygame

from .config import WIDTH, HEIGHT, WHITE, ARENA_RECT
from .fonts import get_font, fit_font
from .drawing import draw_ball_avatar, draw_outlined_text
from .fighters.base import BaseFighter
from .teams import build_team
from .sim import new_world, step_battle, step_fx, draw_battle
from . import registry

INK = (40, 32, 52)
CUTIN_TIME = 1.5
DEMO_TIME = 7.5
CD_BOOST = 1.6   # demo attack bars fill this much faster than normal

# Short move list per roster key (shown during the demo). Unknown keys just show the name.
MOVES = {
    "DUO": [("Stick Charge", "one charges in with the sasumata"),
            ("Partner Spin", "the other follows up with a spin"),
            ("Weeding", "pulls weeds for permanent buffs"),
            ("Avenge", "+10 dmg if the partner falls")],
    "MOMONGA": [("Dekatsuyo", "summons Dekatsuyo to crash on the enemy"),
                ("Shout", "a cone shout after a miss: knockback + daze"),
                ("Crybaby", "misses twice -> cries, Kani throws books")],
    "RAKKO": [("Sword Spin", "charges in and spins the sword"),
              ("Pink Car", "rams across the arena in the car"),
              ("Counter", "parries hits and strikes back")],
    "USAGI": [("Spin", "3-hit tracking spin"),
              ("Seeds", "spits 5 watermelon seeds"),
              ("Crazy Bounce", "5s frenzy, faster + tankier"),
              ("Snacks", "eats food to heal")],
    "ANOKO": [("Triple Claw", "three lunging claw swipes"),
              ("Pounce Throw", "grabs, swings, hurls into a wall"),
              ("Tail Swipe", "double spin, swats projectiles"),
              ("Medusa Stare", "cone stare that petrifies")],
    "KURIMANJU": [("Burp", "two arena-wide shockwaves"),
                  ("Stick Swipe", "longer lunge = harder hit, dazes"),
                  ("Beer", "random buff or debuff every 10s")],
    "SHISA": [("Ramen Lob", "bowls that leave burning pools"),
              ("Yoroi-san", "her sensei charges across"),
              ("Study", "pauses to study, +7 dmg forever")],
    "KANI": [("Book Toss", "4 bouncing books in a cross"),
             ("Reading", "reads in the middle, letters fly"),
             ("Claw Snip", "two lunging crab-claw snips"),
             ("Momonga Assist", "Momonga charges every 15s")],
    "CHIIKABU": [("Horn Charge", "rushes in, wall slams daze"),
                 ("Latch On", "sticks on and nibbles"),
                 ("Big Form", "transforms: dive + punch"),
                 ("Last Stand", "survives one lethal hit")],
    "SIREN": [("Sing", "vines grow from the walls"),
              ("Tail Slam", "arena-wide tidal shockwave"),
              ("Flood", "floods the arena every 15s"),
              ("Mermaids", "two mermaids ram every 5s")],
}


def _ease_out(t):
    t = max(0.0, min(1.0, t))
    return 1 - (1 - t) ** 3


def _darken(c, k=0.6):
    return tuple(int(v * k) for v in c[:3])


def _lighten(c, k=0.5):
    return tuple(int(v + (255 - v) * k) for v in c[:3])


# ---------------------------------------------------------------- training dummy
class DummyFighter(BaseFighter):
    hud = False

    def __init__(self, x, y):
        super().__init__("DUMMY", x, y, hp=999, color=(200, 80, 80), radius=30, speed=80.0)

    def receive_damage(self, amount, attacker, world):
        hit = super().receive_damage(amount, attacker, world)
        self.hp = self.max_hp  # never dies
        return hit

    def update(self, dt, enemies, world):
        if self.grabbed_by:
            return
        if self.stun_timer > 0:
            self.stun_timer -= dt
            return
        self.move_and_bounce(dt)

    def draw(self, surf, enemies):
        cx, cy = int(self.x), int(self.y)
        r = self.radius
        pygame.draw.rect(surf, (150, 105, 60), (cx - 4, cy, 8, r + 6))  # post
        for k, col in enumerate(((235, 70, 70), WHITE, (235, 70, 70), WHITE)):
            pygame.draw.circle(surf, col, (cx, cy), int(r * (1 - k * 0.24)))
        pygame.draw.circle(surf, INK, (cx, cy), r, 3)


class DummyTeam:
    cooldown_ratio = 0.0

    def __init__(self):
        self.dummy = DummyFighter(ARENA_RECT.right - 120, ARENA_RECT.centery)
        self.fighters = [self.dummy]

    def update(self, dt, enemies, world):
        self.dummy.update(dt, enemies, world)


# ---------------------------------------------------------------- the intro
class IntroDemo:
    def __init__(self, left_keys, right_keys):
        self.queue = [(k, "LEFT") for k in left_keys] + [(k, "RIGHT") for k in right_keys]
        self.index = 0
        self.done = not self.queue
        self.skip_rect = pygame.Rect(WIDTH - 150, HEIGHT - 92, 130, 56)
        if not self.done:
            self._start()

    # ---------- flow ----------
    def _start(self):
        key, side = self.queue[self.index]
        self.key, self.side = key, side
        self.info = registry.ROSTER[key]
        self.t = 0.0
        self.team = build_team(key, "LEFT")
        self.dummy_team = DummyTeam()
        self.world = new_world()
        for obj in self._cd_owners():  # first move comes out almost straight away
            obj.cd_timer = obj.cd_max * 0.8

    def _next(self):
        self.index += 1
        if self.index >= len(self.queue):
            self.done = True
        else:
            self._start()

    def click(self, pos):
        if pos == "SKIP_ALL" or (isinstance(pos, tuple) and self.skip_rect.collidepoint(pos)):
            self.done = True
        else:
            self._next()

    def _cd_owners(self):
        objs = [self.team] + list(getattr(self.team, "subs", [])) + list(self.team.fighters)
        return [o for o in objs if hasattr(o, "cd_timer") and hasattr(o, "cd_max")]

    def update(self, dt):
        if self.done:
            return
        self.t += dt
        if self.t >= CUTIN_TIME:
            for o in self._cd_owners():
                if getattr(o, "state", "ROAM") == "ROAM":
                    o.cd_timer += dt * (CD_BOOST - 1.0)
            step_battle(self.team, self.dummy_team, self.world, dt)
        step_fx(self.team.fighters + self.dummy_team.fighters, self.world, dt)
        if self.t >= CUTIN_TIME + DEMO_TIME:
            self._next()

    # ---------- drawing ----------
    def draw(self, surf, arena_surf, arena_pos):
        if self.done:
            return
        draw_battle(surf, self.team, self.dummy_team, self.world, self.t, arena_surf, arena_pos)
        self._draw_header(surf)
        self._draw_footer(surf)
        if self.t < CUTIN_TIME:
            self._draw_cutin(surf, self.t)

    def _colors(self):
        a, b = self.info["bar_colors"]
        return a[:3], b[:3]

    def _draw_cutin(self, surf, t):
        col, col2 = self._colors()
        from_left = self.side == "LEFT"
        d = 1 if from_left else -1

        # dim the screen + white flash on entry
        dim = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        fade = min(1.0, t / 0.15, max(0.0, CUTIN_TIME - t) / 0.2)
        dim.fill((20, 14, 30, int(150 * fade)))
        surf.blit(dim, (0, 0))

        # slide: in (0-0.28s), slow drift while holding, out (last 0.22s)
        if t < 0.28:
            off = (1 - _ease_out(t / 0.28)) * WIDTH * 1.3
        elif t > CUTIN_TIME - 0.22:
            off = -_ease_out((t - (CUTIN_TIME - 0.22)) / 0.22) * WIDTH * 1.3
        else:
            off = -(t - 0.28) * 18
        ox = -off * d

        cy, h, skew = HEIGHT // 2, 210, 70

        def para(y0, y1, x_off, extra=0):
            return [(-80 + x_off - extra, y1), (-80 + skew + x_off - extra, y0),
                    (WIDTH + 80 + skew + x_off + extra, y0), (WIDTH + 80 + x_off + extra, y1)]

        # accent stripes behind the panel (lag a little for a layered whoosh)
        for k, (c, dy, hh) in enumerate(((col2, -h // 2 - 18, 12), (_lighten(col, 0.4), h // 2 + 8, 10))):
            lag = ox * (1.25 + 0.15 * k)
            pygame.draw.polygon(surf, c, para(cy + dy, cy + dy + hh, lag))

        panel = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        poly = para(cy - h // 2, cy + h // 2, ox)
        pygame.draw.polygon(panel, col, poly)
        # moving speed lines inside the panel
        for i in range(14):
            yy = cy - h // 2 + 10 + (i * 37) % (h - 20)
            x0 = ((i * 97 + t * 1400 * d) % (WIDTH + 300)) - 150
            ln = 60 + (i * 53) % 120
            pygame.draw.line(panel, (*_lighten(col, 0.35), 160), (x0 + ox, yy), (x0 + ln * d + ox, yy), 3)
        # diagonal darker band where the portrait sits
        band_x = (WIDTH * 0.28 if from_left else WIDTH * 0.72) + ox
        band = [(band_x - 120, cy + h // 2), (band_x - 120 + skew, cy - h // 2),
                (band_x + 70 + skew, cy - h // 2), (band_x + 70, cy + h // 2)]
        pygame.draw.polygon(panel, (*_darken(col, 0.75), 255), band)
        # clip everything to the panel shape
        mask = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        pygame.draw.polygon(mask, (255, 255, 255, 255), poly)
        panel.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
        surf.blit(panel, (0, 0))
        pygame.draw.polygon(surf, WHITE, poly, 6)
        pygame.draw.polygon(surf, INK, poly, 2)

        # big portrait(s) popping out over the top edge
        ps = self.info["portraits"][:2]
        px, py = int(band_x + skew * 0.3), cy - 14
        if len(ps) == 1:
            draw_ball_avatar(surf, ps[0], px, py, 112)
        else:
            draw_ball_avatar(surf, ps[1], px + 52, py + 14, 82)
            draw_ball_avatar(surf, ps[0], px - 52, py - 6, 88)

        # name + tag on the other side
        tx = int((WIDTH * 0.68 if from_left else WIDTH * 0.32) + ox)
        tag = f"{self.side} SIDE"
        draw_outlined_text(surf, get_font(16), tag, _lighten(col, 0.7), INK, (tx, cy - 54), 2)
        name = self.info["name"]
        f = fit_font(name, 250, 42, 18)
        draw_outlined_text(surf, f, name, WHITE, INK, (tx, cy - 8), 3)
        draw_outlined_text(surf, get_font(18), "ENTERS THE ARENA!", (255, 236, 150), INK, (tx, cy + 40), 2)

    def _draw_header(self, surf):
        col, col2 = self._colors()
        # angled name banner
        y0, y1, skew = 18, 74, 26
        poly = [(10, y1), (10 + skew, y0), (WIDTH - 10, y0), (WIDTH - 10 - skew, y1)]
        pygame.draw.polygon(surf, col, poly)
        pygame.draw.polygon(surf, col2, [(WIDTH - 120, y1), (WIDTH - 120 + skew, y0), (WIDTH - 10, y0), (WIDTH - 10 - skew, y1)])
        pygame.draw.polygon(surf, WHITE, poly, 4)
        pygame.draw.polygon(surf, INK, poly, 2)
        name = self.info["name"]
        draw_outlined_text(surf, fit_font(name, WIDTH - 200, 30, 14), name, WHITE, INK, ((WIDTH - 110) // 2 + 10, (y0 + y1) // 2), 2)
        draw_outlined_text(surf, get_font(16), "DEMO", WHITE, INK, (WIDTH - 62, (y0 + y1) // 2), 2)

        # move list
        moves = MOVES.get(self.key, [])
        y = 86
        for n, (mv, desc) in enumerate(moves[:4]):
            chip = pygame.Rect(20, y, 150, 24)
            pygame.draw.rect(surf, WHITE, chip, border_radius=8)
            pygame.draw.rect(surf, col, chip, 2, border_radius=8)
            t = fit_font(mv, chip.width - 10, 14, 9).render(mv, True, INK)
            surf.blit(t, t.get_rect(center=chip.center))
            d = fit_font(desc, WIDTH - chip.right - 30, 13, 9, bold=False).render(desc, True, (90, 80, 105))
            surf.blit(d, (chip.right + 10, chip.centery - d.get_height() // 2))
            y += 29

    def _draw_footer(self, surf):
        col, _ = self._colors()
        # progress bar for this demo + dots for the queue
        total = CUTIN_TIME + DEMO_TIME
        bar = pygame.Rect(20, ARENA_RECT.bottom + 26, WIDTH - 40, 10)
        pygame.draw.rect(surf, (225, 215, 232), bar, border_radius=5)
        fill = bar.copy()
        fill.width = int(bar.width * min(1.0, self.t / total))
        pygame.draw.rect(surf, col, fill, border_radius=5)
        for i, (k, side) in enumerate(self.queue):
            cx = WIDTH // 2 - (len(self.queue) - 1) * 14 + i * 28
            c = registry.ROSTER[k]["bar_colors"][0]
            pygame.draw.circle(surf, c if i <= self.index else (220, 212, 228), (cx, ARENA_RECT.bottom + 60), 8)
            pygame.draw.circle(surf, INK, (cx, ARENA_RECT.bottom + 60), 8, 2)
        hint = get_font(13, bold=False).render("tap anywhere for the next fighter", True, (120, 110, 135))
        surf.blit(hint, (24, HEIGHT - 72))
        r = self.skip_rect
        pygame.draw.rect(surf, (90, 76, 104), r.move(0, 4), border_radius=14)
        pygame.draw.rect(surf, (250, 205, 90), r, border_radius=14)
        pygame.draw.rect(surf, INK, r, 3, border_radius=14)
        draw_outlined_text(surf, get_font(19), "SKIP >>", WHITE, INK, r.center, 2)
