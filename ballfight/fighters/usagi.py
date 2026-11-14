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
from .base import BaseFighter


# ==========================================
# CHARACTER 4: USAGI (2.9s CD, Spin 22 / 5 Seeds x 9 / 5s Crazy Bounce 10 dmg + 30% DR)
# ==========================================
class UsagiFighter(BaseFighter):
    """
    Usagi (250 HP, 2.9s attack cooldown, 3-move cycle):
    - Attack 1: 1.0s active spinning stick hitbox around him (22 damage).
    - Attack 2: Spits 5 watermelon seeds toward the enemy at medium speed (9 damage each).
    - Attack 3: Crazy Bounce Frenzy for 5.0s! Speeds up (2.3x), takes 30% less damage, and deals
                10 damage whenever he collides with an enemy.
    - Passive Food: Every 2.0s, 30% chance for food to spawn. Usagi eats for 0.8s (pausing CD)
                    to heal +15 HP; enemies touching it first heal +1 HP.
    """
    def __init__(self, x, y):
        super().__init__("USAGI", x, y, hp=250, color=USAGI_YELLOW, radius=31, speed=235.0)
        self.cd_max = 2.8
        self.cd_timer = 0.0
        self.attack_index = 0  # Cycles 0 (Spin) -> 1 (Seed Spit x5) -> 2 (Crazy Bounce 5s)

        self.food_roll_timer = 2.0
        self.target_food = None
        self.hit_targets = set()
        self.seeds_to_spit = 0
        self.seed_interval_timer = 0.0
        self.crazy_hit_cooldowns = {}
        self.afterimages = []

    def complete_eating(self, world):
        if self.target_food and self.target_food.alive:
            self.target_food.alive = False
        self.target_food = None
        self.hp = min(self.max_hp, self.hp + 20.0)
        SFX_WEED.play()
        world["popups"].append(
            FloatingPopup(self.x, self.y - 28, "+20", HP_GREEN, WHITE, 22)
        )
        for _ in range(14):
            world["particles"].append(Particle(self.x, self.y, USAGI_YELLOW, 160))

    def update(self, dt, enemies, world):
        if not self.alive or self.grabbed_by:
            return

        # Passive: 20% chance every 2.0s to spawn food on the map
        self.food_roll_timer -= dt
        if self.food_roll_timer <= 0:
            self.food_roll_timer += 2.0
            if random.random() < 0.30:
                fx = random.randint(ARENA_RECT.left + 48, ARENA_RECT.right - 48)
                fy = random.randint(ARENA_RECT.top + 48, ARENA_RECT.bottom - 48)
                world["foods"].append(UsagiFoodItem(fx, fy, self))

        self.afterimages = [(ax, ay, life - dt) for ax, ay, life in self.afterimages if life - dt > 0]

        if self.stun_timer > 0:
            self.stun_timer -= dt
            return

        living = [e for e in enemies if e.alive]
        nearest = (
            min(living, key=lambda e: math.hypot(e.x - self.x, e.y - self.y))
            if living
            else None
        )

        # EATING ANIMATION STATE (Stops movement AND pauses attack bar)
        if self.state == "EATING":
            self.dmg_taken_mult = 0.70  # 30% less damage while eating
            self.state_timer -= dt
            self.weapon_angle += 12.0 * dt
            if self.state_timer <= 0:
                self.complete_eating(world)
                self.state = "ROAM"
            return

        # ATTACK 1: 1.0s Active Spin Hitbox (22 Damage)
        if self.state == "SPIN":
            self.state_timer -= dt
            self.move_and_bounce(dt)
            self.weapon_angle += 26.0 * dt
            for e in living:
                if e not in self.hit_targets and math.hypot(self.x - e.x, self.y - e.y) <= self.radius + e.radius + 54:
                    self.hit_targets.add(e)
                    e.receive_damage(25.0, self, world)
            if self.state_timer <= 0:
                self.state = "ROAM"
                self.cd_timer = 0.0
            return

        # ATTACK 2: Spit 5 Watermelon Seeds (9 Damage each)
        if self.state == "SEED_SPIT":
            if nearest:
                self.weapon_angle = math.atan2(nearest.y - self.y, nearest.x - self.x)
            self.seed_interval_timer -= dt
            if self.seed_interval_timer <= 0 and self.seeds_to_spit > 0:
                self.seed_interval_timer = 0.09
                self.seeds_to_spit -= 1
                spread = random.uniform(-0.10, 0.10)
                SFX_SEED.play()
                world["projectiles"].append(
                    WatermelonSeedProjectile(self.x, self.y, self.weapon_angle + spread, self)
                )
                if self.seeds_to_spit <= 0:
                    self.state = "ROAM"
                    self.cd_timer = 0.0
            return

        # ATTACK 3: 5.0s CRAZY BOUNCE FRENZY (Speed up, 30% less dmg taken, 12 dmg on collision)
        if self.state == "CRAZY_BOUNCE":
            self.state_timer -= dt
            self.dmg_taken_mult = 0.70  # Takes 30% less damage
            self.afterimages.append((self.x, self.y, 0.16))
            self.move_and_bounce(dt, speed_override=750.0)
            self.weapon_angle += 20.0 * dt

            # Frenzy: gobble any food he touches instantly (no eating pause)
            for f_item in world["foods"]:
                if f_item.alive and f_item.claimed_by is None:
                    if math.hypot(self.x - f_item.x, self.y - f_item.y) <= self.radius + f_item.radius:
                        f_item.claimed_by = self
                        self.target_food = f_item
                        self.complete_eating(world)

            for e in list(self.crazy_hit_cooldowns.keys()):
                self.crazy_hit_cooldowns[e] -= dt
                if self.crazy_hit_cooldowns[e] <= 0:
                    del self.crazy_hit_cooldowns[e]

            for e in living:
                if e not in self.crazy_hit_cooldowns and not e.in_air:
                    if math.hypot(self.x - e.x, self.y - e.y) <= self.radius + e.radius + 6:
                        self.crazy_hit_cooldowns[e] = 0.25
                        e.receive_damage(12.0, self, world)

            if self.state_timer <= 0:
                self.state = "ROAM"
                self.dmg_taken_mult = 1.0
                self.cd_timer = 0.0
            return

        # ROAM STATE
        self.dmg_taken_mult = 1.0
        self.move_and_bounce(dt)

        for f_item in world["foods"]:
            if f_item.alive and f_item.claimed_by is None:
                if math.hypot(self.x - f_item.x, self.y - f_item.y) <= self.radius + f_item.radius:
                    f_item.claimed_by = self
                    self.target_food = f_item
                    self.state = "EATING"
                    self.state_timer = 0.80
                    self.dmg_taken_mult = 0.70
                    return

        if living:
            self.cd_timer += dt * self.cd_rate()
            if self.cd_timer >= self.cd_max:
                self.cd_timer = 0.0
                if self.attack_index == 0:
                    self.state = "SPIN"
                    self.state_timer = 1.0
                    self.hit_targets.clear()
                    SFX_SPIN.play()
                elif self.attack_index == 1:
                    self.state = "SEED_SPIT"
                    self.seeds_to_spit = 5
                    self.seed_interval_timer = 0.05
                else:
                    self.state = "CRAZY_BOUNCE"
                    self.state_timer = 5.0
                    self.crazy_hit_cooldowns.clear()
                    SFX_CRAZY.play()
                self.attack_index = (self.attack_index + 1) % 3

    def draw(self, surf, enemies):
        if not self.alive:
            return
        cx, cy = int(self.x), int(self.y)

        # Crazy Bounce speed afterimages
        for ax, ay, life in self.afterimages:
            r = max(4, int(self.radius * (life / 0.16)))
            pygame.draw.circle(surf, (250, 225, 120), (int(ax), int(ay)), r, 2)

        if self.state == "EATING":
            cy += int(math.sin(self.state_timer * 30.0) * 5)

        if self.state == "SPIN":
            pygame.draw.circle(surf, USAGI_YELLOW, (cx, cy), self.radius + 52, 4)
            draw_usagi_stick(surf, cx, cy, self.weapon_angle, 56, 1.3)
        elif self.state == "CRAZY_BOUNCE":
            pygame.draw.circle(surf, (255, 235, 95), (cx, cy), self.radius + 8, 3)
            draw_usagi_stick(surf, cx, cy, self.weapon_angle, 42, 1.1)
        else:
            draw_usagi_stick(surf, cx, cy, self.weapon_angle, 40, 1.0)

        draw_ball_avatar(surf, "USAGI", cx, cy, self.radius)
        if self.stun_timer > 0:
            draw_dashed_circle(surf, MEDUSA_PURPLE, (cx, cy), self.radius + 6, 3, 16)


# ==========================================

    def bounce_speed(self):
        return 540.0 if self.state == "CRAZY_BOUNCE" else self.base_speed


register_solo("USAGI", "Usagi", USAGI_YELLOW, UsagiFighter)
