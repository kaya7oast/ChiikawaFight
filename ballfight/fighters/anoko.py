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
from ..registry import register_image
from ..assets import ASSETS
from .base import BaseFighter


# ==========================================
# CHARACTER 5: ANOKO (300 HP, 3.0s CD, Lunge Claws / Pounce-Throw / Moving Tail 20 / Moving Medusa)
# ==========================================
class AnokoFighter(BaseFighter):
    """
    Anoko (320 HP, Bigger radius = 40, 2.9s attack cooldown):
    - Attack 1: Triple Claw Slash in front (0.2s CD between swipes, lunges forward slightly toward
                the target on each swipe, 22 damage each).
    - Attack 2: Pounces toward enemy, swings them around, and throws them into a wall (20 damage,
                dazed for 4s).
    - Attack 3: Giant Tail Swipe (0.5s startup, can move throughout, radius = 1/5th map): spins once
                (15 dmg), pauses 0.4s, spins again (15 dmg).
    - Passive Medusa Stare: Every 2 attacks, 2.0s after finishing the 2nd attack, Anoko channels
                a 1.2s cone-shaped Medusa stare while continuing to move. Anyone caught in the cone
                takes 10 damage and is stunned in place for 1.0s (with their attack bar frozen).
    """
    def __init__(self, x, y):
        super().__init__("ANOKO", x, y, hp=320, color=ANOKO_CREAM, radius=40, speed=195.0)
        self.cd_max = 2.9
        self.cd_timer = 0.0
        self.attack_index = 0
        self.attacks_done = 0

        self.medusa_delay_timer = -1.0
        self.cone_half_angle = 0.48
        self.cone_length = 260.0

        self.slashes_left = 0
        self.slash_timer = 0.0
        self.pounce_vx = 0.0
        self.pounce_vy = 0.0
        self.grabbed_victim = None
        self.thrown_victim = None
        self.throw_vx = 0.0
        self.throw_vy = 0.0
        self.hit_targets = set()
        self.tail_spin_radius = int(ARENA_SIZE / 5.0) + self.radius
        self.tail_spins_left = 0

    def _finish_main_attack(self):
        self.state = "ROAM"
        self.cd_timer = 0.0
        self.attacks_done += 1
        if self.attacks_done % 2 == 0:
            self.medusa_delay_timer = 2.0

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

        if self.thrown_victim:
            v = self.thrown_victim
            if not v.alive:
                v.grabbed_by = None
                self.thrown_victim = None
            else:
                v.x += self.throw_vx * dt
                v.y += self.throw_vy * dt
                if v.clamp_to_walls():
                    SFX_SLAM.play()
                    v.grabbed_by = None
                    v.receive_damage(20.0, self, world)
                    v.apply_daze(4.0)
                    world["popups"].append(FloatingPopup(v.x, v.y - 50, "DAZED", (245, 190, 60), WHITE, 16, 0.9))
                    self.thrown_victim = None

        # --- MEDUSA STARE STATE (1.2s startup while moving -> 5 dmg + 1.0s petrify stun) ---
        if self.state == "MEDUSA_STARTUP":
            self.state_timer -= dt
            self.move_and_bounce(dt)
            if nearest:
                self.weapon_angle = math.atan2(nearest.y - self.y, nearest.x - self.x)
            if self.state_timer <= 0:
                SFX_STARE.play()
                for e in living:
                    if e.in_air:
                        continue
                    dx, dy = e.x - self.x, e.y - self.y
                    dist = math.hypot(dx, dy)
                    if dist <= self.cone_length + e.radius:
                        ang_diff = abs((math.atan2(dy, dx) - self.weapon_angle + math.pi) % math.tau - math.pi)
                        if ang_diff <= self.cone_half_angle:
                            e.receive_damage(10.0, self, world)
                            e.apply_stun(1.0, world)
                self.state = "ROAM"
            return

        # --- ATTACK 1: TRIPLE CLAW SLASH (0.2s between swipes, lunges forward per swipe, 15 dmg) ---
        if self.state == "TRIPLE_CLAW":
            self.slash_timer -= dt
            if self.slash_timer <= 0 and self.slashes_left > 0:
                self.slash_timer = 0.20  # 0.2s CD between each swipe
                self.slashes_left -= 1
                if nearest:
                    self.weapon_angle = math.atan2(nearest.y - self.y, nearest.x - self.x)
                # Slight forward lunge toward target on each swipe
                lunge_step = 32.0
                self.x += math.cos(self.weapon_angle) * lunge_step
                self.y += math.sin(self.weapon_angle) * lunge_step
                self.clamp_to_walls()

                SFX_CLAW.play()
                world["effects"].append(ClawSlashEffect(self.x, self.y, self.weapon_angle))
                for e in living:
                    if e.in_air:
                        continue
                    dx, dy = e.x - self.x, e.y - self.y
                    dist = math.hypot(dx, dy)
                    ang_diff = abs((math.atan2(dy, dx) - self.weapon_angle + math.pi) % math.tau - math.pi)
                    if dist <= self.radius + e.radius + 72 and ang_diff <= 0.78:
                        e.receive_damage(22.0, self, world)
                if self.slashes_left <= 0:
                    self._finish_main_attack()
            return

        # --- ATTACK 2: POUNCE -> SWING ABOUT -> THROW INTO WALL (20 damage) ---
        if self.state == "POUNCE":
            self.state_timer -= dt
            self.x += self.pounce_vx * dt
            self.y += self.pounce_vy * dt
            self.clamp_to_walls()

            for e in living:
                if not e.in_air and math.hypot(self.x - e.x, self.y - e.y) <= self.radius + e.radius + 14:
                    self.grabbed_victim = e
                    e.grabbed_by = self
                    self.state = "SWING_THROW"
                    self.state_timer = 0.48
                    SFX_SPIN.play()
                    return

            if self.state_timer <= 0:
                self._finish_main_attack()
            return

        if self.state == "SWING_THROW":
            self.state_timer -= dt
            self.weapon_angle += 24.0 * dt
            if self.grabbed_victim and self.grabbed_victim.alive:
                hold_dist = self.radius + self.grabbed_victim.radius + 8
                self.grabbed_victim.x = self.x + math.cos(self.weapon_angle) * hold_dist
                self.grabbed_victim.y = self.y + math.sin(self.weapon_angle) * hold_dist
                self.grabbed_victim.clamp_to_walls()

            if self.state_timer <= 0:
                if self.grabbed_victim and self.grabbed_victim.alive:
                    self.thrown_victim = self.grabbed_victim
                    throw_speed = 920.0
                    self.throw_vx = math.cos(self.weapon_angle) * throw_speed
                    self.throw_vy = math.sin(self.weapon_angle) * throw_speed
                self.grabbed_victim = None
                self._finish_main_attack()
            return

        # --- ATTACK 3: TAIL SWIPE (0.5s moving startup -> moving spin for 20 damage) ---
        if self.state == "TAIL_STARTUP":
            self.state_timer -= dt
            self.move_and_bounce(dt)
            if self.state_timer <= 0:
                self.state = "TAIL_SPIN"
                self.state_timer = TAIL_SPIN_TIME
                self.tail_spins_left = 1  # one more spin after this one
                self.hit_targets.clear()
                SFX_SPIN.play()
                world["effects"].append(RingEffect(self.x, self.y, self.tail_spin_radius, ANOKO_CREAM))
            return

        if self.state == "TAIL_SPIN":
            self.state_timer -= dt
            self.move_and_bounce(dt)
            self.weapon_angle += (math.tau / TAIL_SPIN_TIME) * dt  # exactly one full turn
            for e in living:
                if e not in self.hit_targets and math.hypot(self.x - e.x, self.y - e.y) <= self.tail_spin_radius + e.radius:
                    self.hit_targets.add(e)
                    e.receive_damage(15.0, self, world)
            if self.state_timer <= 0:
                if self.tail_spins_left > 0:
                    self.tail_spins_left -= 1
                    self.state = "TAIL_PAUSE"
                    self.state_timer = 0.4
                else:
                    self._finish_main_attack()
            return

        if self.state == "TAIL_PAUSE":  # 0.4s breather between the two tail spins
            self.state_timer -= dt
            self.move_and_bounce(dt)
            if self.state_timer <= 0:
                self.state = "TAIL_SPIN"
                self.state_timer = TAIL_SPIN_TIME
                self.hit_targets.clear()
                SFX_SPIN.play()
                world["effects"].append(RingEffect(self.x, self.y, self.tail_spin_radius, ANOKO_CREAM))
            return

        # --- ROAM STATE ---
        self.move_and_bounce(dt)

        if self.medusa_delay_timer > 0:
            self.medusa_delay_timer -= dt
            if self.medusa_delay_timer <= 0 and nearest:
                self.medusa_delay_timer = -1.0
                self.state = "MEDUSA_STARTUP"
                self.state_timer = 1.20
                self.weapon_angle = math.atan2(nearest.y - self.y, nearest.x - self.x)
                SFX_WARN.play()
                return

        if living:
            self.cd_timer += dt * self.cd_rate()
            if self.cd_timer >= self.cd_max:
                self.cd_timer = 0.0
                if self.attack_index == 0:
                    self.state = "TRIPLE_CLAW"
                    self.slashes_left = 3
                    self.slash_timer = 0.0
                elif self.attack_index == 1:
                    self.state = "POUNCE"
                    self.state_timer = 0.42
                    ang = math.atan2(nearest.y - self.y, nearest.x - self.x) if nearest else self.weapon_angle
                    self.weapon_angle = ang
                    self.pounce_vx = math.cos(ang) * 720.0
                    self.pounce_vy = math.sin(ang) * 720.0
                    SFX_CHARGE.play()
                else:
                    self.state = "TAIL_STARTUP"
                    self.state_timer = 0.50  # 0.5s moving startup before tail swipe
                self.attack_index = (self.attack_index + 1) % 3

    def draw(self, surf, enemies):
        if not self.alive:
            return
        cx, cy = int(self.x), int(self.y)

        if self.state == "MEDUSA_STARTUP":
            cone_surf = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            pts = [(cx, cy)]
            steps = 16
            for i in range(steps + 1):
                a = self.weapon_angle - self.cone_half_angle + (2 * self.cone_half_angle * i / steps)
                pts.append((cx + math.cos(a) * self.cone_length, cy + math.sin(a) * self.cone_length))
            pygame.draw.polygon(cone_surf, (175, 95, 225, 95), pts)
            pygame.draw.polygon(cone_surf, (175, 95, 225, 220), pts, 3)
            surf.blit(cone_surf, (0, 0))

        if self.state in ("TAIL_STARTUP", "TAIL_PAUSE"):
            draw_dashed_circle(surf, ANOKO_CREAM, (cx, cy), self.tail_spin_radius, 2, 24)
            # tail winds up behind her, wiggling
            wind = self.weapon_angle + math.pi + math.sin(self.state_timer * 30) * 0.25
            draw_anoko_tail(surf, cx, cy, wind, self.tail_spin_radius * 0.75)
        elif self.state == "TAIL_SPIN":
            pygame.draw.circle(surf, ANOKO_CREAM, (cx, cy), self.tail_spin_radius, 5)
            draw_dashed_circle(surf, WHITE, (cx, cy), self.tail_spin_radius - 8, 2, 24)
            # motion-blur ghosts + the tail sweeping round
            for k, fade in ((0.5, 70), (0.25, 130)):
                draw_anoko_tail(surf, cx, cy, self.weapon_angle - k, self.tail_spin_radius, alpha=fade)
            draw_anoko_tail(surf, cx, cy, self.weapon_angle, self.tail_spin_radius)

        draw_ball_avatar(surf, "ANOKO", cx, cy, self.radius)
        if self.stun_timer > 0:
            draw_dashed_circle(surf, MEDUSA_PURPLE, (cx, cy), self.radius + 6, 3, 16)


