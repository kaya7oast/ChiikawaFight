import math
import random

import pygame

from ..config import *
from ..audio import *
from ..effects import *
from ..world_objects import *
from ..drawing import *
from ..registry import register_sprite, register_roster
from ..teams import register_solo
from ..voices import play_voice
from .base import BaseFighter
from .kani import BookProjectile, BookVolley, BOOK_COLORS


# ==========================================
# CHARACTER 2: MOMONGA (3.2s CD, Dekatsuyo aims at Enemy)
# - Passive SHOUT: after Dekatsuyo misses, cone shout (like Anoko's stare): 5 dmg, heavy
#   knockback + daze.
# - Passive CRYBABY: missing 2 attacks in a row -> cries for 1s, Kani walks in and throws
#   3 books (10 dmg each, 4 wall bounces).
# ==========================================
SHOUT_HALF_ANGLE = 0.5    # cone half-width (radians)
SHOUT_LENGTH = 270.0
SHOUT_STARTUP = 1.0
SHOUT_DELAY = 0.2         # short pause after Dekatsuyo misses before starting to shout
SHOUT_DAZE = 2.0
CRY_TIME = 1.0


class MomongaDekatsuyo(DekatsuyoRunner):
    """Dekatsuyo that tells Momonga whether it hit anything when it finishes its run."""
    def __init__(self, *a, on_done=None, **kw):
        super().__init__(*a, **kw)
        self.on_done = on_done

    def update(self, dt, enemies, world):
        super().update(dt, enemies, world)
        if not self.alive and self.on_done:
            self.on_done(bool(self.hit_targets), world)
            self.on_done = None


class KaniHelper:
    """Kani runs in from the nearest wall, throws 3 books, then runs back out. Can't be hit."""
    SPEED = 420.0

    def __init__(self, owner):
        self.owner = owner
        ox, oy = owner.x, owner.y
        # enter from whichever wall is closest to Momonga
        d = {"L": ox - ARENA_RECT.left, "R": ARENA_RECT.right - ox, "T": oy - ARENA_RECT.top, "B": ARENA_RECT.bottom - oy}
        side = min(d, key=d.get)
        self.home = {"L": (ARENA_RECT.left - 40, oy), "R": (ARENA_RECT.right + 40, oy),
                     "T": (ox, ARENA_RECT.top - 40), "B": (ox, ARENA_RECT.bottom + 40)}[side]
        self.x, self.y = self.home
        self.phase = "IN"
        self.timer = 0.0
        self.books_left = 3
        self.volley = BookVolley()
        self.volley.total = 3
        self.alive = True
        self.radius = 26

    def _move_to(self, tx, ty, dt):
        dx, dy = tx - self.x, ty - self.y
        dist = math.hypot(dx, dy)
        step = self.SPEED * dt
        if dist <= step:
            self.x, self.y = tx, ty
            return True
        self.x += dx / dist * step
        self.y += dy / dist * step
        return False

    def update(self, dt, enemies, world):
        o = self.owner
        if self.phase == "IN":
            # stop right next to Momonga
            ang = math.atan2(self.home[1] - o.y, self.home[0] - o.x)
            if self._move_to(o.x + math.cos(ang) * 60, o.y + math.sin(ang) * 60, dt):
                self.phase, self.timer = "THROW", 0.1
        elif self.phase == "THROW":
            self.timer -= dt
            if self.timer <= 0 and self.books_left > 0:
                living = [e for e in enemies if e.alive]
                tgt = min(living, key=lambda e: math.hypot(e.x - self.x, e.y - self.y)) if living else None
                aim = math.atan2(tgt.y - self.y, tgt.x - self.x) if tgt else random.uniform(0, math.tau)
                spread = (self.books_left - 2) * 0.35  # left / centre / right
                world["projectiles"].append(BookProjectile(self.x, self.y, aim + spread, o, self.volley,
                                                           BOOK_COLORS[self.books_left % len(BOOK_COLORS)], bounces=4))
                SFX_SPIN.play()
                self.books_left -= 1
                self.timer = 0.25
            if self.books_left <= 0 and self.timer <= 0:
                self.phase = "OUT"
        else:
            if self._move_to(*self.home, dt):
                self.alive = False

    def draw(self, surf):
        draw_ball_avatar(surf, "KANI", int(self.x), int(self.y), self.radius)


