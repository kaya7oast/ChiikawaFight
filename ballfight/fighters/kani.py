"""
Kani (250 HP, 2.95s attack cooldown, 3-move cycle)
- Attack 1 BOOK TOSS: 4 big books thrown in a cross (90 deg apart), each bounces off walls
  5 times, 10 dmg on hit.
- Attack 2 READING: runs to the middle and reads; random letters fly at the enemy (5 dmg each).
  Takes 50% less damage while reading.
- Passive MOMONGA ASSIST: every 15s Momonga charges across the arena (35 dmg).
- Attack 3 CLAW SNIP: two frontal crab-claw snips (like Anoko's claws), each with a short
  lunge toward the enemy, 12 dmg each.
"""
import math
import random
import string

import pygame

from ..config import *
from ..audio import *
from ..effects import *
from ..world_objects import *
from ..drawing import *
from ..fonts import get_font
from ..teams import register_solo
from ..registry import register_image
from ..assets import ASSETS
from ..voices import play_voice
from .base import BaseFighter

KANI_RED = (232, 96, 84)
MOMONGA_EVERY = 15.0  # seconds between Momonga's assists
BOOK_COLORS = [(110, 160, 230), (240, 170, 70), (150, 200, 120), (225, 120, 170)]


class BookVolley:
    def __init__(self):
        self.hits = 0
        self.total = 4


class BookProjectile:
    def __init__(self, x, y, angle, owner, volley, color):
        self.x, self.y, self.owner, self.volley, self.color = x, y, owner, volley, color
        self.vx, self.vy = math.cos(angle) * 400, math.sin(angle) * 400
        self.radius = 18
        self.bounces = 5
        self.spin = random.uniform(0, 360)
        self.alive = True

    def update(self, dt, enemies, world):
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.spin += 600 * dt
        hit_wall = False
        if self.x - self.radius < ARENA_RECT.left or self.x + self.radius > ARENA_RECT.right:
            self.vx = -self.vx
            self.x = max(ARENA_RECT.left + self.radius, min(ARENA_RECT.right - self.radius, self.x))
            hit_wall = True
        if self.y - self.radius < ARENA_RECT.top or self.y + self.radius > ARENA_RECT.bottom:
            self.vy = -self.vy
            self.y = max(ARENA_RECT.top + self.radius, min(ARENA_RECT.bottom - self.radius, self.y))
            hit_wall = True
        if hit_wall:
            if self.bounces <= 0:
                self.alive = False
                return
            self.bounces -= 1
        for e in enemies:
            if e.alive and not e.in_air and math.hypot(self.x - e.x, self.y - e.y) <= self.radius + e.radius:
                e.receive_damage(10.0, self.owner, world)
                self.volley.hits += 1
                self.alive = False
                return

    def draw(self, surf):
        b = pygame.Surface((40, 30), pygame.SRCALPHA)
        pygame.draw.rect(b, self.color, (0, 0, 40, 30), border_radius=4)
        pygame.draw.rect(b, (255, 250, 235), (32, 3, 6, 24))
        pygame.draw.line(b, (255, 255, 255), (6, 10), (24, 10), 3)
        pygame.draw.rect(b, (60, 50, 70), (0, 0, 40, 30), 3, border_radius=4)
        rot = pygame.transform.rotate(b, self.spin)
        surf.blit(rot, rot.get_rect(center=(int(self.x), int(self.y))))


class LetterProjectile:
    def __init__(self, x, y, angle, owner):
        self.x, self.y, self.owner = x, y, owner
        self.vx, self.vy = math.cos(angle) * 420, math.sin(angle) * 420
        self.char = random.choice(string.ascii_uppercase)
        self.color = random.choice([(90, 120, 220), (220, 90, 110), (80, 160, 110), (180, 110, 200)])
        self.radius = 9
        self.alive = True

    def update(self, dt, enemies, world):
        self.x += self.vx * dt
        self.y += self.vy * dt
        if not ARENA_RECT.collidepoint(self.x, self.y):
            self.alive = False
            return
        for e in enemies:
            if e.alive and not e.in_air and math.hypot(self.x - e.x, self.y - e.y) <= self.radius + e.radius:
                e.receive_damage(5.0, self.owner, world)
                self.alive = False
                return

    def draw(self, surf):
        draw_outlined_text(surf, get_font(20), self.char, self.color, WHITE, (int(self.x), int(self.y)), 2)


