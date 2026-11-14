"""
Siren (team: 1 Siren + 2 small mermaids; the team loses when the Siren dies)
SIREN - 150 HP, 2.85s attack cooldown, 2-move cycle
- Attack 1 SING: slows down and sings for 1s, then 2 vines grow out of the walls. A vine whips
  any enemy that gets close (10 dmg), then withers. Vines can't be targeted.
- Attack 2 TAIL SLAM: shockwave across the whole arena (like Kurimanju's burp), damage
  depending on distance (20 -> 5), plus knockback.
- Passive FLOOD: every 15s the arena floods for 5s: enemy attack bars fill 10% slower, vines get
  +20% range and +5 dmg, and the Siren takes 10% less damage.
MERMAIDS - 40 HP each. Every 5s each mermaid rams an enemy for 9 dmg.
- If all mermaids die: the Siren heals 50 HP and gets +10 dmg on all her attacks.
"""
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

SIREN_TEAL = (60, 165, 200)
MERMAID_PINK = (240, 135, 170)
VINE_GREEN = (90, 165, 85)
FLOOD_EVERY = 15.0
FLOOD_DURATION = 5.0
RAM_EVERY = 5.0
ARENA_DIAG = math.hypot(ARENA_RECT.width, ARENA_RECT.height)


# ---------------------------------------------------------------- visuals
class TideWave:
    def __init__(self, x, y):
        self.x, self.y = x, y
        self.life = self.max_life = 0.6

    def update(self, dt):
        self.life -= dt

    def draw(self, surf):
        if self.life <= 0:
            return
        t = 1 - self.life / self.max_life
        for k, col in enumerate(((150, 215, 245), (60, 165, 200), (255, 255, 255))):
            r = int(30 + t * ARENA_DIAG * (1 - k * 0.12))
            pygame.draw.circle(surf, col, (int(self.x), int(self.y)), r, max(1, int(10 * (1 - t))))


class MusicNote:
    def __init__(self, x, y):
        self.x, self.y = x + random.uniform(-20, 20), y - 20
        self.vx, self.vy = random.uniform(-30, 30), random.uniform(-70, -40)
        self.life = self.max_life = 0.9
        self.col = random.choice([(60, 165, 200), (240, 135, 170), (150, 110, 210)])

    def update(self, dt):
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.life -= dt

    def draw(self, surf):
        if self.life <= 0:
            return
        x, y = int(self.x), int(self.y)
        pygame.draw.ellipse(surf, self.col, (x - 6, y - 3, 10, 8))
        pygame.draw.line(surf, self.col, (x + 3, y), (x + 3, y - 15), 2)
        pygame.draw.line(surf, self.col, (x + 3, y - 15), (x + 9, y - 11), 3)


class FloodOverlay:
    """Water over the whole arena while flooded (lives in world['floor'])."""
    def __init__(self, owner, duration):
        self.owner = owner
        self.life = duration
        self.t = 0.0
        self.alive = True

    def update(self, dt, enemies, world):
        self.life -= dt
        self.t += dt
        if self.life <= 0 or not self.owner.alive:
            self.alive = False

    def draw(self, surf):
        fade = min(1.0, self.t / 0.5, max(0.0, self.life) / 0.5)
        s = pygame.Surface(ARENA_RECT.size, pygame.SRCALPHA)
        s.fill((80, 170, 230, int(85 * fade)))
        for row in range(0, ARENA_RECT.height, 46):
            pts = [(x, row + 20 + math.sin(x * 0.04 + self.t * 3 + row) * 6) for x in range(0, ARENA_RECT.width + 20, 20)]
            pygame.draw.lines(s, (255, 255, 255, int(120 * fade)), False, pts, 2)
        surf.blit(s, ARENA_RECT.topleft)


