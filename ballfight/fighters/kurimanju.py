"""
Kurimanju (250 HP, 2.85s attack cooldown, 2-move cycle)
- Attack 1 BURP: drinks, then a shockwave hits the whole arena. Closer = more damage (28 -> 5)
  and more knockback.
- Attack 2 STICK SWIPE: short lunge in and swipes: 17 dmg, heavy knockback (wall slams hurt 3-9
  depending on speed), and dazes for 3s (enemy attack bar fills 50% slower).
- Passive BEER: every 10s drinks a beer, equal chance of one effect until the next beer:
  +35% damage | +15% defence | takes 20% more damage | attacks 30% slower.
"""
import math
import random

import pygame

from ..config import *
from ..audio import *
from ..effects import *
from ..world_objects import *
from ..drawing import *
from ..fonts import get_font
from ..teams import register_solo
from .base import BaseFighter

KURI_BROWN = (176, 118, 70)
BEER_GOLD = (246, 196, 60)
ARENA_DIAG = math.hypot(ARENA_SIZE, ARENA_SIZE)

BEER_EFFECTS = [
    # (label, colour, dmg_mult, dmg_taken_mult, cd_rate_mult)
    ("ATK +35%", (235, 90, 70), 1.35, 1.0, 1.0),
    ("DEF +15%", (90, 150, 230), 1.0, 0.85, 1.0),
    ("DEF -20%", (150, 110, 170), 1.0, 1.20, 1.0),
    ("SLOW -30%", (130, 130, 140), 1.0, 1.0, 0.70),
]


class BurpWave:
    """Expanding shockwave ring (visual only)."""
    def __init__(self, x, y):
        self.x, self.y = x, y
        self.life = self.max_life = 0.55

    def update(self, dt):
        self.life -= dt

    def draw(self, surf):
        if self.life <= 0:
            return
        t = 1 - self.life / self.max_life
        for k, col in enumerate(((255, 236, 150), (246, 196, 60), (255, 255, 255))):
            r = int(30 + t * ARENA_DIAG * (1 - k * 0.12))
            pygame.draw.circle(surf, col, (int(self.x), int(self.y)), r, max(1, int(9 * (1 - t))))


def draw_beer_mug(surf, cx, cy, tilt=0.0, scale=1.0):
    w, h = int(16 * scale), int(20 * scale)
    mug = pygame.Surface((w + 10, h + 8), pygame.SRCALPHA)
    pygame.draw.rect(mug, BEER_GOLD, (2, 6, w, h), border_radius=3)
    pygame.draw.rect(mug, (255, 250, 240), (0, 0, w + 4, 9), border_radius=5)  # foam
    pygame.draw.rect(mug, (90, 60, 30), (2, 6, w, h), 2, border_radius=3)
    pygame.draw.arc(mug, (90, 60, 30), (w - 2, 10, 12, 12), -math.pi / 2, math.pi / 2, 3)
    rot = pygame.transform.rotate(mug, tilt)
    surf.blit(rot, rot.get_rect(center=(cx, cy)))


def draw_stick(surf, cx, cy, angle, length=50, color=(140, 95, 55)):
    ex, ey = cx + math.cos(angle) * length, cy + math.sin(angle) * length
    pygame.draw.line(surf, (70, 45, 25), (cx, cy), (ex, ey), 8)
    pygame.draw.line(surf, color, (cx, cy), (ex, ey), 5)
    pygame.draw.circle(surf, color, (int(ex), int(ey)), 5)


