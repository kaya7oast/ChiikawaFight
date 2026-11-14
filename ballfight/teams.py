"""Team wrappers + the build_team() factory used by the game loop."""
from .config import ARENA_RECT
from . import registry


class SingleBossTeam:
    """A team made of one fighter. Fighter class must expose cd_timer / cd_max."""

    def __init__(self, fighter_cls, side):
        self.side = side
        x_pos = ARENA_RECT.left + 115 if side == "LEFT" else ARENA_RECT.right - 115
        self.boss = fighter_cls(x_pos, ARENA_RECT.centery)
        self.fighters = [self.boss]

    @property
    def cooldown_ratio(self):
        return min(1.0, self.boss.cd_timer / self.boss.cd_max)

    def update(self, dt, enemies, world):
        self.boss.update(dt, enemies, world)


def register_solo(key, name, color, fighter_cls, image=None):
    """One-liner to register a single-ball character (sprite + roster entry)."""
    registry.register_sprite(key, color, image=image, name=name)
    registry.register_roster(key, [(name, color)], lambda side: SingleBossTeam(fighter_cls, side))


def build_team(key, side):
    info = registry.ROSTER[key]
    team = info["build"](side)
    team.info = info
    return team


class CompositeTeam:
    """Two (or more) roster teams fighting on the same side, for 2v2."""

    def __init__(self, subs):
        self.subs = subs
        parts = []
        for i, t in enumerate(subs):
            if i:
                parts.append((" + ", (150, 155, 165)))
            parts.extend(t.info["title_parts"])
        self.info = {
            "key": "+".join(t.info["key"] for t in subs),
            "title_parts": parts,
            "name": "".join(p for p, _ in parts),
            "bar_colors": (subs[0].info["bar_colors"][0], subs[-1].info["bar_colors"][0]),
            "portraits": [p for t in subs for p in t.info["portraits"]],
        }

    @property
    def fighters(self):
        return [f for t in self.subs for f in t.fighters]

    @property
    def cooldown_ratio(self):
        return sum(t.cooldown_ratio for t in self.subs) / len(self.subs)

    def update(self, dt, enemies, world):
        for t in self.subs:
            t.update(dt, enemies, world)


def build_side(keys, side):
    """keys = list of roster keys for one side (1 for 1v1, 2 for 2v2)."""
    teams = [build_team(k, side) for k in keys]
    if len(teams) == 1:
        return teams[0]
    # spread the teams out vertically so they don't spawn on top of each other
    n = len(teams)
    for i, t in enumerate(teams):
        off = (i - (n - 1) / 2) * ARENA_RECT.height / n
        for f in t.fighters:
            f.y += off
            f.clamp_to_walls()
    return CompositeTeam(teams)