# ---------------------------------------------------------------- minions
class Vine:
    """Grows from a wall, whips the first enemy that comes close, then withers.
    Not a fighter, so enemies never target it. Lives in world['hazards']."""

    def __init__(self, x, y, face_angle, siren):
        self.x, self.y = x, y
        self.face = face_angle
        self.owner = siren
        self.grow = 0.0
        self.whip_anim = 0.0
        self.whip_to = None
        self.t = random.uniform(0, 6)
        self.alive = True

    def update(self, dt, enemies, world):
        self.t += dt
        if not self.owner.alive:
            self.alive = False
            return
        self.grow = min(1.0, self.grow + dt * 2.5)
        if self.whip_anim > 0:
            self.whip_anim -= dt
            if self.whip_anim <= 0:
                self.alive = False  # one hit, then it's done
            return
        if self.grow < 1.0:
            return
        rng = self.owner.vine_range()
        for e in enemies:
            if e.alive and not e.in_air and e.core and math.hypot(e.x - self.x, e.y - self.y) <= rng + e.radius:
                e.receive_damage(self.owner.vine_damage(), self.owner, world)
                self.whip_anim = 0.22
                self.whip_to = (e.x, e.y)
                SFX_CLAW.play()
                for _ in range(8):
                    world["particles"].append(Particle(e.x, e.y, (120, 200, 100), 160))
                return

    def _curve(self, x0, y0, x1, y1, bend, n=10):
        dx, dy = x1 - x0, y1 - y0
        L = math.hypot(dx, dy) or 1
        px, py = -dy / L, dx / L
        return [(x0 + dx * u + px * math.sin(u * math.pi) * bend, y0 + dy * u + py * math.sin(u * math.pi) * bend)
                for u in [k / (n - 1) for k in range(n)]]

    def draw(self, surf):
        bx, by = self.x, self.y
        if self.whip_to:  # lashing out at the enemy
            pts = self._curve(bx, by, self.whip_to[0], self.whip_to[1], 26 * math.sin(self.whip_anim * 20))
            _draw_stem(surf, pts, 11, 4)
            for k, u in enumerate((0.35, 0.6, 0.85)):
                i = int(u * (len(pts) - 1))
                a = math.atan2(pts[i + 1][1] - pts[i][1], pts[i + 1][0] - pts[i][0]) + (1.0 if k % 2 else -1.0)
                _draw_leaf(surf, pts[i][0], pts[i][1], a, 14)
            tx, ty = self.whip_to
            for k in range(3):  # impact swoosh
                pygame.draw.arc(surf, WHITE, (tx - 22 - k * 5, ty - 22 - k * 5, 44 + k * 10, 44 + k * 10),
                                self.t * 8 + k, self.t * 8 + k + 2.2, 3)
            return

        # dirt clump where it pokes out of the wall
        pygame.draw.ellipse(surf, (150, 110, 80), (bx - 13, by - 8, 26, 16))
        pygame.draw.ellipse(surf, (95, 65, 45), (bx - 13, by - 8, 26, 16), 2)
        L = 62 * self.grow  # vine length
        sway = math.sin(self.t * 3) * 0.35
        ang = self.face + sway
        tip = (bx + math.cos(ang) * L, by + math.sin(ang) * L)
        pts = self._curve(bx, by, tip[0], tip[1], 9 * math.sin(self.t * 2.3))
        _draw_stem(surf, pts, 11, 4)
        if self.grow > 0.5:  # two leaves on alternate sides
            for k, u in enumerate((0.3, 0.55, 0.8)):
                i = int(u * (len(pts) - 1))
                a = math.atan2(pts[i + 1][1] - pts[i][1], pts[i + 1][0] - pts[i][0]) + (1.1 if k % 2 else -1.1)
                _draw_leaf(surf, pts[i][0], pts[i][1], a, 13 * self.grow)
        # pink bud on the tip (opens when fully grown)
        r = 4 + int(3 * self.grow)
        for k in range(5 if self.grow >= 1 else 0):
            pa = self.t * 0.8 + k * math.tau / 5
            pygame.draw.circle(surf, (255, 170, 200), (int(tip[0] + math.cos(pa) * r), int(tip[1] + math.sin(pa) * r)), r)
        pygame.draw.circle(surf, (250, 215, 110) if self.grow >= 1 else (255, 150, 185), (int(tip[0]), int(tip[1])), r)


