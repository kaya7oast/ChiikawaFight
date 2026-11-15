"""
Shisa (250 HP, 2.9s attack cooldown, 2-move cycle)
- Attack 1 RAMEN LOB: lobs a ramen bowl at the enemy plus a 2nd bowl at a random spot. 10 dmg on landing hit, leaves a hot
  ramen pool for 9s that burns 5 dmg/second to enemies standing in it.
- Attack 2 YOROI-SAN: her sensei charges across the arena like Dekatsuyo, 20 dmg.
- Passive STUDY: every 5s she stops (attack bar paused) and studies for 1.0s, taking 20% less
  damage. Afterwards all her attacks permanently gain +7 dmg (not the ramen pool burn).
"""
import math
import random

import pygame

from ..config import *
from ..audio import *
from ..effects import *
from ..world_objects import *
from ..drawing import *
from ..registry import register_image
from ..teams import register_solo
from .base import BaseFighter

SHISA_ORANGE = (240, 150, 70)
BROTH = (236, 168, 80)
YOROI_GOLD = (232, 190, 70)


def draw_ramen_bowl(surf, cx, cy, s=1.0):
    w, h = int(30 * s), int(16 * s)
    pygame.draw.ellipse(surf, BROTH, (cx - w // 2, cy - h // 2 - 3, w, int(h / 1.4)))
    for i in range(3):  # noodles
        pygame.draw.arc(surf, (255, 235, 160), (cx - w // 3 + i * 6, cy - h // 2 - 2, 10, 8), 0, math.pi, 2)
    bowl = [(cx - w // 2, cy - 3), (cx + w // 2, cy - 3), (cx + w // 3, cy + h // 2 + 2), (cx - w // 3, cy + h // 2 + 2)]
    pygame.draw.polygon(surf, (225, 70, 60), bowl)
    pygame.draw.polygon(surf, (90, 30, 30), bowl, 2)
    pygame.draw.line(surf, WHITE, (cx - w // 3, cy + 2), (cx + w // 3, cy + 2), 2)


class RamenPool:
    """Floor hazard (world['floor']): 5 dmg per second to enemies inside, lasts 9s."""
    def __init__(self, x, y, owner):
        self.x, self.y, self.owner = x, y, owner
        self.radius = 100  # 2.5x bigger pool
        self.life = 9.0
        self.alive = True
        self.tick = {}
        self.t = 0.0

    def update(self, dt, enemies, world):
        self.life -= dt
        self.t += dt
        if self.life <= 0:
            self.alive = False
            return
        for e in enemies:
            if not e.alive or e.in_air:
                continue
            # pool is drawn as a flat ellipse (radius wide, radius/2 tall) - match that shape
            rx, ry = self.radius + e.radius * 0.4, self.radius * 0.5 + e.radius * 0.4
            inside = ((e.x - self.x) / rx) ** 2 + ((e.y - self.y) / ry) ** 2 <= 1.0
            self.tick[e] = self.tick.get(e, 0.0) - dt
            if inside and self.tick[e] <= 0:
                self.tick[e] = 1.0
                e.receive_damage(5.0, self.owner, world)
        if random.random() < dt * 12:
            world["particles"].append(Particle(self.x + random.uniform(-70, 70), self.y + random.uniform(-25, 25), (255, 245, 230), 40))

    def draw(self, surf):
        fade = min(1.0, self.life / 0.8)
        r = int(self.radius * (0.6 + 0.4 * min(1.0, self.t / 0.25)))
        s = pygame.Surface((r * 2 + 4, r + 4), pygame.SRCALPHA)
        pygame.draw.ellipse(s, (*BROTH, int(200 * fade)), (2, 2, r * 2, r))
        pygame.draw.ellipse(s, (255, 220, 140, int(160 * fade)), (r // 2, r // 4, r, r // 2))
        for i in range(9):
            a = self.t * 1.5 + i * 0.7
            pygame.draw.arc(s, (255, 240, 190, int(200 * fade)), (r - 12 + math.cos(a) * r * 0.5, r // 2 - 4 + math.sin(a) * r * 0.2, 14, 8), 0, math.pi, 2)
        pygame.draw.ellipse(s, (180, 90, 40, int(180 * fade)), (2, 2, r * 2, r), 2)
        surf.blit(s, s.get_rect(center=(int(self.x), int(self.y))))


class RamenBowlLob:
    """Arcing projectile; hits whoever is near the landing spot, then becomes a RamenPool."""
    def __init__(self, x, y, tx, ty, owner, damage):
        self.sx, self.sy, self.tx, self.ty = x, y, tx, ty
        self.x, self.y = x, y
        self.owner, self.damage = owner, damage
        self.t, self.dur = 0.0, 0.7
        self.alive = True
        self.height = 0.0

    def update(self, dt, enemies, world):
        self.t += dt
        p = min(1.0, self.t / self.dur)
        self.x = self.sx + (self.tx - self.sx) * p
        self.y = self.sy + (self.ty - self.sy) * p
        self.height = math.sin(p * math.pi) * 110
        if p >= 1.0:
            self.alive = False
            SFX_SLAM.play()
            for e in enemies:
                if e.alive and math.hypot(e.x - self.x, e.y - self.y) <= e.radius + 30:
                    e.receive_damage(self.damage, self.owner, world)
            world["floor"].append(RamenPool(self.x, self.y, self.owner))
            for _ in range(12):
                world["particles"].append(Particle(self.x, self.y, BROTH, 170))

    def draw(self, surf):
        sh = pygame.Surface((30, 12), pygame.SRCALPHA)
        pygame.draw.ellipse(sh, (60, 40, 50, 70), sh.get_rect())
        surf.blit(sh, sh.get_rect(center=(int(self.x), int(self.y))))
        draw_ramen_bowl(surf, int(self.x), int(self.y - self.height), 1.0 + self.height / 300)


class YoroiRunner(DekatsuyoRunner):
    def __init__(self, tx, ty, owner, damage):
        super().__init__(tx, ty, owner, damage=damage, sprite_key="YOROI", color=YOROI_GOLD, radius=48, speed=640.0)

    def draw_body(self, surf, cx, cy):
        if super().draw_body(surf, cx, cy):
            return True
        # simple golden armoured runner (fallback when no yoroi image)
        r = self.radius
        pygame.draw.circle(surf, YOROI_GOLD, (cx, cy), r)
        pygame.draw.circle(surf, (120, 90, 30), (cx, cy), r, 4)
        pygame.draw.rect(surf, (90, 70, 40), (cx - r * 0.6, cy - 6, r * 1.2, 12), border_radius=5)  # visor
        pygame.draw.polygon(surf, (255, 225, 110), [(cx - 8, cy - r + 4), (cx, cy - r - 18), (cx + 8, cy - r + 4)])
        for a in (-0.6, 0.6):
            pygame.draw.circle(surf, (250, 215, 100), (int(cx + math.sin(a) * r), int(cy + r * 0.45)), 10)
        return True


class ShisaFighter(BaseFighter):
    def __init__(self, x, y):
        super().__init__("SHISA", x, y, hp=250, color=SHISA_ORANGE, radius=30, speed=220.0)
        self.cd_max = 2.9
        self.cd_timer = 0.0
        self.attack_index = 0
        self.study_timer = 5.0
        self.bonus = 0

    def update(self, dt, enemies, world):
        if not self.alive or self.grabbed_by:
            return
        if self.stun_timer > 0:
            self.stun_timer -= dt
            return
        self.check_enemy_food_pickup(world)
        living = [e for e in enemies if e.alive]
        nearest = min(living, key=lambda e: math.hypot(e.x - self.x, e.y - self.y)) if living else None

        if self.state == "STUDY":
            self.state_timer -= dt
            self.dmg_taken_mult = 0.80
            if self.state_timer <= 0:
                self.state = "ROAM"
                self.dmg_taken_mult = 1.0
                self.bonus += 7
                self.study_timer = 5.0
                SFX_WEED.play()
                world["popups"].append(FloatingPopup(self.x, self.y - 44, f"+7 DMG ({self.bonus})", SHISA_ORANGE, WHITE, 18, 1.1))
            return

        self.study_timer -= dt
        if self.study_timer <= 0:
            self.state = "STUDY"
            self.state_timer = 1.0
            return

        self.move_and_bounce(dt)
        if living:
            self.cd_timer += dt * self.cd_rate()
            if self.cd_timer >= self.cd_max:
                self.cd_timer = 0.0
                if self.attack_index == 0:
                    # lead the target slightly so the bowl lands where they're heading
                    tx = nearest.x + nearest.vx * 0.35
                    ty = nearest.y + nearest.vy * 0.35
                    tx = max(ARENA_RECT.left + 30, min(ARENA_RECT.right - 30, tx))
                    ty = max(ARENA_RECT.top + 30, min(ARENA_RECT.bottom - 30, ty))
                    world["projectiles"].append(RamenBowlLob(self.x, self.y, tx, ty, self, 10 + self.bonus))
                    rx = random.randint(ARENA_RECT.left + 60, ARENA_RECT.right - 60)
                    ry = random.randint(ARENA_RECT.top + 60, ARENA_RECT.bottom - 60)
                    world["projectiles"].append(RamenBowlLob(self.x, self.y, rx, ry, self, 10 + self.bonus))
                    SFX_JUMP.play()
                else:
                    world["hazards"].append(YoroiRunner(nearest.x, nearest.y, self, 20 + self.bonus))
                self.attack_index = (self.attack_index + 1) % 2

    def draw(self, surf, enemies):
        if not self.alive:
            return
        cx, cy = int(self.x), int(self.y)
        draw_ball_avatar(surf, self.type, cx, cy, self.radius)
        if self.state == "STUDY":
            # little open notebook + pencil wiggle
            bx, by = cx, cy + self.radius - 2
            pygame.draw.polygon(surf, WHITE, [(bx - 22, by - 6), (bx, by), (bx + 22, by - 6), (bx + 22, by + 10), (bx, by + 16), (bx - 22, by + 10)])
            pygame.draw.polygon(surf, (90, 80, 100), [(bx - 22, by - 6), (bx, by), (bx + 22, by - 6), (bx + 22, by + 10), (bx, by + 16), (bx - 22, by + 10)], 2)
            pygame.draw.line(surf, (90, 80, 100), (bx, by), (bx, by + 16), 2)
            wig = math.sin(self.state_timer * 30) * 4
            pygame.draw.line(surf, (250, 200, 60), (bx + 6 + wig, by + 2), (bx + 18 + wig, by - 12), 4)
            draw_dashed_circle(surf, (120, 170, 240), (cx, cy), self.radius + 8, 2, 18)
        if self.stun_timer > 0:
            draw_dashed_circle(surf, MEDUSA_PURPLE, (cx, cy), self.radius + 6, 3, 16)


register_image("YOROI", "yoroi", "yoroisan", "yoroi-san", "golden_yoroi")
register_solo("SHISA", "Shisa", SHISA_ORANGE, ShisaFighter)
