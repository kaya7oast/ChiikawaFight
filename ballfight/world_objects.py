import math
import random

import pygame

from .config import *
from .audio import *
from .assets import ASSETS
from .fonts import get_font
from .drawing import draw_dashed_arrow, draw_ball_avatar


class WeedTuft:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.radius = 20
        self.claimed_by = None
        self.alive = True

    def draw(self, surf):
        cx, cy = int(self.x), int(self.y)
        if ASSETS.get("WEED"):
            surf.blit(ASSETS["WEED"], ASSETS["WEED"].get_rect(center=(cx, cy)))
            return
        pygame.draw.ellipse(surf, (210, 225, 205), (cx - 18, cy + 6, 36, 12))
        left_blade = [(cx - 2, cy + 10), (cx - 18, cy - 8), (cx - 6, cy + 2)]
        mid_blade = [(cx, cy + 12), (cx, cy - 18), (cx + 5, cy + 4)]
        right_blade = [(cx + 2, cy + 10), (cx + 18, cy - 8), (cx + 6, cy + 2)]
        for poly in (left_blade, right_blade, mid_blade):
            pygame.draw.polygon(surf, WEED_GREEN, poly)
            pygame.draw.polygon(surf, (45, 75, 40), poly, 2)


class UsagiFoodItem:
    def __init__(self, x, y, owner):
        self.x = x
        self.y = y
        self.owner = owner
        self.radius = 20
        self.claimed_by = None
        self.alive = True

    def draw(self, surf):
        cx, cy = int(self.x), int(self.y)
        if ASSETS.get("FOOD"):
            surf.blit(ASSETS["FOOD"], ASSETS["FOOD"].get_rect(center=(cx, cy)))
            return
        pygame.draw.ellipse(surf, (235, 240, 248), (cx - 20, cy + 4, 40, 14))
        pygame.draw.ellipse(surf, BLACK, (cx - 20, cy + 4, 40, 14), 2)
        body = [(cx - 14, cy + 10), (cx - 9, cy - 10), (cx + 9, cy - 10), (cx + 14, cy + 10)]
        pygame.draw.polygon(surf, (250, 215, 95), body)
        pygame.draw.polygon(surf, BLACK, body, 2)
        top = [(cx - 9, cy - 10), (cx + 9, cy - 10), (cx + 11, cy - 3), (cx - 11, cy - 3)]
        pygame.draw.polygon(surf, (135, 75, 35), top)
        pygame.draw.circle(surf, (235, 65, 75), (cx, cy - 13), 4)


class WatermelonSeedProjectile:
    """Usagi's 2nd attack: 5 fast watermelon seeds, 9 damage each, 1 wall bounce each."""
    def __init__(self, x, y, angle, owner):
        self.x = x
        self.y = y
        self.angle = angle
        self.owner = owner
        self.speed = 760.0
        self.bounces = 1
        self.vx = math.cos(angle) * self.speed
        self.vy = math.sin(angle) * self.speed
        self.radius = 8
        self.alive = True

    def update(self, dt, enemies, world):
        self.x += self.vx * dt
        self.y += self.vy * dt
        if not ARENA_RECT.collidepoint(self.x, self.y):
            if self.bounces <= 0:
                self.alive = False
                return
            self.bounces -= 1
            if self.x < ARENA_RECT.left or self.x > ARENA_RECT.right:
                self.vx = -self.vx
            if self.y < ARENA_RECT.top or self.y > ARENA_RECT.bottom:
                self.vy = -self.vy
            self.x = max(ARENA_RECT.left + 1, min(ARENA_RECT.right - 1, self.x))
            self.y = max(ARENA_RECT.top + 1, min(ARENA_RECT.bottom - 1, self.y))
            self.angle = math.atan2(self.vy, self.vx)
            SFX_BOUNCE.play()

        for e in enemies:
            if e.alive and math.hypot(self.x - e.x, self.y - e.y) <= self.radius + e.radius:
                self.alive = False
                e.receive_damage(9.0, self.owner, world)
                break

    def draw(self, surf):
        cx, cy = int(self.x), int(self.y)
        tx = cx + math.cos(self.angle) * 9
        ty = cy + math.sin(self.angle) * 9
        bx = cx - math.cos(self.angle) * 6
        by = cy - math.sin(self.angle) * 6
        perp = self.angle + math.pi / 2
        lx = cx + math.cos(perp) * 5
        ly = cy + math.sin(perp) * 5
        rx = cx - math.cos(perp) * 5
        ry = cy - math.sin(perp) * 5
        pts = [(tx, ty), (lx, ly), (bx, by), (rx, ry)]
        pygame.draw.polygon(surf, (35, 30, 30), pts)
        pygame.draw.polygon(surf, WHITE, pts, 1)


