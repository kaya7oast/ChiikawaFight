"""
Chiikabu (two forms)
FORM 1 - small beetle: 50 HP, 2.5s attack cooldown. When it "dies" it transforms into form 2.
- Attack 1 HORN CHARGE: slows down, vibrates, then rushes the enemy: 10 dmg + heavy knockback.
  Being slammed into a wall hurts a little and dazes them (attack bar 50% slower for 3s).
- Attack 2 LATCH ON: pounces and sticks to the enemy for 2s: 5 dmg every 0.5s and their attack
  bar fills 30% slower. While latched it takes 30% less damage and reflects 20% of the damage it
  takes back at the attacker. Taking more than 30 dmg while latched throws it off: stunned 2s.
FORM 2 - big muscle form: 150 HP, 2.9s attack cooldown.
- Attack 1 DIVE: flies up for 1s (untouchable, drifts toward the enemy) and crashes down, 30 dmg.
- Attack 2 PUNCH: a stronger horn charge, 25 dmg on hit (same knockback / wall daze).
- Passive LAST STAND: the first hit that would kill it leaves it on 1 HP instead.
- Passive SHRINK BACK (once): if the big form survives 25s it turns back into small Chiikabu
  (fresh 50 HP) and the whole cycle restarts - but the second big form stays big for good.
ALWAYS - naturally takes 5% less damage from everything.
"""
import math
import random

import pygame

from ..config import *
from ..audio import *
from ..effects import *
from ..world_objects import *
from ..drawing import *
from ..registry import register_sprite
from ..fonts import get_font
from ..teams import register_solo
from .base import BaseFighter

CHIIKABU_BROWN = (150, 100, 62)
CHIIKABU_BIG_BROWN = (120, 72, 40)
BASE_DR = 0.95        # naturally takes 5% less damage
BIG_FORM_TIME = 25.0  # big form shrinks back after this long (only once)
_reflecting = False  # guard so reflected damage never reflects again


