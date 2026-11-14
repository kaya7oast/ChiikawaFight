import math
import random

import pygame

from ..config import *
from ..audio import *
from ..effects import *
from ..world_objects import *
from ..drawing import *
from ..registry import register_sprite, register_roster
from .base import BaseFighter


# ==========================================
# CHARACTER 1: CHIIKAWA & HACHIWARE TAG TEAM
# ==========================================
class DuoMemberFighter(BaseFighter):
    def __init__(self, char_type, x, y, color):
        super().__init__(char_type, x, y, hp=125, color=color, radius=29, speed=225.0)
        self.bonus_dmg = 0
        self.avenge_applied = False
        self.target_weed = None
        self.charge_vx = 0.0
        self.charge_vy = 0.0
        self.charge_hit_done = False
        self.spin_hit_done = False
        self.trigger_partner_spin = False

    @property
    def charge_damage(self):
        return 10 + self.bonus_dmg

    @property
    def spin_damage(self):
        return 15 + self.bonus_dmg

    def complete_weeding(self):
        if self.target_weed and self.target_weed.alive:
            self.target_weed.alive = False
        self.target_weed = None
        self.bonus_dmg += 5
        self.hp = min(self.max_hp, self.hp + 10.0)
        SFX_WEED.play()

    def start_ready_stick(self, target):
        if not self.alive or self.stun_timer > 0 or self.grabbed_by:
            return
        if self.state == "WEEDING" and self.target_weed:
            self.complete_weeding()
        self.state = "READY"
        self.state_timer = 0.50
        if target:
            self.weapon_angle = math.atan2(target.y - self.y, target.x - self.x)

    def start_spin_attack(self):
        if not self.alive or self.stun_timer > 0 or self.grabbed_by:
            return
        if self.state == "WEEDING" and self.target_weed:
            self.complete_weeding()
        self.state = "SPIN"
        self.state_timer = 0.45
        self.spin_hit_done = False
        SFX_SPIN.play()

    def update(self, dt, enemies, world):
        if not self.alive or self.grabbed_by:
            return
        if self.stun_timer > 0:
            self.stun_timer -= dt
            return

        self.check_enemy_food_pickup(world)

        living_enemies = [e for e in enemies if e.alive]
        nearest = (
            min(living_enemies, key=lambda e: math.hypot(e.x - self.x, e.y - self.y))
            if living_enemies
            else None
        )

        if self.state == "WEEDING":
            self.state_timer -= dt
            self.weapon_angle += 10.0 * dt
            if self.state_timer <= 0:
                wx, wy = self.x, self.y
                self.complete_weeding()
                self.state = "ROAM"
                world["popups"].append(FloatingPopup(wx, wy - 28, "+10", HP_GREEN, WHITE, 22))
                for _ in range(12):
                    world["particles"].append(Particle(wx, wy, WEED_GREEN, 150))
            return

        if self.state == "READY":
            self.state_timer -= dt
            if nearest:
                self.weapon_angle = math.atan2(nearest.y - self.y, nearest.x - self.x)
            if self.state_timer <= 0:
                self.state = "CHARGE"
                self.state_timer = 0.38
                self.charge_hit_done = False
                ang = self.weapon_angle
                self.charge_vx = math.cos(ang) * 760.0
                self.charge_vy = math.sin(ang) * 760.0
                SFX_CHARGE.play()
            return

        if self.state == "CHARGE":
            self.state_timer -= dt
            self.x += self.charge_vx * dt
            self.y += self.charge_vy * dt
            self.clamp_to_walls()

            if not self.charge_hit_done and nearest:
                if math.hypot(self.x - nearest.x, self.y - nearest.y) <= self.radius + nearest.radius + 24:
                    self.charge_hit_done = True
                    nearest.receive_damage(self.charge_damage, self, world)
                    self.state_timer = 0.0

            if self.state_timer <= 0:
                self.start_spin_attack()
                self.trigger_partner_spin = True
            return

        if self.state == "SPIN":
            self.state_timer -= dt
            self.weapon_angle += 28.0 * dt
            if not self.spin_hit_done and nearest:
                if math.hypot(self.x - nearest.x, self.y - nearest.y) <= self.radius + nearest.radius + 54:
                    self.spin_hit_done = True
                    nearest.receive_damage(self.spin_damage, self, world)
            if self.state_timer <= 0:
                self.state = "ROAM"
            return

        self.move_and_bounce(dt)
        for w in world["weeds"]:
            if w.alive and w.claimed_by is None:
                if math.hypot(self.x - w.x, self.y - w.y) <= self.radius + w.radius:
                    w.claimed_by = self
                    self.target_weed = w
                    self.state = "WEEDING"
                    self.state_timer = 0.80
                    break

    def draw(self, surf, enemies):
        if not self.alive:
            return
        cx, cy = int(self.x), int(self.y)
        if self.state == "WEEDING":
            cy += int(math.sin(self.state_timer * 28.0) * 4)

        if self.state == "READY" and enemies:
            living = [e for e in enemies if e.alive]
            if living:
                target = min(living, key=lambda e: math.hypot(e.x - self.x, e.y - self.y))
                draw_dashed_arrow(surf, self.color, (self.x, self.y), (target.x, target.y), 3)

        if self.state == "SPIN":
            pygame.draw.circle(surf, self.color, (cx, cy), self.radius + 50, 4)
            draw_sasumata(surf, cx, cy, self.weapon_angle, self.color, 54, 1.3)
        elif self.state in ("READY", "CHARGE"):
            draw_sasumata(surf, cx, cy, self.weapon_angle, self.color, 48, 1.2)
        else:
            draw_sasumata(surf, cx, cy, self.weapon_angle, self.color, 34, 1.0)

        draw_ball_avatar(surf, self.type, cx, cy, self.radius)
        if self.stun_timer > 0:
            draw_dashed_circle(surf, MEDUSA_PURPLE, (cx, cy), self.radius + 6, 3, 16)