class Tear:
    def __init__(self, x, y, side):
        self.x, self.y = x + side * 12, y - 6
        self.vx, self.vy = side * random.uniform(40, 90), random.uniform(-120, -60)
        self.life = 0.5

    def update(self, dt):
        self.vy += 500 * dt
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.life -= dt

    def draw(self, surf):
        if self.life > 0:
            pygame.draw.circle(surf, (110, 185, 245), (int(self.x), int(self.y)), 4)
            pygame.draw.circle(surf, WHITE, (int(self.x) - 1, int(self.y) - 1), 1)


class ShoutWave:
    """Arcs flying out along the shout cone (visual only)."""
    def __init__(self, x, y, ang):
        self.x, self.y, self.ang = x, y, ang
        self.life = self.max_life = 0.35

    def update(self, dt):
        self.life -= dt

    def draw(self, surf):
        if self.life <= 0:
            return
        t = 1 - self.life / self.max_life
        for k in range(3):
            r = int(40 + (t + k * 0.25) % 1.0 * SHOUT_LENGTH)
            rect = pygame.Rect(self.x - r, self.y - r, r * 2, r * 2)
            pygame.draw.arc(surf, (255, 255, 255), rect, -self.ang - SHOUT_HALF_ANGLE, -self.ang + SHOUT_HALF_ANGLE, 6)
            pygame.draw.arc(surf, MOMONGA_CYAN, rect, -self.ang - SHOUT_HALF_ANGLE, -self.ang + SHOUT_HALF_ANGLE, 3)