class ChiikabuFighter(BaseFighter):
    COLLIDE_STATES = {"ROAM"}

    def __init__(self, x, y):
        super().__init__("CHIIKABU", x, y, hp=50, color=CHIIKABU_BROWN, radius=26, speed=240.0)
        self.form = 1
        self.cd_max = 2.5
        self.cd_timer = 0.0
        self.attack_index = 0
        self.target = None
        self.rush_angle = 0.0
        self.charge_damage = 10.0
        self.attached_to = None
        self.attach_timer = 0.0
        self.attach_tick = 0.0
        self.attach_taken = 0.0
        self.last_stand_used = False
        self.air_timer = 0.0
        self.air_duration = 1.0
        self.slam_radius = 105
        self.transform_anim = 0.0
        self.dmg_taken_mult = BASE_DR
        self.big_timer = 0.0
        self.reverted = False

    @property
    def draw_layer(self):
        return 1 if (self.in_air or self.state == "ATTACHED") else 0

    # ---------------- damage / forms ----------------
    def receive_damage(self, amount, attacker, world):
        global _reflecting
        if not self.alive or self.in_air:
            return False
        attached = self.state == "ATTACHED"
        hp_before = self.hp
        self.dmg_taken_mult = BASE_DR * (0.70 if attached else 1.0)
        hit = super().receive_damage(amount, attacker, world)
        self.dmg_taken_mult = BASE_DR
        taken = hp_before - self.hp

        if attached and taken > 0:
            # reflect 20% of what got through
            if attacker is not None and attacker is not self and attacker.alive and not _reflecting:
                _reflecting = True
                try:
                    attacker.receive_damage(taken * 0.2, self, world)
                finally:
                    _reflecting = False
            self.attach_taken += taken

        if self.hp <= 0:
            if self.form == 1:
                self.transform(world)
                return hit
            if not self.last_stand_used:
                self.last_stand_used = True
                self.hp = 1.0
                world["popups"].append(FloatingPopup(self.x, self.y - 50, "1 HP!", (235, 80, 70), WHITE, 20, 1.2))
                world["effects"].append(RingEffect(self.x, self.y, self.radius + 20, (235, 80, 70)))
                return hit

        if attached and self.alive and self.attach_taken > 30:
            self.detach(world, thrown=True)
        return hit

    def transform(self, world):
        self.detach(world)
        self.form = 2
        self.type = "CHIIKABU_BIG"
        self.color = CHIIKABU_BIG_BROWN
        self.max_hp = self.hp = 150.0
        self._ui_trail = 150.0
        self.radius = 36
        self.base_speed = 195.0
        self.cd_max = 2.9
        self.cd_timer = 0.0
        self.attack_index = 0
        self.charge_damage = 25.0
        self.state = "ROAM"
        self.stun_timer = 0.0
        self.dmg_taken_mult = BASE_DR
        self.big_timer = BIG_FORM_TIME
        self.clamp_to_walls()
        self.transform_anim = 0.8
        SFX_SLAM.play()
        world["shake"] = max(world.get("shake", 0), 10)
        world["effects"].append(RingEffect(self.x, self.y, 90, CHIIKABU_BIG_BROWN))
        world["popups"].append(FloatingPopup(self.x, self.y - 60, "TRANSFORM!", CHIIKABU_BIG_BROWN, WHITE, 22, 1.4))
        for _ in range(26):
            world["particles"].append(Particle(self.x, self.y, CHIIKABU_BROWN, 240))

    def shrink_back(self, world):
        """Big form survived 25s -> back to small Chiikabu with fresh HP (only ever once)."""
        self.reverted = True
        self.form = 1
        self.type = "CHIIKABU"
        self.color = CHIIKABU_BROWN
        self.max_hp = self.hp = 50.0
        self._ui_trail = 50.0
        self.radius = 26
        self.base_speed = 240.0
        self.cd_max = 2.5
        self.cd_timer = 0.0
        self.attack_index = 0
        self.charge_damage = 10.0
        self.last_stand_used = False
        self.transform_anim = 0.8
        SFX_WEED.play()
        world["effects"].append(RingEffect(self.x, self.y, 70, CHIIKABU_BROWN))
        world["popups"].append(FloatingPopup(self.x, self.y - 50, "SHRUNK BACK!", CHIIKABU_BROWN, WHITE, 20, 1.3))
        for _ in range(18):
            world["particles"].append(Particle(self.x, self.y, (240, 220, 200), 180))

    def detach(self, world, thrown=False):
        v = self.attached_to
        if v is not None and v.attached_by is self:
            v.attached_by = None
        self.attached_to = None
        if self.state == "ATTACHED":
            self.state = "ROAM"
        self.dmg_taken_mult = BASE_DR
        if v is not None:
            ang = random.uniform(0, math.tau)
            self.x = v.x + math.cos(ang) * (v.radius + self.radius + 6)
            self.y = v.y + math.sin(ang) * (v.radius + self.radius + 6)
            self.vx, self.vy = math.cos(ang) * self.base_speed, math.sin(ang) * self.base_speed
            self.clamp_to_walls()
        if thrown:
            self.stun_timer = max(self.stun_timer, 2.0)
            SFX_COUNTER.play()
            world["popups"].append(FloatingPopup(self.x, self.y - 44, "THROWN OFF!", WHITE, (60, 40, 30), 16, 1.0))

    # ---------------- behaviour ----------------
    def _nearest(self, living):
        return min(living, key=lambda e: math.hypot(e.x - self.x, e.y - self.y)) if living else None

    def update(self, dt, enemies, world):
        if not self.alive or self.grabbed_by:
            return
        self.transform_anim = max(0.0, self.transform_anim - dt)
        living = [e for e in enemies if e.alive]
        if self.form == 2 and not self.reverted:
            self.big_timer -= dt
            if self.big_timer <= 0 and self.state == "ROAM" and not self.in_air:
                self.shrink_back(world)
                return

        # --- latched onto someone ---
        if self.state == "ATTACHED":
            v = self.attached_to
            if v is None or not v.alive or v.in_air:
                self.detach(world)
                return
            self.x, self.y = v.x, v.y - v.radius * 0.55
            self.attach_timer -= dt
            self.attach_tick -= dt
            if self.attach_tick <= 0:
                self.attach_tick += 0.5
                v.receive_damage(5.0, self, world)
            if self.attach_timer <= 0:
                self.detach(world)
            return

        # --- form 2 dive (in the air) ---
        if self.in_air:
            self.air_timer -= dt
            tgt = self._nearest(living)
            if tgt:
                dx, dy = tgt.x - self.x, tgt.y - self.y
                d = math.hypot(dx, dy)
                if d > 4:
                    self.x += dx / d * 170 * dt
                    self.y += dy / d * 170 * dt
            self.clamp_to_walls()
            if self.air_timer <= 0:
                self.in_air = False
                SFX_SLAM.play()
                world["shake"] = max(world.get("shake", 0), 8)
                world["effects"].append(RingEffect(self.x, self.y, self.slam_radius, CHIIKABU_BIG_BROWN))
                for _ in range(20):
                    world["particles"].append(Particle(self.x, self.y, CHIIKABU_BROWN, 220))
                for e in living:
                    if math.hypot(e.x - self.x, e.y - self.y) <= self.slam_radius + e.radius:
                        e.receive_damage(30.0, self, world)
            return

        if self.stun_timer > 0:
            self.stun_timer -= dt
            return
        self.check_enemy_food_pickup(world)
        nearest = self._nearest(living)
        tgt = self.target if (self.target and self.target.alive) else nearest

        # --- horn charge: slow down -> vibrate -> rush ---
        if self.state == "CHARGE_SLOW":
            self.state_timer -= dt
            self.move_and_bounce(dt, speed_override=self.base_speed * 0.3)
            if self.state_timer <= 0:
                self.state, self.state_timer = "CHARGE_VIBRATE", 0.35
                SFX_CHARGE.play()
            return
        if self.state == "CHARGE_VIBRATE":
            self.state_timer -= dt
            if tgt:
                self.rush_angle = math.atan2(tgt.y - self.y, tgt.x - self.x)
            if self.state_timer <= 0:
                self.state, self.state_timer = "CHARGE_RUSH", 0.55
            return
        if self.state == "CHARGE_RUSH":
            self.state_timer -= dt
            self.x += math.cos(self.rush_angle) * 820 * dt
            self.y += math.sin(self.rush_angle) * 820 * dt
            hit_wall = self.clamp_to_walls()
            for e in living:
                if not e.in_air and math.hypot(e.x - self.x, e.y - self.y) <= self.radius + e.radius + 6:
                    e.receive_damage(self.charge_damage, self, world)
                    e.apply_knockback(math.cos(self.rush_angle) * 1150, math.sin(self.rush_angle) * 1150,
                                      self, wall_damage=True, wall_daze=3.0)
                    world["effects"].append(RingEffect(e.x, e.y, e.radius + 18, self.color))
                    self.state_timer = 0
                    break
            if self.state_timer <= 0 or hit_wall:
                self.state = "ROAM"
                self.vx, self.vy = -math.cos(self.rush_angle) * self.base_speed, -math.sin(self.rush_angle) * self.base_speed
            return

        # --- form 1 pounce -> latch on ---
        if self.state == "POUNCE":
            self.state_timer -= dt
            if tgt:
                ang = math.atan2(tgt.y - self.y, tgt.x - self.x)
                self.x += math.cos(ang) * 650 * dt
                self.y += math.sin(ang) * 650 * dt
                self.clamp_to_walls()
                if (not tgt.in_air and tgt.attached_by is None and
                        math.hypot(tgt.x - self.x, tgt.y - self.y) <= self.radius + tgt.radius + 4):
                    self.state = "ATTACHED"
                    self.attached_to = tgt
                    tgt.attached_by = self
                    self.attach_timer, self.attach_tick, self.attach_taken = 2.0, 0.5, 0.0
                    SFX_CLAW.play()
                    world["popups"].append(FloatingPopup(tgt.x, tgt.y - 54, "LATCHED!", self.color, WHITE, 16, 0.9))
                    return
            if self.state_timer <= 0:
                self.state = "ROAM"
            return

        # --- roam + attack bar ---
        self.move_and_bounce(dt)
        if living:
            self.cd_timer += dt * self.cd_rate()
            if self.cd_timer >= self.cd_max:
                self.cd_timer = 0.0
                self.target = nearest
                if self.form == 1:
                    if self.attack_index == 0:
                        self.state, self.state_timer = "CHARGE_SLOW", 0.35
                    else:
                        self.state, self.state_timer = "POUNCE", 0.7
                        SFX_JUMP.play()
                else:
                    if self.attack_index == 0:
                        self.in_air = True
                        self.air_timer = self.air_duration
                        SFX_JUMP.play()
                    else:
                        self.state, self.state_timer = "CHARGE_SLOW", 0.3
                self.attack_index = (self.attack_index + 1) % 2

    def draw(self, surf, enemies):
        if not self.alive:
            return
        cx, cy = int(self.x), int(self.y)
        if self.transform_anim > 0:
            r = int(self.radius + 30 * self.transform_anim)
            pygame.draw.circle(surf, (255, 230, 150), (cx, cy), r, 4)

        if self.in_air:
            draw_dashed_circle(surf, self.color, (cx, cy), self.slam_radius, 2, 28)
            pygame.draw.ellipse(surf, (160, 150, 150), (cx - 26, cy - 10, 52, 20))
            p = 1.0 - self.air_timer / self.air_duration
            arc = math.sin(p * math.pi)
            draw_ball_avatar(surf, self.type, cx, cy - int(arc * 85), int(self.radius * (1 + 0.3 * arc)))
            return

        if self.state in ("CHARGE_SLOW", "CHARGE_VIBRATE") and self.target and self.target.alive:
            draw_dashed_arrow(surf, self.color, (self.x, self.y), (self.target.x, self.target.y), 3)
        if self.state == "CHARGE_VIBRATE":
            cx += random.randint(-3, 3)
            cy += random.randint(-3, 3)
        if self.state == "CHARGE_RUSH":
            for k in range(1, 4):  # speed streaks
                bx = cx - math.cos(self.rush_angle) * 14 * k
                by = cy - math.sin(self.rush_angle) * 14 * k
                pygame.draw.circle(surf, (230, 210, 190), (int(bx), int(by)), max(3, self.radius - 6 * k), 2)

        r = int(self.radius * 0.8) if self.state == "ATTACHED" else self.radius
        draw_ball_avatar(surf, self.type, cx, cy, r)
        if self.form == 2 and not self.reverted and 0 < self.big_timer <= 5.0:
            t = get_font(11).render(f"shrinks in {self.big_timer:.1f}s", True, WHITE)
            rr = t.get_rect(center=(cx, cy + self.radius + 14)).inflate(8, 2)
            pygame.draw.rect(surf, CHIIKABU_BROWN, rr, border_radius=6)
            surf.blit(t, t.get_rect(center=rr.center))
        if self.state == "ATTACHED":
            draw_dashed_circle(surf, (235, 80, 70), (cx, cy), r + 6, 2, 14)
        if self.stun_timer > 0:
            draw_dashed_circle(surf, MEDUSA_PURPLE, (cx, cy), self.radius + 6, 3, 16)


register_solo("CHIIKABU", "Chiikabu", CHIIKABU_BROWN, ChiikabuFighter, image="chiikabu")
register_sprite("CHIIKABU_BIG", CHIIKABU_BIG_BROWN, image="chiikabu_big", name="Chiikabu")
