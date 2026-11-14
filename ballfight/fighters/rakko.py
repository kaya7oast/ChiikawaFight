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
# CHARACTER 3: RAKKO (250 HP, 2.8s CD, Moves during Counter)
# ==========================================
class RakkoFighter(BaseFighter):
    def __init__(self, x, y):
        super().__init__("RAKKO", x, y, hp=250, color=RAKKO_BROWN, radius=31, speed=225.0)
        self.cd_max = 2.8
        self.cd_timer = 0.0
        self.attack_index = 0
        self.charge_vx = 0.0
        self.charge_vy = 0.0
        self.hit_targets = set()
        self.explosion_radius = 135

    def receive_damage(self, amount, attacker, world):
        if not self.alive or self.in_air:
            return False

        if self.state == "COUNTER":
            reduced = amount * 0.10
            self.hp = max(0.0, self.hp - reduced)
            SFX_COUNTER.play()
            num_val = max(1, int(round(reduced)))
            world["popups"].append(
                FloatingPopup(self.x, self.y - 28, f"-{num_val}", DEKATSUYO_GOLD, WHITE, 22)
            )
            if attacker and attacker.alive:
                old_x, old_y = self.x, self.y
                ang = math.atan2(attacker.y - old_y, attacker.x - old_x)
                self.x = max(
                    ARENA_RECT.left + self.radius,
                    min(ARENA_RECT.right - self.radius, attacker.x + math.cos(ang) * 48),
                )
                self.y = max(
                    ARENA_RECT.top + self.radius,
                    min(ARENA_RECT.bottom - self.radius, attacker.y + math.sin(ang) * 48),
                )
                world["effects"].append(SlashLineEffect(old_x, old_y, self.x, self.y, WHITE))
                attacker.receive_damage(15.0, self, world)

            self.state = "ROAM"
            self.dmg_taken_mult = 1.0
            self.cd_timer = 0.0
            return True

        return super().receive_damage(amount, attacker, world)

    def update(self, dt, enemies, world):
        if not self.alive or self.grabbed_by:
            return
        if self.stun_timer > 0:
            self.stun_timer -= dt
            return

        self.check_enemy_food_pickup(world)
        living = [e for e in enemies if e.alive]
        nearest = (
            min(living, key=lambda e: math.hypot(e.x - self.x, e.y - self.y))
            if living
            else None
        )

        if self.state == "ATK1_READY":
            self.state_timer -= dt
            if nearest:
                self.weapon_angle = math.atan2(nearest.y - self.y, nearest.x - self.x)
            if self.state_timer <= 0:
                self.state = "ATK1_CHARGE"
                self.state_timer = 0.38
                self.hit_targets.clear()
                self.charge_vx = math.cos(self.weapon_angle) * 760.0
                self.charge_vy = math.sin(self.weapon_angle) * 760.0
                SFX_CHARGE.play()
            return

        if self.state == "ATK1_CHARGE":
            self.state_timer -= dt
            self.x += self.charge_vx * dt
            self.y += self.charge_vy * dt
            self.clamp_to_walls()
            for e in living:
                if e not in self.hit_targets and math.hypot(self.x - e.x, self.y - e.y) <= self.radius + e.radius + 24:
                    self.hit_targets.add(e)
                    e.receive_damage(10.0, self, world)
                    self.state_timer = 0.0
            if self.state_timer <= 0:
                self.state = "ATK1_SPIN"
                self.state_timer = 0.45
                self.hit_targets.clear()
                SFX_SPIN.play()
            return

        if self.state == "ATK1_SPIN":
            self.state_timer -= dt
            self.weapon_angle += 28.0 * dt
            for e in living:
                if e not in self.hit_targets and math.hypot(self.x - e.x, self.y - e.y) <= self.radius + e.radius + 54:
                    self.hit_targets.add(e)
                    e.receive_damage(20.0, self, world)
            if self.state_timer <= 0:
                self.state = "ROAM"
                self.cd_timer = 0.0
            return

        if self.state == "CAR_READY":
            self.state_timer -= dt
            self.dmg_taken_mult = 0.20
            if nearest:
                self.weapon_angle = math.atan2(nearest.y - self.y, nearest.x - self.x)
            if self.state_timer <= 0:
                self.state = "CAR_CHARGE"
                self.hit_targets.clear()
                car_speed = 680.0
                self.charge_vx = math.cos(self.weapon_angle) * car_speed
                self.charge_vy = math.sin(self.weapon_angle) * car_speed
                SFX_CAR.play()
                play_voice("rakko_carhonk", cooldown=0)
            return

        if self.state == "CAR_CHARGE":
            self.dmg_taken_mult = 0.20
            self.x += self.charge_vx * dt
            self.y += self.charge_vy * dt
            for e in living:
                if e not in self.hit_targets and math.hypot(self.x - e.x, self.y - e.y) <= self.radius + e.radius + 14:
                    self.hit_targets.add(e)
                    if e.receive_damage(30.0, self, world):
                        e.apply_stun(0.50, world)

            if self.clamp_to_walls():
                SFX_EXPLODE.play()
                world["effects"].append(RingEffect(self.x, self.y, self.explosion_radius, CAR_PINK))
                for _ in range(24):
                    world["particles"].append(Particle(self.x, self.y, CAR_PINK, 230))
                for e in living:
                    if math.hypot(self.x - e.x, self.y - e.y) <= self.explosion_radius + e.radius:
                        e.receive_damage(20.0, self, world)
                self.state = "ROAM"
                self.dmg_taken_mult = 1.0
                self.cd_timer = 0.0
            return

        if self.state == "COUNTER":
            self.state_timer -= dt
            self.move_and_bounce(dt)
            if self.state_timer <= 0:
                self.state = "ROAM"
                self.dmg_taken_mult = 1.0
                self.cd_timer = 0.0
            return

        self.dmg_taken_mult = 1.0
        self.move_and_bounce(dt)
        if living:
            self.cd_timer += dt * self.cd_rate()
            if self.cd_timer >= self.cd_max:
                self.cd_timer = 0.0
                if self.attack_index == 0:
                    self.state = "ATK1_READY"
                    self.state_timer = 0.45
                elif self.attack_index == 1:
                    self.state = "CAR_READY"
                    self.state_timer = 0.40
                else:
                    self.state = "COUNTER"
                    self.state_timer = 2.0
                self.attack_index = (self.attack_index + 1) % 3

    def draw(self, surf, enemies):
        if not self.alive:
            return
        cx, cy = int(self.x), int(self.y)

        if self.state in ("CAR_READY", "CAR_CHARGE"):
            if self.state == "CAR_READY" and enemies:
                living = [e for e in enemies if e.alive]
                if living:
                    t = min(living, key=lambda e: math.hypot(e.x - self.x, e.y - self.y))
                    draw_dashed_arrow(surf, CAR_PINK, (self.x, self.y), (t.x, t.y), 3)
            draw_pink_car(surf, cx, cy, self.weapon_angle)
            draw_ball_avatar(surf, "RAKKO", cx, cy, int(self.radius * 0.78))
            return

        if self.state == "COUNTER":
            draw_dashed_circle(surf, DEKATSUYO_GOLD, (cx, cy), self.radius + 16, 3, 20)
            pygame.draw.circle(surf, (255, 240, 150), (cx, cy), self.radius + 8, 2)

        if self.state == "ATK1_SPIN":
            pygame.draw.circle(surf, RAKKO_BROWN, (cx, cy), self.radius + 50, 4)
            draw_rakko_sword(surf, cx, cy, self.weapon_angle, 54, 1.3)
        else:
            draw_rakko_sword(surf, cx, cy, self.weapon_angle, 38, 1.0)

        draw_ball_avatar(surf, "RAKKO", cx, cy, self.radius)
        if self.stun_timer > 0:
            draw_dashed_circle(surf, MEDUSA_PURPLE, (cx, cy), self.radius + 6, 3, 16)


# ==========================================


register_solo("RAKKO", "Rakko", RAKKO_BROWN, RakkoFighter)