class KurimanjuFighter(BaseFighter):
    def __init__(self, x, y):
        super().__init__("KURIMANJU", x, y, hp=250, color=KURI_BROWN, radius=31, speed=210.0)
        self.cd_max = 2.85
        self.cd_timer = 0.0
        self.attack_index = 0
        self.beer_timer = 10.0
        self.beer_anim = 0.0
        self.buff = None
        self.target = None
        self.swipe_done = False

    # ---- passive ----
    def drink_beer(self, world):
        label, col, dm, dt_mult, cdm = random.choice(BEER_EFFECTS)
        self.buff = (label, col)
        self.dmg_mult, self.dmg_taken_mult, self.cd_rate_mult = dm, dt_mult, cdm
        self.beer_anim = 0.7
        SFX_WEED.play()
        world["popups"].append(FloatingPopup(self.x, self.y - 44, label, col, WHITE, 18, 1.2))
        for _ in range(10):
            world["particles"].append(Particle(self.x, self.y - 20, BEER_GOLD, 120))

    def do_burp(self, enemies, world):
        SFX_SLAM.play()
        world["effects"].append(BurpWave(self.x, self.y))
        world["shake"] = max(world.get("shake", 0), 8)
        for e in enemies:
            if not e.alive:
                continue
            d = math.hypot(e.x - self.x, e.y - self.y)
            close = max(0.0, min(1.0, 1.0 - d / (ARENA_DIAG * 0.85)))
            e.receive_damage((5 + 23 * close) * self.dmg_mult, self, world)
            if d > 0:
                push = 200 + 700 * close
                e.apply_knockback((e.x - self.x) / d * push, (e.y - self.y) / d * push, self)

    def update(self, dt, enemies, world):
        if not self.alive or self.grabbed_by:
            return
        self.beer_anim = max(0.0, self.beer_anim - dt)
        self.beer_timer -= dt
        if self.beer_timer <= 0:
            self.beer_timer += 10.0
            self.drink_beer(world)

        if self.stun_timer > 0:
            self.stun_timer -= dt
            return
        self.check_enemy_food_pickup(world)
        living = [e for e in enemies if e.alive]
        nearest = min(living, key=lambda e: math.hypot(e.x - self.x, e.y - self.y)) if living else None

        if self.state == "BURP_DRINK":  # tilting the mug back
            self.state_timer -= dt
            if self.state_timer <= 0:
                self.do_burp(living, world)
                self.state = "ROAM"
            return

        if self.state == "SWIPE_DASH":
            self.state_timer -= dt
            tgt = self.target if (self.target and self.target.alive) else nearest
            if tgt:
                ang = math.atan2(tgt.y - self.y, tgt.x - self.x)
                self.weapon_angle = ang - 1.3
                self.x += math.cos(ang) * 560 * dt
                self.y += math.sin(ang) * 560 * dt
                self.clamp_to_walls()
                if math.hypot(tgt.x - self.x, tgt.y - self.y) <= self.radius + tgt.radius + 40:
                    self.state_timer = 0
            if self.state_timer <= 0:
                self.state = "SWIPE"
                self.state_timer = 0.28
                self.swipe_done = False
                SFX_SPIN.play()
            return

        if self.state == "SWIPE":
            self.state_timer -= dt
            self.weapon_angle += 9.5 * dt
            if not self.swipe_done:
                self.swipe_done = True
                for e in living:
                    d = math.hypot(e.x - self.x, e.y - self.y)
                    if d <= self.radius + e.radius + 62:
                        e.receive_damage(17 * self.dmg_mult, self, world)
                        e.apply_daze(3.0)
                        if d > 0:
                            e.apply_knockback((e.x - self.x) / d * 1250, (e.y - self.y) / d * 1250, self, wall_damage=True)
                        world["popups"].append(FloatingPopup(e.x, e.y - 50, "DAZED", (245, 190, 60), WHITE, 16, 0.9))
            if self.state_timer <= 0:
                self.state = "ROAM"
            return

        self.move_and_bounce(dt)
        if living:
            self.cd_timer += dt * self.cd_rate()
            if self.cd_timer >= self.cd_max:
                self.cd_timer = 0.0
                if self.attack_index == 0:
                    self.state = "BURP_DRINK"
                    self.state_timer = 0.55
                    self.beer_anim = 0.55
                else:
                    self.state = "SWIPE_DASH"
                    self.state_timer = 0.28  # shorter dash (was 0.55s ~ 300px, now ~155px)
                    self.target = nearest
                self.attack_index = (self.attack_index + 1) % 2

    def draw(self, surf, enemies):
        if not self.alive:
            return
        cx, cy = int(self.x), int(self.y)
        if self.state in ("SWIPE_DASH", "SWIPE"):
            draw_stick(surf, cx, cy, self.weapon_angle, 64)
        else:
            draw_stick(surf, cx, cy, self.weapon_angle * 0.3 + 0.6, 40)
        draw_ball_avatar(surf, self.type, cx, cy, self.radius)
        if self.beer_anim > 0 or self.state == "BURP_DRINK":
            draw_beer_mug(surf, cx + 24, cy - 18, tilt=40 * math.sin(self.beer_anim * 6), scale=1.1)
        if self.buff:
            label, col = self.buff
            t = get_font(11).render(label, True, WHITE)
            r = t.get_rect(center=(cx, cy + self.radius + 14)).inflate(8, 2)
            pygame.draw.rect(surf, col, r, border_radius=6)
            surf.blit(t, t.get_rect(center=r.center))
        if self.stun_timer > 0:
            draw_dashed_circle(surf, MEDUSA_PURPLE, (cx, cy), self.radius + 6, 3, 16)


register_solo("KURIMANJU", "Kurimanju", KURI_BROWN, KurimanjuFighter, image=["kurimanju", "kuromanju"])