class MomongaFighter(BaseFighter):
    COLLIDE_STATES = BaseFighter.COLLIDE_STATES | {"SHOUT_STARTUP", "CRY"}

    def __init__(self, x, y):
        super().__init__("MOMONGA", x, y, hp=250, color=MOMONGA_CYAN, radius=31, speed=215.0)
        self.cd_max = 3.2
        self.cd_timer = 0.0
        self.air_duration = 1.7
        self.air_timer = 0.0
        self.air_homing_speed = 115.0
        self.jump_count = 0
        self.slam_radius = 125
        self.shout_delay = None   # counting down to the shout after Dekatsuyo misses
        self.miss_streak = 0      # attacks missed in a row (2 -> cry + Kani)
        self.tear_timer = 0.0

    def update(self, dt, enemies, world):
        if not self.alive or self.grabbed_by:
            return
        if self.stun_timer > 0 and not self.in_air:
            self.stun_timer -= dt
            return

        self.check_enemy_food_pickup(world)
        living = [e for e in enemies if e.alive]

        if self.in_air:
            self.air_timer -= dt
            if living:
                nearest = min(living, key=lambda e: math.hypot(e.x - self.x, e.y - self.y))
                dx, dy = nearest.x - self.x, nearest.y - self.y
                dist = math.hypot(dx, dy)
                if dist > 4.0:
                    self.x += (dx / dist) * self.air_homing_speed * dt
                    self.y += (dy / dist) * self.air_homing_speed * dt
                    self.vx = (dx / dist) * self.base_speed
                    self.vy = (dy / dist) * self.base_speed
            self.bounce_walls()

            if self.air_timer <= 0:
                self.in_air = False
                SFX_SLAM.play()
                world["effects"].append(RingEffect(self.x, self.y, self.slam_radius, MOMONGA_CYAN))
                for _ in range(20):
                    world["particles"].append(Particle(self.x, self.y, MOMONGA_CYAN, 210))
                landed = False
                for e in living:
                    if math.hypot(e.x - self.x, e.y - self.y) <= self.slam_radius + e.radius:
                        if e.receive_damage(25.0, self, world):
                            landed = True
                self.register_attack(landed, world)
            return

        # --- crying (missed 2 in a row): stands still, attack bar paused ---
        if self.state == "CRY":
            self.state_timer -= dt
            self.tear_timer -= dt
            if self.tear_timer <= 0:
                self.tear_timer = 0.08
                world["effects"].append(Tear(self.x, self.y, random.choice((-1, 1))))
            if self.state_timer <= 0:
                self.state = "ROAM"
            return

        # --- cone shout (passive: 1s after every 2nd hit, 1s startup) ---
        if self.shout_delay is not None:
            self.shout_delay -= dt
            if self.shout_delay <= 0 and self.state == "ROAM":
                self.shout_delay = None
                self.state, self.state_timer = "SHOUT_STARTUP", SHOUT_STARTUP
        if self.state == "SHOUT_STARTUP":
            self.state_timer -= dt
            self.move_and_bounce(dt)
            if living:
                tgt = min(living, key=lambda e: math.hypot(e.x - self.x, e.y - self.y))
                self.weapon_angle = math.atan2(tgt.y - self.y, tgt.x - self.x)
            if self.state_timer <= 0:
                self.state = "ROAM"
                self.do_shout(living, world)
            return

        self.move_and_bounce(dt)
        self.cd_timer += dt * self.cd_rate()
        if self.cd_timer >= self.cd_max:
            self.cd_timer = 0.0
            self.in_air = True
            self.air_timer = self.air_duration
            self.jump_count += 1
            SFX_JUMP.play()
            if self.jump_count % 3 != 0:
                play_voice("momonga_ushya", "momonga_silly", cooldown=2.5)
            if self.jump_count % 3 == 0:
                target_enemy = random.choice(living) if living else self
                world["hazards"].append(MomongaDekatsuyo(target_enemy.x, target_enemy.y, self,
                                                          on_done=self.dekatsuyo_done))
                play_voice("momonga_scream", cooldown=0)

    def register_attack(self, hit, world):
        """Slam / Dekatsuyo result. 2 misses in a row -> cry for 1s and Kani comes to help."""
        if hit:
            self.miss_streak = 0
            return
        self.miss_streak += 1
        if self.miss_streak >= 2 and self.alive:
            self.miss_streak = 0
            self.state, self.state_timer = "CRY", CRY_TIME
            world["popups"].append(FloatingPopup(self.x, self.y - 50, "WAAAH!", (110, 185, 245), WHITE, 18, 1.0))
            world["hazards"].append(KaniHelper(self))

    def dekatsuyo_done(self, hit, world):
        if not hit and self.alive and self.shout_delay is None and self.state != "SHOUT_STARTUP":
            self.shout_delay = SHOUT_DELAY
        self.register_attack(hit, world)

    def do_shout(self, living, world):
        SFX_STARE.play()
        play_voice("momonga_silly", "momonga_scream", cooldown=0)
        world["effects"].append(ShoutWave(self.x, self.y, self.weapon_angle))
        for e in living:
            if e.in_air:
                continue
            dx, dy = e.x - self.x, e.y - self.y
            dist = math.hypot(dx, dy)
            ang_diff = abs((math.atan2(dy, dx) - self.weapon_angle + math.pi) % math.tau - math.pi)
            if dist <= SHOUT_LENGTH + e.radius and ang_diff <= SHOUT_HALF_ANGLE:
                e.receive_damage(5.0, self, world)
                e.apply_daze(SHOUT_DAZE)
                world["popups"].append(FloatingPopup(e.x, e.y - 50, "DAZED", (245, 190, 60), WHITE, 16, 0.9))
                if dist > 0:
                    e.apply_knockback(dx / dist * 1300, dy / dist * 1300, self)

    def draw(self, surf, enemies):
        if not self.alive:
            return
        cx, cy = int(self.x), int(self.y)
        if self.in_air:
            draw_dashed_circle(surf, MOMONGA_CYAN, (cx, cy), self.slam_radius, 2, 28)
            pygame.draw.ellipse(surf, (160, 175, 190), (cx - 24, cy - 12, 48, 24))
            progress = 1.0 - (self.air_timer / self.air_duration)
            arc = math.sin(progress * math.pi)
            air_cy = cy - int(arc * 78)
            air_r = int(self.radius * (1.0 + 0.35 * arc))
            draw_ball_avatar(surf, "MOMONGA", cx, air_cy, air_r)
        else:
            if self.state == "SHOUT_STARTUP":  # cone warning, like Anoko's stare
                cone = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
                p = 1 - self.state_timer / SHOUT_STARTUP
                pts = [(cx, cy)] + [(cx + math.cos(self.weapon_angle - SHOUT_HALF_ANGLE + 2 * SHOUT_HALF_ANGLE * i / 16) * SHOUT_LENGTH,
                                     cy + math.sin(self.weapon_angle - SHOUT_HALF_ANGLE + 2 * SHOUT_HALF_ANGLE * i / 16) * SHOUT_LENGTH)
                                    for i in range(17)]
                pygame.draw.polygon(cone, (96, 178, 230, int(50 + 70 * p)), pts)
                pygame.draw.polygon(cone, (96, 178, 230, 220), pts, 3)
                surf.blit(cone, (0, 0))
            draw_ball_avatar(surf, "MOMONGA", cx, cy, self.radius)
            if self.stun_timer > 0:
                draw_dashed_circle(surf, MEDUSA_PURPLE, (cx, cy), self.radius + 6, 3, 16)


register_solo("MOMONGA", "Momonga", MOMONGA_CYAN, MomongaFighter)