class ChiikawaHachiwareTeam:
    def __init__(self, side):
        self.side = side
        x_pos = ARENA_RECT.left + 115 if side == "LEFT" else ARENA_RECT.right - 115
        self.chiikawa = DuoMemberFighter("CHIIKAWA", x_pos, ARENA_RECT.top + 115, CHIIKAWA_PINK)
        self.hachiware = DuoMemberFighter("HACHIWARE", x_pos, ARENA_RECT.bottom - 115, HACHIWARE_BLUE)
        self.fighters = [self.chiikawa, self.hachiware]

        self.cd_max = 3.0
        self.cd_timer = 0.0
        self.next_turn = "HACHIWARE"
        self.weed_roll_timer = 1.0

    @property
    def cooldown_ratio(self):
        return min(1.0, self.cd_timer / self.cd_max)

    def update(self, dt, enemies, world):
        self.weed_roll_timer -= dt
        if self.weed_roll_timer <= 0:
            self.weed_roll_timer += 1.0
            if random.random() < 0.20:
                wx = random.randint(ARENA_RECT.left + 45, ARENA_RECT.right - 45)
                wy = random.randint(ARENA_RECT.top + 45, ARENA_RECT.bottom - 45)
                world["weeds"].append(WeedTuft(wx, wy))

        if not self.chiikawa.alive and self.hachiware.alive and not self.hachiware.avenge_applied:
            self.hachiware.avenge_applied = True
            self.hachiware.bonus_dmg += 10
        elif not self.hachiware.alive and self.chiikawa.alive and not self.chiikawa.avenge_applied:
            self.chiikawa.avenge_applied = True
            self.chiikawa.bonus_dmg += 10

        busy = any(f.alive and f.state in ("READY", "CHARGE", "SPIN") for f in self.fighters)
        can_progress_cd = any(f.alive and f.stun_timer <= 0 and not f.grabbed_by for f in self.fighters)
        if not busy and can_progress_cd and any(e.alive for e in enemies):
            self.cd_timer += dt * min(f.cd_rate() for f in self.fighters if f.alive)
            if self.cd_timer >= self.cd_max:
                self.cd_timer = 0.0
                if self.next_turn == "HACHIWARE":
                    attacker = self.hachiware if (self.hachiware.alive and self.hachiware.stun_timer <= 0) else self.chiikawa
                    self.next_turn = "CHIIKAWA"
                else:
                    attacker = self.chiikawa if (self.chiikawa.alive and self.chiikawa.stun_timer <= 0) else self.hachiware
                    self.next_turn = "HACHIWARE"

                living_enemies = [e for e in enemies if e.alive]
                if attacker.alive and attacker.stun_timer <= 0 and living_enemies:
                    target = min(living_enemies, key=lambda e: math.hypot(e.x - attacker.x, e.y - attacker.y))
                    attacker.start_ready_stick(target)

        for f in self.fighters:
            f.update(dt, enemies, world)

        if self.hachiware.trigger_partner_spin:
            self.hachiware.trigger_partner_spin = False
            if self.chiikawa.alive:
                self.chiikawa.start_spin_attack()
        if self.chiikawa.trigger_partner_spin:
            self.chiikawa.trigger_partner_spin = False
            if self.hachiware.alive:
                self.hachiware.start_spin_attack()


register_sprite("CHIIKAWA", CHIIKAWA_PINK, name="Chiikawa")
register_sprite("HACHIWARE", HACHIWARE_BLUE, name="Hachiware")
register_roster(
    "DUO",
    [("Chiikawa", CHIIKAWA_PINK), (" & ", (150, 155, 165)), ("Hachiware", HACHIWARE_BLUE)],
    ChiikawaHachiwareTeam,
    bar_colors=(CHIIKAWA_PINK, HACHIWARE_BLUE),
)
