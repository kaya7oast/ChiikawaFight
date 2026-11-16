"""
Character select screen.
Tap a slot (it glows), then tap a fighter to put them in it. 1v1 or 2v2. Then FIGHT!
"""
import random

import pygame

from .config import WIDTH, WHITE, DARK_SLATE, DEKATSUYO_GOLD
from .fonts import get_font, fit_font
from .drawing import draw_ball_avatar, draw_outlined_text
from . import registry

INK = (78, 66, 92)
SIDE_COL = {"LEFT": (255, 150, 180), "RIGHT": (120, 165, 230)}


class SelectMenu:
    def __init__(self):
        keys = registry.roster_keys()
        self.mode = 1  # fighters per side
        self.slots = {"LEFT": [keys[0], keys[2 % len(keys)]], "RIGHT": [keys[1 % len(keys)], keys[3 % len(keys)]]}
        self.active = ("LEFT", 0)
        self.hits = []      # (rect, action) built each draw
        self.flash = {}     # action -> timer
        self.intro_on = True  # play the character cut-in + demo before each match

    # ---------- what the game reads ----------
    def picks(self, side):
        return self.slots[side][: self.mode]

    def randomize(self):
        keys = registry.roster_keys()
        for side in self.slots:
            self.slots[side] = [random.choice(keys) for _ in range(2)]

    def cycle(self, side):
        """Keyboard 1 / 2: step the first fighter of a side through the roster."""
        keys = registry.roster_keys()
        cur = self.slots[side][0]
        self.slots[side][0] = keys[(keys.index(cur) + 1) % len(keys)]

    # ---------- input ----------
    def _slot_order(self):
        order = []
        for i in range(self.mode):
            order += [("LEFT", i), ("RIGHT", i)]
        return order

    def click(self, pos):
        """Returns "FIGHT" when the player starts the match."""
        for rect, action in self.hits:
            if not rect.collidepoint(pos):
                continue
            self.flash[str(action)] = 0.15
            kind = action[0]
            if kind == "MODE":
                self.mode = action[1]
                if self.active[1] >= self.mode:
                    self.active = (self.active[0], 0)
            elif kind == "SLOT":
                self.active = (action[1], action[2])
            elif kind == "PICK":
                side, i = self.active
                self.slots[side][i] = action[1]
                order = self._slot_order()
                self.active = order[(order.index(self.active) + 1) % len(order)]
            elif kind == "RANDOM":
                self.randomize()
            elif kind == "INTRO":
                self.intro_on = not self.intro_on
            elif kind == "FIGHT":
                return "FIGHT"
            return None
        return None

    # ---------- drawing ----------
    def _button(self, surf, rect, text, col, action, small=None, selected=False):
        down = str(action) in self.flash
        r = rect.move(0, 3 if down else 0)
        if not down:
            pygame.draw.rect(surf, (90, 76, 104), rect.move(0, 4), border_radius=14)
        pygame.draw.rect(surf, col, r, border_radius=14)
        pygame.draw.rect(surf, (255, 255, 255), (r.x + 6, r.y + 4, r.width - 12, 8), border_radius=5)
        pygame.draw.rect(surf, WHITE if selected else INK, r, 4 if selected else 3, border_radius=14)
        draw_outlined_text(surf, get_font(19), text, WHITE, INK, (r.centerx, r.centery - (6 if small else 0)), 2)
        if small:
            t = get_font(11).render(small, True, INK)
            surf.blit(t, t.get_rect(center=(r.centerx, r.centery + 14)))
        self.hits.append((rect, action))

    def _portraits(self, surf, key, cx, cy, r):
        ps = registry.ROSTER[key]["portraits"][:2]
        if len(ps) == 1:
            draw_ball_avatar(surf, ps[0], cx, cy, r)
        else:
            draw_ball_avatar(surf, ps[0], cx - int(r * 0.55), cy, int(r * 0.8))
            draw_ball_avatar(surf, ps[1], cx + int(r * 0.55), cy, int(r * 0.8))

    def draw(self, surf, dt):
        self.hits = []
        for k in list(self.flash):
            self.flash[k] -= dt
            if self.flash[k] <= 0:
                del self.flash[k]

        draw_outlined_text(surf, get_font(28), "CHOOSE YOUR FIGHTERS", (255, 150, 180), INK, (WIDTH // 2, 38), 2)

        # mode toggle
        for i, m in enumerate((1, 2)):
            rect = pygame.Rect(WIDTH // 2 - 130 + i * 136, 66, 124, 40)
            self._button(surf, rect, f"{m} v {m}", (250, 205, 90) if self.mode == m else (235, 230, 240),
                         ("MODE", m), selected=self.mode == m)

        # intro demo toggle (top-right pill)
        tr = pygame.Rect(WIDTH - 126, 70, 114, 32)
        on = self.intro_on
        pygame.draw.rect(surf, (250, 205, 90) if on else (225, 218, 232), tr, border_radius=16)
        pygame.draw.rect(surf, INK, tr, 2, border_radius=16)
        knob_x = tr.right - 16 if on else tr.x + 16
        pygame.draw.circle(surf, WHITE, (knob_x, tr.centery), 11)
        pygame.draw.circle(surf, INK, (knob_x, tr.centery), 11, 2)
        lbl = get_font(12).render("INTRO ON" if on else "INTRO OFF", True, INK)
        surf.blit(lbl, lbl.get_rect(center=(tr.centerx + (-10 if on else 10), tr.centery)))
        self.hits.append((tr, ("INTRO",)))

        # slots
        top = 122
        for side, x0 in (("LEFT", 20), ("RIGHT", WIDTH // 2 + 20)):
            panel = pygame.Rect(x0, top, WIDTH // 2 - 40, 132)
            pygame.draw.rect(surf, (255, 255, 255), panel, border_radius=16)
            pygame.draw.rect(surf, SIDE_COL[side], panel, 3, border_radius=16)
            lbl = get_font(13).render(side, True, SIDE_COL[side])
            surf.blit(lbl, (panel.x + 10, panel.y + 6))
            w = (panel.width - 16 - 8 * (self.mode - 1)) // self.mode
            for i in range(self.mode):
                key = self.slots[side][i]
                rect = pygame.Rect(panel.x + 8 + i * (w + 8), panel.y + 26, w, panel.height - 34)
                active = self.active == (side, i)
                pygame.draw.rect(surf, (255, 246, 210) if active else (248, 244, 250), rect, border_radius=12)
                pygame.draw.rect(surf, DEKATSUYO_GOLD if active else (225, 215, 232), rect, 4 if active else 2, border_radius=12)
                self._portraits(surf, key, rect.centerx, rect.y + 36, 26 if self.mode == 1 else 22)
                name = registry.ROSTER[key]["name"]
                f = fit_font(name, rect.width - 8, 15, 9)
                t = f.render(name, True, INK)
                surf.blit(t, t.get_rect(center=(rect.centerx, rect.bottom - 16)))
                self.hits.append((rect, ("SLOT", side, i)))
        pygame.draw.circle(surf, DARK_SLATE, (WIDTH // 2, top + 66), 20)
        pygame.draw.circle(surf, DEKATSUYO_GOLD, (WIDTH // 2, top + 66), 20, 3)
        draw_outlined_text(surf, get_font(15), "VS", WHITE, DARK_SLATE, (WIDTH // 2, top + 66), 1)

        side, i = self.active
        hint = f"tap a fighter to put in {side.lower()} slot {i + 1}" if self.mode == 2 else f"tap a fighter for the {side.lower()} side"
        t = get_font(12, bold=False).render(hint, True, (120, 110, 135))
        surf.blit(t, t.get_rect(center=(WIDTH // 2, top + 146)))

        # roster grid
        keys = registry.roster_keys()
        cols, cw, ch, gx, gy = 3, 160, 112, 10, 10
        x_start = (WIDTH - (cols * cw + (cols - 1) * gx)) // 2
        y_start = top + 166
        for n, key in enumerate(keys):
            r, c = divmod(n, cols)
            rect = pygame.Rect(x_start + c * (cw + gx), y_start + r * (ch + gy), cw, ch)
            chosen = key in self.slots["LEFT"][: self.mode] or key in self.slots["RIGHT"][: self.mode]
            down = str(("PICK", key)) in self.flash
            rr = rect.move(0, 3 if down else 0)
            pygame.draw.rect(surf, (60, 40, 80, 40) if False else (215, 205, 225), rect.move(0, 4), border_radius=14)
            pygame.draw.rect(surf, (255, 255, 255), rr, border_radius=14)
            col = registry.ROSTER[key]["bar_colors"][0]
            pygame.draw.rect(surf, col, rr, 4 if chosen else 2, border_radius=14)
            self._portraits(surf, key, rr.centerx, rr.y + 46, 30)
            name = registry.ROSTER[key]["name"]
            f = fit_font(name, cw - 12, 15, 9)
            t = f.render(name, True, INK)
            surf.blit(t, t.get_rect(center=(rr.centerx, rr.bottom - 17)))
            self.hits.append((rect, ("PICK", key)))

        # bottom buttons
        rows = (len(keys) + cols - 1) // cols
        by = max(y_start + rows * (ch + gy) + 6, 846)
        self._button(surf, pygame.Rect(20, by, 170, 64), "RANDOM", (190, 170, 240), ("RANDOM",), "surprise me")
        self._button(surf, pygame.Rect(206, by, WIDTH - 226, 64), "FIGHT!", (250, 205, 90), ("FIGHT",), "start the match")