TAIL_SPIN_TIME = 0.3  # seconds for one full tail spin
_TAIL_CACHE = {}


def draw_anoko_tail(surf, cx, cy, angle, length, alpha=255):
    """Tail image (assets/anoko_tail.png) pointing from Anoko's centre toward `angle`."""
    img = ASSETS.get("ANOKO_TAIL")
    tip_x, tip_y = cx + math.cos(angle) * length, cy + math.sin(angle) * length
    if not img:
        pygame.draw.line(surf, (80, 120, 80), (cx, cy), (tip_x, tip_y), 16)
        pygame.draw.line(surf, (120, 165, 110), (cx, cy), (tip_x, tip_y), 10)
        return
    key = (int(length), alpha)
    if key not in _TAIL_CACHE:
        w, h = img.get_size()
        s = length / h
        scaled = pygame.transform.smoothscale(img, (max(1, int(w * s)), max(1, int(length))))
        if alpha < 255:
            scaled = scaled.copy()
            scaled.fill((255, 255, 255, alpha), special_flags=pygame.BLEND_RGBA_MULT)
        _TAIL_CACHE[key] = scaled
    tail = _TAIL_CACHE[key]
    # image points "up" (tip at top); rotate so the tip faces `angle`
    rot = pygame.transform.rotate(tail, -math.degrees(angle) - 90)
    mid = (cx + math.cos(angle) * length * 0.5, cy + math.sin(angle) * length * 0.5)
    surf.blit(rot, rot.get_rect(center=(int(mid[0]), int(mid[1]))))


register_image("ANOKO_TAIL", "anoko_tail")
register_solo("ANOKO", "Anoko", ANOKO_CREAM, AnokoFighter)