def draw_claw(surf, x, y, angle, size, alpha=255):
    """Kani's claw image (assets/Kani_crabclaw.png) facing `angle`. Returns False if no image."""
    img = ASSETS.get("KANI_CLAW")
    if not img:
        return False
    w, h = img.get_size()
    s = size / max(w, h)
    c = pygame.transform.smoothscale(img, (max(1, int(w * s)), max(1, int(h * s))))
    if alpha < 255:
        c.fill((255, 255, 255, alpha), special_flags=pygame.BLEND_RGBA_MULT)
    c = pygame.transform.rotate(c, -math.degrees(angle))
    surf.blit(c, c.get_rect(center=(int(x), int(y))))
    return True


class SnipEffect:
    """Claw pinch: the claw image punches forward and squeezes (falls back to drawn pincers)."""
    def __init__(self, x, y, angle):
        self.x, self.y, self.angle = x, y, angle
        self.life = self.max_life = 0.2

    def update(self, dt):
        self.life -= dt

    def draw(self, surf):
        if self.life <= 0:
            return
        t = self.life / self.max_life  # 1 -> 0 (open -> closed)
        pulse = 1.0 + 0.45 * math.sin((1 - t) * math.pi)
        if draw_claw(surf, self.x, self.y, self.angle, 44 * pulse, int(255 * min(1, t * 2))):
            for side in (-1, 1):  # little impact ticks
                a = self.angle + side * 0.9
                pygame.draw.line(surf, WHITE, (self.x + math.cos(a) * 26, self.y + math.sin(a) * 26),
                                 (self.x + math.cos(a) * 38, self.y + math.sin(a) * 38), 3)
            return
        for side in (-1, 1):
            a = self.angle + side * (0.15 + 0.6 * t)
            pts = []
            for k in range(7):
                u = k / 6
                r = 10 + 34 * u
                bend = side * math.sin(u * math.pi) * 0.35
                pts.append((self.x + math.cos(a - bend) * r - math.cos(self.angle) * 30,
                            self.y + math.sin(a - bend) * r - math.sin(self.angle) * 30))
            pygame.draw.lines(surf, (150, 40, 40), False, pts, 9)
            pygame.draw.lines(surf, KANI_RED, False, pts, 5)


