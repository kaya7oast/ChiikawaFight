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


# ==========================================
# CHARACTER 2: MOMONGA (3.2s CD, Dekatsuyo aims at Enemy)
# ==========================================
class MomongaFighter(BaseFighter):
    def __init__(self, x, y):
        super().__init__("MOMONGA", x, y, hp=250, color=MOMONGA_CYAN, radius=31, speed=215.0)
        self.cd_max = 3.2
        self.cd_timer = 0.0
        self.air_duration = 1.7
        self.air_timer = 0.0
        self.air_homing_speed = 115.0
        self.jump_count = 0
        self.slam_radius = 125

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
                for e in living:
                    if math.hypot(e.x - self.x, e.y - self.y) <= self.slam_radius + e.radius:
                        e.receive_damage(25.0, self, world)
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
                world["hazards"].append(DekatsuyoRunner(target_enemy.x, target_enemy.y, self))
                play_voice("momonga_scream", cooldown=0)

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
            draw_ball_avatar(surf, "MOMONGA", cx, cy, self.radius)
            if self.stun_timer > 0:
                draw_dashed_circle(surf, MEDUSA_PURPLE, (cx, cy), self.radius + 6, 3, 16)


register_solo("MOMONGA", "Momonga", MOMONGA_CYAN, MomongaFighter)