class DekatsuyoRunner:
    """Big thing that charges across the arena after a warning. Subclass / pass params for other runners."""
    def __init__(self, target_x, target_y, owner, damage=80.0, sprite_key="DEKATSUYO",
                 color=DEKATSUYO_GOLD, radius=64, speed=600.0, on_hit=None):
        self.owner = owner
        self.damage = damage
        self.sprite_key = sprite_key
        self.color = color
        self.on_hit = on_hit
        angle = random.uniform(0, math.tau)
        spawn_dist = 340.0
        self.start_x = target_x - math.cos(angle) * spawn_dist
        self.start_y = target_y - math.sin(angle) * spawn_dist
        self.end_x = target_x + math.cos(angle) * spawn_dist
        self.end_y = target_y + math.sin(angle) * spawn_dist

        self.x = self.start_x
        self.y = self.start_y
        self.angle = angle
        self.speed = speed
        self.vx = math.cos(angle) * self.speed
        self.vy = math.sin(angle) * self.speed
        self.radius = radius

        self.warn_timer = 0.80
        self.warn_x = max(ARENA_RECT.left + 36, min(ARENA_RECT.right - 36, self.start_x))
        self.warn_y = max(ARENA_RECT.top + 36, min(ARENA_RECT.bottom - 36, self.start_y))
        self.font_warn = get_font(46)

        self.distance_travelled = 0.0
        self.max_distance = spawn_dist * 2.0
        self.hit_targets = set()
        self.alive = True
        SFX_WARN.play()

    def update(self, dt, enemies, world):
        if self.warn_timer > 0:
            self.warn_timer -= dt
            if self.warn_timer <= 0:
                SFX_DEKATSUYO.play()
            return

        step = self.speed * dt
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.distance_travelled += step

        for e in enemies:
            if e.alive and e not in self.hit_targets:
                if math.hypot(self.x - e.x, self.y - e.y) <= self.radius + e.radius:
                    self.hit_targets.add(e)
                    e.receive_damage(self.damage, self.owner, world)
                    if self.on_hit:
                        self.on_hit(e, world)

        if self.distance_travelled >= self.max_distance:
            self.alive = False

    def draw(self, surf):
        draw_dashed_arrow(surf, (235, 80, 65), (self.x, self.y), (self.end_x, self.end_y), 3)

        if self.warn_timer > 0:
            pulse = 1.0 + 0.18 * math.sin(self.warn_timer * 28.0)
            badge_r = int(26 * pulse)
            wx, wy = int(self.warn_x), int(self.warn_y)
            pygame.draw.circle(surf, (230, 65, 55), (wx, wy), badge_r)
            pygame.draw.circle(surf, WHITE, (wx, wy), badge_r, 3)
            excl = self.font_warn.render("!", True, WHITE)
            surf.blit(excl, excl.get_rect(center=(wx, wy)))
            return

        cx, cy = int(self.x), int(self.y)
        if not ARENA_RECT.inflate(120, 120).collidepoint(cx, cy):
            return

        if self.draw_body(surf, cx, cy):
            return
        if self.sprite_key != "DEKATSUYO":
            draw_ball_avatar(surf, self.sprite_key, cx, cy, self.radius)  # e.g. Momonga with no picture
            return

        pts = []
        spikes = 22
        for i in range(spikes * 2):
            r = self.radius if i % 2 == 0 else self.radius * 0.78
            a = i * math.pi / spikes + self.distance_travelled * 0.02
            pts.append((cx + math.cos(a) * r, cy + math.sin(a) * r))
        pygame.draw.polygon(surf, DEKATSUYO_GOLD, pts)
        pygame.draw.polygon(surf, BLACK, pts, 3)

        pygame.draw.circle(surf, WHITE, (cx, cy), int(self.radius * 0.62))
        pygame.draw.circle(surf, BLACK, (cx, cy), int(self.radius * 0.62), 2)
        pygame.draw.circle(surf, (240, 60, 50), (cx - 14, cy - 8), 7)
        pygame.draw.circle(surf, (240, 60, 50), (cx + 14, cy - 8), 7)
        pygame.draw.ellipse(surf, (220, 90, 105), (cx - 22, cy + 4, 44, 22))
        pygame.draw.ellipse(surf, BLACK, (cx - 22, cy + 4, 44, 22), 2)

    def draw_body(self, surf, cx, cy):
        """Draw the runner's image; return True if drawn (else Dekatsuyo fallback art is used)."""
        img = ASSETS.get(self.sprite_key)
        if not img:
            return False
        if img.get_width() > self.radius * 2.6:
            img = _scaled_cache(self.sprite_key, img, int(self.radius * 2.3))
        wobble = math.sin(self.distance_travelled * 0.045) * 9
        rot = pygame.transform.rotate(img, wobble)
        surf.blit(rot, rot.get_rect(center=(cx, cy)))
        return True


_SCALED = {}


def _scaled_cache(key, img, box):
    k = (key, box)
    if k not in _SCALED:
        w, h = img.get_size()
        s = box / max(w, h)
        _SCALED[k] = pygame.transform.smoothscale(img, (max(1, int(w * s)), max(1, int(h * s))))
    return _SCALED[k]
