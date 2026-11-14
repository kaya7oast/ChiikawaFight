import math
import random

import pygame

from ..config import *
from ..audio import *
from ..effects import *


# ==========================================
# MODULAR BASE FIGHTER
# ==========================================
class BaseFighter:
    # States in which this ball physically bounces off other balls (override per character if needed)
    COLLIDE_STATES = {"ROAM", "COUNTER", "SPIN", "CRAZY_BOUNCE", "TAIL_STARTUP", "TAIL_SPIN", "MEDUSA_STARTUP"}

    def __init__(self, char_type, x, y, hp, color, radius=29, speed=225.0):
        self.type = char_type
        self.x = float(x)
        self.y = float(y)
        self.hp = float(hp)
        self.max_hp = float(hp)
        self.color = color
        self.radius = radius
        self.base_speed = speed

        ang = random.uniform(0, math.tau)
        self.vx = math.cos(ang) * self.base_speed
        self.vy = math.sin(ang) * self.base_speed
        self.weapon_angle = random.uniform(0, math.tau)

        self.state = "ROAM"
        self.state_timer = 0.0
        self.stun_timer = 0.0
        self.grabbed_by = None
        self.in_air = False
        self.dmg_taken_mult = 1.0
        self.hit_flash = 0.0  # white flash timer when damaged

        # Shared status effects (used by any character)
        self.dmg_mult = 1.0        # outgoing damage multiplier (buffs)
        self.cd_rate_mult = 1.0    # attack-bar fill speed multiplier (buffs/debuffs)
        self.daze_timer = 0.0      # dazed = attack bar fills 50% slower
        self.kb_vx = 0.0           # knockback velocity (applied on top of normal movement)
        self.kb_vy = 0.0
        self.kb_wall_damage = False
        self.kb_attacker = None
        self.kb_wall_cd = 0.0

    # ---------- shared status helpers ----------
    def cd_rate(self):
        """Multiply dt by this when filling the attack bar."""
        return self.cd_rate_mult * (0.5 if self.daze_timer > 0 else 1.0)

    def apply_daze(self, duration):
        if self.alive:
            self.daze_timer = max(self.daze_timer, duration)

    def apply_knockback(self, vx, vy, attacker=None, wall_damage=False):
        if not self.alive or self.in_air or self.grabbed_by:
            return
        self.kb_vx += vx
        self.kb_vy += vy
        self.kb_attacker = attacker
        self.kb_wall_damage = self.kb_wall_damage or wall_damage

    def update_status(self, dt, world):
        """Called once per frame by the game loop for every fighter."""
        if self.daze_timer > 0:
            self.daze_timer -= dt
        if self.kb_wall_cd > 0:
            self.kb_wall_cd -= dt
        spd = math.hypot(self.kb_vx, self.kb_vy)
        if spd < 25 or not self.alive or self.in_air or self.grabbed_by:
            self.kb_vx = self.kb_vy = 0.0
            self.kb_wall_damage = False
            return
        self.x += self.kb_vx * dt
        self.y += self.kb_vy * dt
        decay = math.exp(-3.0 * dt)
        self.kb_vx *= decay
        self.kb_vy *= decay
        hit = False
        if self.x - self.radius < ARENA_RECT.left:
            self.x, self.kb_vx, hit = ARENA_RECT.left + self.radius, abs(self.kb_vx) * 0.6, True
        elif self.x + self.radius > ARENA_RECT.right:
            self.x, self.kb_vx, hit = ARENA_RECT.right - self.radius, -abs(self.kb_vx) * 0.6, True
        if self.y - self.radius < ARENA_RECT.top:
            self.y, self.kb_vy, hit = ARENA_RECT.top + self.radius, abs(self.kb_vy) * 0.6, True
        elif self.y + self.radius > ARENA_RECT.bottom:
            self.y, self.kb_vy, hit = ARENA_RECT.bottom - self.radius, -abs(self.kb_vy) * 0.6, True
        if hit and self.kb_wall_damage and self.kb_wall_cd <= 0 and spd > 160:
            self.kb_wall_cd = 0.18
            dmg = max(3, min(9, int(round(spd / 110))))  # faster slam = more damage
            self.receive_damage(dmg, self.kb_attacker, world)
            world["effects"].append(RingEffect(self.x, self.y, self.radius + 14, (255, 255, 255)))

    def bounce_speed(self):
        """Speed this ball leaves a ball-to-ball collision with."""
        return self.base_speed

    @property
    def alive(self):
        return self.hp > 0

    def apply_stun(self, duration, world):
        if not self.alive or self.in_air:
            return
        self.stun_timer = max(self.stun_timer, duration)

    def receive_damage(self, amount, attacker, world):
        """Clean damage pipeline: shows only numeric damage popups (-15, -20, etc.)."""
        if not self.alive or self.in_air:
            return False

        actual = amount * self.dmg_taken_mult
        self.hp = max(0.0, self.hp - actual)
        SFX_HIT.play()
        self.hit_flash = 0.14
        world["shake"] = max(world.get("shake", 0.0), min(9.0, actual * 0.22))
        num_val = max(1, int(round(actual)))
        col = attacker.color if attacker else HP_GREEN
        world["popups"].append(FloatingPopup(self.x, self.y - 28, f"-{num_val}", col, WHITE, 22))
        for _ in range(12):
            world["particles"].append(Particle(self.x, self.y, col, 180))
        return True

    def check_enemy_food_pickup(self, world):
        """If a non-Usagi fighter touches Usagi's spawned food first, they heal +1 HP."""
        for f_item in world["foods"]:
            if f_item.alive and f_item.claimed_by is None and f_item.owner is not self:
                if math.hypot(self.x - f_item.x, self.y - f_item.y) <= self.radius + f_item.radius:
                    f_item.alive = False
                    self.hp = min(self.max_hp, self.hp + 1.0)
                    SFX_WEED.play()
                    world["popups"].append(
                        FloatingPopup(self.x, self.y - 28, "+1", HP_GREEN, WHITE, 20)
                    )

    def move_and_bounce(self, dt, speed_override=None):
        spd = speed_override if speed_override is not None else self.base_speed
        cur = math.hypot(self.vx, self.vy)
        if cur > 0:
            self.vx = (self.vx / cur) * spd
            self.vy = (self.vy / cur) * spd
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.weapon_angle += 3.0 * dt
        return self.bounce_walls()

    def clamp_to_walls(self):
        hit_wall = False
        if self.x - self.radius <= ARENA_RECT.left:
            self.x = ARENA_RECT.left + self.radius
            hit_wall = True
        elif self.x + self.radius >= ARENA_RECT.right:
            self.x = ARENA_RECT.right - self.radius
            hit_wall = True
        if self.y - self.radius <= ARENA_RECT.top:
            self.y = ARENA_RECT.top + self.radius
            hit_wall = True
        elif self.y + self.radius >= ARENA_RECT.bottom:
            self.y = ARENA_RECT.bottom - self.radius
            hit_wall = True
        return hit_wall

    def bounce_walls(self):
        bounced = False
        if self.x - self.radius < ARENA_RECT.left:
            self.x = ARENA_RECT.left + self.radius
            self.vx = abs(self.vx)
            bounced = True
        elif self.x + self.radius > ARENA_RECT.right:
            self.x = ARENA_RECT.right - self.radius
            self.vx = -abs(self.vx)
            bounced = True

        if self.y - self.radius < ARENA_RECT.top:
            self.y = ARENA_RECT.top + self.radius
            self.vy = abs(self.vy)
            bounced = True
        elif self.y + self.radius > ARENA_RECT.bottom:
            self.y = ARENA_RECT.bottom - self.radius
            self.vy = -abs(self.vy)
            bounced = True

        if bounced and not self.in_air:
            SFX_BOUNCE.play()
        return bounced


# ==========================================