def _draw_stem(surf, pts, w0, w1):
    """Tapered vine: thick at the base, thin at the tip, dark outline + light highlight."""
    n = len(pts) - 1
    for i in range(n):
        w = int(w0 + (w1 - w0) * i / n)
        a, b = (int(pts[i][0]), int(pts[i][1])), (int(pts[i + 1][0]), int(pts[i + 1][1]))
        pygame.draw.line(surf, (35, 80, 40), a, b, w + 4)
        pygame.draw.circle(surf, (35, 80, 40), a, (w + 4) // 2)
    for i in range(n):
        w = int(w0 + (w1 - w0) * i / n)
        a, b = (int(pts[i][0]), int(pts[i][1])), (int(pts[i + 1][0]), int(pts[i + 1][1]))
        pygame.draw.line(surf, VINE_GREEN, a, b, w)
        pygame.draw.circle(surf, VINE_GREEN, a, w // 2)
        pygame.draw.line(surf, (150, 215, 130), a, b, max(1, w // 4))


def _draw_leaf(surf, x, y, ang, size):
    if size < 3:
        return
    side1, side2 = [], []
    for k in range(9):
        u = k / 8
        w = math.sin(u * math.pi) * size * 0.42
        px, py = x + math.cos(ang) * size * u, y + math.sin(ang) * size * u
        side1.append((px + math.cos(ang + 1.57) * w, py + math.sin(ang + 1.57) * w))
        side2.append((px - math.cos(ang + 1.57) * w, py - math.sin(ang + 1.57) * w))
    poly = side1 + side2[::-1]
    pygame.draw.polygon(surf, (120, 200, 100), poly)
    pygame.draw.polygon(surf, (35, 80, 40), poly, 2)
    pygame.draw.line(surf, (60, 120, 55), (x, y), (x + math.cos(ang) * size * 0.9, y + math.sin(ang) * size * 0.9), 1)


class MermaidMinion(BaseFighter):
    core = False
    COLLIDE_STATES = {"ROAM"}

    def __init__(self, x, y):
        super().__init__("MERMAID", x, y, hp=40, color=MERMAID_PINK, radius=17, speed=215.0)
        self.target = None
        self.hit_done = False

    def start_ram(self, target):
        if self.alive and self.stun_timer <= 0 and not self.grabbed_by:
            self.target = target
            self.state, self.state_timer = "RAM", 0.7
            self.hit_done = False

    def update(self, dt, enemies, world):
        if not self.alive or self.grabbed_by:
            return
        if self.stun_timer > 0:
            self.stun_timer -= dt
            return
        if self.state == "RAM":
            self.state_timer -= dt
            t = self.target
            if t and t.alive:
                ang = math.atan2(t.y - self.y, t.x - self.x)
                self.weapon_angle = ang
                self.x += math.cos(ang) * 640 * dt
                self.y += math.sin(ang) * 640 * dt
                self.clamp_to_walls()
                if not t.in_air and math.hypot(t.x - self.x, t.y - self.y) <= self.radius + t.radius + 4:
                    t.receive_damage(9.0, self, world)
                    world["effects"].append(RingEffect(t.x, t.y, t.radius + 12, MERMAID_PINK))
                    self.state_timer = 0
            if self.state_timer <= 0:
                self.state = "ROAM"
                self.vx, self.vy = -math.cos(self.weapon_angle) * self.base_speed, -math.sin(self.weapon_angle) * self.base_speed
            return
        self.move_and_bounce(dt)

    def draw(self, surf, enemies):
        if not self.alive:
            return
        cx, cy = int(self.x), int(self.y)
        if self.state == "RAM":  # speed streaks behind her (drawn underneath the picture)
            for k in range(1, 4):
                bx = cx - math.cos(self.weapon_angle) * 10 * k
                by = cy - math.sin(self.weapon_angle) * 10 * k
                pygame.draw.circle(surf, (255, 200, 220), (int(bx), int(by)), max(3, self.radius - 4 * k), 2)
        draw_ball_avatar(surf, self.type, cx, cy, self.radius)
        if self.stun_timer > 0:
            draw_dashed_circle(surf, MEDUSA_PURPLE, (cx, cy), self.radius + 5, 2, 12)


# ---------------------------------------------------------------- the Siren
class SirenFighter(BaseFighter):
    COLLIDE_STATES = {"ROAM", "SING"}

    def __init__(self, x, y):
        super().__init__("SIREN", x, y, hp=150, color=SIREN_TEAL, radius=34, speed=190.0)
        self.cd_max = 2.85
        self.cd_timer = 0.0
        self.attack_index = 0
        self.bonus = 0.0          # +10 once all mermaids are gone
        self.flooding = False
        self.team = None
        self.note_timer = 0.0

    def vine_range(self):
        return 70.0 * (1.2 if self.flooding else 1.0)

    def vine_damage(self):
        return 10.0 + (5.0 if self.flooding else 0.0) + self.bonus

    def receive_damage(self, amount, attacker, world):
        if self.flooding:
            self.dmg_taken_mult = 0.9
        hit = super().receive_damage(amount, attacker, world)
        self.dmg_taken_mult = 1.0
        return hit

    def grow_vines(self, world):
        for _ in range(2):
            side = random.randrange(4)
            inset = 14
            if side == 0:
                x, y, face = random.uniform(ARENA_RECT.left + 40, ARENA_RECT.right - 40), ARENA_RECT.top + inset, math.pi / 2
            elif side == 1:
                x, y, face = random.uniform(ARENA_RECT.left + 40, ARENA_RECT.right - 40), ARENA_RECT.bottom - inset, -math.pi / 2
            elif side == 2:
                x, y, face = ARENA_RECT.left + inset, random.uniform(ARENA_RECT.top + 40, ARENA_RECT.bottom - 40), 0.0
            else:
                x, y, face = ARENA_RECT.right - inset, random.uniform(ARENA_RECT.top + 40, ARENA_RECT.bottom - 40), math.pi
            world["hazards"].append(Vine(x, y, face, self))
            for _ in range(6):
                world["particles"].append(Particle(x, y, VINE_GREEN, 90))
        SFX_WEED.play()

    def tail_slam(self, living, world):
        SFX_SLAM.play()
        world["effects"].append(TideWave(self.x, self.y))
        world["shake"] = max(world.get("shake", 0), 8)
        for e in living:
            d = math.hypot(e.x - self.x, e.y - self.y)
            close = max(0.0, min(1.0, 1.0 - d / (ARENA_DIAG * 0.85)))
            e.receive_damage(5 + 15 * close + self.bonus, self, world)
            if d > 0:
                push = 200 + 600 * close
                e.apply_knockback((e.x - self.x) / d * push, (e.y - self.y) / d * push, self)

    def update(self, dt, enemies, world):
        if not self.alive or self.grabbed_by:
            return
        if self.stun_timer > 0:
            self.stun_timer -= dt
            return
        self.check_enemy_food_pickup(world)
        living = [e for e in enemies if e.alive]

        if self.state == "SING":
            self.state_timer -= dt
            self.move_and_bounce(dt, speed_override=self.base_speed * 0.3)
            self.note_timer -= dt
            if self.note_timer <= 0:
                self.note_timer = 0.12
                world["effects"].append(MusicNote(self.x, self.y))
            if self.state_timer <= 0:
                self.state = "ROAM"
                self.grow_vines(world)
            return

        if self.state == "TAIL_WINDUP":
            self.state_timer -= dt
            if self.state_timer <= 0:
                self.state = "ROAM"
                self.tail_slam(living, world)
            return

        self.move_and_bounce(dt)
        if living:
            self.cd_timer += dt * self.cd_rate()
            if self.cd_timer >= self.cd_max:
                self.cd_timer = 0.0
                if self.attack_index == 0:
                    self.state, self.state_timer = "SING", 1.0
                    SFX_JUMP.play()
                else:
                    self.state, self.state_timer = "TAIL_WINDUP", 0.35
                self.attack_index = (self.attack_index + 1) % 2

    def draw(self, surf, enemies):
        if not self.alive:
            return
        cx, cy = int(self.x), int(self.y)
        if self.state == "SING":
            for k in range(3):
                r = self.radius + 10 + k * 12 + int((pygame.time.get_ticks() * 0.05) % 12)
                pygame.draw.circle(surf, (150, 215, 245), (cx, cy), r, 2)
        vis_r = int(self.radius * 1.35)  # her picture is bigger than her hitbox
        if self.bonus:  # enraged glow, behind the picture
            pygame.draw.circle(surf, (255, 170, 160), (cx, cy), vis_r + 4)
            pygame.draw.circle(surf, (235, 80, 70), (cx, cy), vis_r + 4, 3)
        if self.state == "TAIL_WINDUP":
            draw_dashed_circle(surf, SIREN_TEAL, (cx, cy), vis_r + 8, 3, 18)
        draw_ball_avatar(surf, self.type, cx, cy, self.radius)
        if self.stun_timer > 0:
            draw_dashed_circle(surf, MEDUSA_PURPLE, (cx, cy), self.radius + 6, 3, 16)


class SirenTeam:
    def __init__(self, side):
        self.side = side
        x = ARENA_RECT.left + 115 if side == "LEFT" else ARENA_RECT.right - 115
        cy = ARENA_RECT.centery
        self.siren = SirenFighter(x, cy)
        self.siren.team = self
        self.mermaids = [MermaidMinion(x + dx, cy + dy) for dx, dy in ((0, -95), (0, 95))]
        self.fighters = [self.siren] + self.mermaids
        self.ram_timer = RAM_EVERY
        self.flood_timer = FLOOD_EVERY
        self.flood_left = 0.0
        self.mermaid_bonus_given = False

    @property
    def cooldown_ratio(self):
        return min(1.0, self.siren.cd_timer / self.siren.cd_max)

    def update(self, dt, enemies, world):
        s = self.siren
        if not s.alive:
            for f in self.fighters:  # everyone goes down with the Siren
                f.hp = 0.0
            return
        living = [e for e in enemies if e.alive]
        core_enemies = [e for e in living if e.core] or living

        # flood
        if self.flood_left > 0:
            self.flood_left -= dt
            for e in enemies:
                e.cd_slow_timer = 0.1
            if self.flood_left <= 0:
                s.flooding = False
        else:
            self.flood_timer -= dt
            if self.flood_timer <= 0:
                self.flood_timer = FLOOD_EVERY
                self.flood_left = FLOOD_DURATION
                s.flooding = True
                world["floor"].append(FloodOverlay(s, FLOOD_DURATION))
                world["popups"].append(FloatingPopup(ARENA_RECT.centerx, ARENA_RECT.top + 40, "FLOOD!", SIREN_TEAL, WHITE, 26, 1.4))
                SFX_DEKATSUYO.play()

        # mermaid rams every 5s
        self.ram_timer -= dt
        if self.ram_timer <= 0:
            self.ram_timer = RAM_EVERY
            for m in self.mermaids:
                if m.alive and core_enemies:
                    m.start_ram(min(core_enemies, key=lambda e: math.hypot(e.x - m.x, e.y - m.y)))

        # all mermaids gone -> heal + damage boost (once)
        if not self.mermaid_bonus_given and not any(m.alive for m in self.mermaids):
            self.mermaid_bonus_given = True
            s.bonus = 10.0
            s.type = "SIREN_ENRAGED"  # swap to the angry picture
            s.hp = min(s.max_hp, s.hp + 50.0)
            world["popups"].append(FloatingPopup(s.x, s.y - 50, "+50  ENRAGED!", (235, 80, 70), WHITE, 20, 1.4))
            world["effects"].append(RingEffect(s.x, s.y, s.radius + 30, (235, 80, 70)))

        for f in self.fighters:
            f.update(dt, enemies, world)


register_sprite("SIREN", SIREN_TEAL, image="siren", name="Siren")
register_sprite("SIREN_ENRAGED", (220, 70, 80), image="siren_enraged", name="Siren")
register_sprite("MERMAID", MERMAID_PINK, image="mermaid", name="Mermaid")
register_roster("SIREN", [("Siren", SIREN_TEAL)], SirenTeam, bar_colors=(SIREN_TEAL, MERMAID_PINK), portraits=["SIREN", "MERMAID"])
