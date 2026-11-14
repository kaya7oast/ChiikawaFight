import math
import random

import pygame

from .config import *
from .fonts import get_font


# ==========================================
# VISUAL EFFECTS & WORLD OBJECTS
# ==========================================
class Particle:
    def __init__(self, x, y, color, speed=160):
        self.x = x
        self.y = y
        a = random.uniform(0, math.tau)
        s = random.uniform(40, speed)
        self.vx = math.cos(a) * s
        self.vy = math.sin(a) * s
        self.life = random.uniform(0.3, 0.65)
        self.max_life = self.life
        self.color = color
        self.r = random.randint(4, 8)

    def update(self, dt):
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.vx *= 0.92
        self.vy *= 0.92
        self.life -= dt

    def draw(self, surf):
        if self.life <= 0:
            return
        rad = max(2, int(self.r * (self.life / self.max_life)))
        pygame.draw.circle(surf, self.color, (int(self.x), int(self.y)), rad)


class SlashLineEffect:
    def __init__(self, x1, y1, x2, y2, color=WHITE):
        self.x1, self.y1 = x1, y1
        self.x2, self.y2 = x2, y2
        self.color = color
        self.life = 0.30
        self.max_life = 0.30

    def update(self, dt):
        self.life -= dt

    def draw(self, surf):
        if self.life <= 0:
            return
        w = max(1, int(9 * (self.life / self.max_life)))
        pygame.draw.line(surf, self.color, (int(self.x1), int(self.y1)), (int(self.x2), int(self.y2)), w)
        pygame.draw.line(surf, (255, 235, 110), (int(self.x1), int(self.y1)), (int(self.x2), int(self.y2)), max(1, w // 2))


class ClawSlashEffect:
    def __init__(self, cx, cy, angle, color=ANOKO_CREAM):
        self.cx = cx
        self.cy = cy
        self.angle = angle
        self.color = color
        self.life = 0.18
        self.max_life = 0.18

    def update(self, dt):
        self.life -= dt

    def draw(self, surf):
        if self.life <= 0:
            return
        perp = self.angle + math.pi / 2
        for offset in (-18, 0, 18):
            bx = self.cx + math.cos(perp) * offset
            by = self.cy + math.sin(perp) * offset
            sx = bx + math.cos(self.angle) * 28
            sy = by + math.sin(self.angle) * 28
            ex = bx + math.cos(self.angle) * 98
            ey = by + math.sin(self.angle) * 98
            pygame.draw.line(surf, self.color, (int(sx), int(sy)), (int(ex), int(ey)), 6)
            pygame.draw.line(surf, WHITE, (int(sx), int(sy)), (int(ex), int(ey)), 2)


class RingEffect:
    def __init__(self, x, y, radius, color):
        self.x = x
        self.y = y
        self.radius = radius
        self.color = color
        self.life = 0.40
        self.max_life = 0.40

    def update(self, dt):
        self.life -= dt

    def draw(self, surf):
        if self.life <= 0:
            return
        w = max(1, int(6 * (self.life / self.max_life)))
        pygame.draw.circle(surf, self.color, (int(self.x), int(self.y)), int(self.radius), w)


class FloatingPopup:
    """Clean numeric-only popup inside the arena (-15, -20, +10, etc.)."""
    def __init__(self, x, y, text, color, outline=WHITE, size=22, life=0.75):
        self.x = x
        self.y = y
        self.text = text
        self.color = color
        self.outline = outline
        self.life = life
        self.font = get_font(size)

    def update(self, dt):
        self.y -= 32 * dt
        self.life -= dt

    def draw(self, surf):
        if self.life <= 0:
            return
        base = self.font.render(self.text, True, self.color)
        out = self.font.render(self.text, True, self.outline)
        cx, cy = int(self.x), int(self.y)
        for ox, oy in [(-2, 0), (2, 0), (0, -2), (0, 2), (-2, -2), (2, 2)]:
            surf.blit(out, out.get_rect(center=(cx + ox, cy + oy)))
        surf.blit(base, base.get_rect(center=(cx, cy)))