class KaniFighter(BaseFighter):
    def __init__(self, x, y):
        super().__init__("KANI", x, y, hp=250, color=KANI_RED, radius=30, speed=225.0)
        self.cd_max = 2.95
        self.cd_timer = 0.0
        self.attack_index = 0
        self.letter_timer = 0.0
        self.snips_left = 0
        self.snip_timer = 0.0
        self.target = None
        self.momonga_cd = MOMONGA_EVERY

    def update(self, dt, enemies, world):
        if not self.alive or self.grabbed_by:
            return
        living = [e for e in enemies if e.alive]
        nearest = min(living, key=lambda e: math.hypot(e.x - self.x, e.y - self.y)) if living else None

        # Momonga helps out every 15s, no matter what (runs even while stunned)
        self.momonga_cd -= dt
        if self.momonga_cd <= 0:
            self.momonga_cd += MOMONGA_EVERY
            if nearest:
                world["hazards"].append(DekatsuyoRunner(nearest.x, nearest.y, self, damage=35.0,
                                                        sprite_key="MOMONGA", color=MOMONGA_CYAN, radius=46, speed=1000.0))
                play_voice("momonga_scream", cooldown=0)

        if self.stun_timer > 0:
            self.stun_timer -= dt
            return
        self.check_enemy_food_pickup(world)

        if self.state == "READ_MOVE":
            cx, cy = ARENA_RECT.center
            d = math.hypot(cx - self.x, cy - self.y)
            self.state_timer -= dt
            if d < 10 or self.state_timer <= 0:
                self.state = "READING"
                self.state_timer = 2.6
                self.letter_timer = 0.2
            else:
                step = min(d, 460 * dt)
                self.x += (cx - self.x) / d * step
                self.y += (cy - self.y) / d * step
            return

        if self.state == "READING":
            self.dmg_taken_mult = 0.5
            self.state_timer -= dt
            self.letter_timer -= dt
            if self.letter_timer <= 0 and living:
                self.letter_timer = 0.17
                tgt = random.choice(living)
                ang = math.atan2(tgt.y - self.y, tgt.x - self.x) + random.uniform(-0.18, 0.18)
                world["projectiles"].append(LetterProjectile(self.x, self.y - 10, ang, self))
                SFX_SEED.play()
            if self.state_timer <= 0:
                self.state = "ROAM"
                self.dmg_taken_mult = 1.0
            return

        if self.state == "CLAW_DASH":
            self.state_timer -= dt
            tgt = self.target if (self.target and self.target.alive) else nearest
            if tgt:
                ang = math.atan2(tgt.y - self.y, tgt.x - self.x)
                self.weapon_angle = ang
                self.x += math.cos(ang) * 600 * dt
                self.y += math.sin(ang) * 600 * dt
                self.clamp_to_walls()
                if math.hypot(tgt.x - self.x, tgt.y - self.y) <= self.radius + tgt.radius + 30:
                    self.state_timer = 0
            if self.state_timer <= 0:
                self.state = "CLAW"
                self.snips_left = 2
                self.snip_timer = 0.0
            return

        if self.state == "CLAW":
            self.snip_timer -= dt
            tgt = self.target if (self.target and self.target.alive) else nearest
            if tgt:
                self.weapon_angle = math.atan2(tgt.y - self.y, tgt.x - self.x)
            if self.snip_timer <= 0 and self.snips_left > 0:
                self.snips_left -= 1
                self.snip_timer = 0.25
                # short lunge toward the target on each snip
                self.x += math.cos(self.weapon_angle) * 32.0
                self.y += math.sin(self.weapon_angle) * 32.0
                self.clamp_to_walls()
                SFX_CLAW.play()
                ex = self.x + math.cos(self.weapon_angle) * (self.radius + 30)
                ey = self.y + math.sin(self.weapon_angle) * (self.radius + 30)
                world["effects"].append(SnipEffect(ex, ey, self.weapon_angle))
                for e in living:
                    if e.in_air:
                        continue
                    dx, dy = e.x - self.x, e.y - self.y
                    ang_diff = abs((math.atan2(dy, dx) - self.weapon_angle + math.pi) % math.tau - math.pi)
                    if math.hypot(dx, dy) <= self.radius + e.radius + 60 and ang_diff <= 0.78:
                        e.receive_damage(12.0, self, world)
            if self.snips_left <= 0 and self.snip_timer <= 0:
                self.state = "ROAM"
            return

        self.dmg_taken_mult = 1.0
        self.move_and_bounce(dt)
        if living:
            self.cd_timer += dt * self.cd_rate()
            if self.cd_timer >= self.cd_max:
                self.cd_timer = 0.0
                if self.attack_index == 0:
                    aim = math.atan2(nearest.y - self.y, nearest.x - self.x)
                    volley = BookVolley()
                    for k in range(4):  # 4 books, 90 deg apart
                        world["projectiles"].append(BookProjectile(self.x, self.y, aim + k * math.tau / 4, self, volley, BOOK_COLORS[k]))
                    SFX_SPIN.play()
                elif self.attack_index == 1:
                    self.state = "READ_MOVE"
                    self.state_timer = 1.5
                else:
                    self.state = "CLAW"
                    self.snips_left = 2
                    self.snip_timer = 0.0
                    self.target = nearest
                self.attack_index = (self.attack_index + 1) % 3

    def draw(self, surf, enemies):
        if not self.alive:
            return
        cx, cy = int(self.x), int(self.y)
        draw_ball_avatar(surf, self.type, cx, cy, self.radius)
        if self.state == "READING":
            bx, by = cx, cy + self.radius - 4
            flap = math.sin(self.state_timer * 14) * 3
            pygame.draw.polygon(surf, (250, 245, 230), [(bx - 24, by - 8 - flap), (bx, by - 2), (bx + 24, by - 8 + flap), (bx + 24, by + 10), (bx, by + 16), (bx - 24, by + 10)])
            pygame.draw.polygon(surf, (110, 160, 230), [(bx - 24, by - 8 - flap), (bx, by - 2), (bx + 24, by - 8 + flap), (bx + 24, by + 10), (bx, by + 16), (bx - 24, by + 10)], 3)
            draw_dashed_circle(surf, (110, 160, 230), (cx, cy), self.radius + 10, 2, 20)
        elif self.state in ("CLAW_DASH", "CLAW"):
            ex = cx + math.cos(self.weapon_angle) * (self.radius + 10)
            ey = cy + math.sin(self.weapon_angle) * (self.radius + 10)
            if not draw_claw(surf, ex, ey, self.weapon_angle, 34):
                pygame.draw.circle(surf, KANI_RED, (int(ex), int(ey)), 11)
                pygame.draw.circle(surf, (150, 40, 40), (int(ex), int(ey)), 11, 2)
        if self.momonga_cd <= 4.0:
            t = get_font(11).render(f"Momonga in {self.momonga_cd:.1f}s", True, WHITE)
            r = t.get_rect(center=(cx, cy + self.radius + 14)).inflate(8, 2)
            pygame.draw.rect(surf, MOMONGA_CYAN, r, border_radius=6)
            surf.blit(t, t.get_rect(center=r.center))
        if self.stun_timer > 0:
            draw_dashed_circle(surf, MEDUSA_PURPLE, (cx, cy), self.radius + 6, 3, 16)


register_image("KANI_CLAW", "kani_crabclaw")
register_solo("KANI", "Kani", KANI_RED, KaniFighter)
