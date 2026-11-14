"""
Character voice clips (sounds/ folder, .ogg or .wav).

play_voice("usagi_wula") plays a clip if it exists; missing clips are silently skipped, so
fighters can call it freely. Each speaker (the part before the first "_") has a short cooldown
so the same character doesn't talk over themselves. Turn everything off with VOICES_ON in config.
"""
import os
import random

import pygame

from .config import VOICES_ON, VOICE_VOLUME

SOUND_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "sounds")
_SOUNDS = {}
_last_spoke = {}


def init_voices():
    if not VOICES_ON or not pygame.mixer.get_init() or not os.path.isdir(SOUND_DIR):
        return
    try:
        pygame.mixer.set_num_channels(24)
    except Exception:
        pass
    for fname in os.listdir(SOUND_DIR):
        stem, ext = os.path.splitext(fname)
        if ext.lower() not in (".ogg", ".wav"):
            continue
        try:
            snd = pygame.mixer.Sound(os.path.join(SOUND_DIR, fname))
            snd.set_volume(VOICE_VOLUME)
            _SOUNDS[stem.lower()] = snd
        except Exception as e:
            print(f"[Voice Warning] {fname}: {e}")
    print(f"[Voices] loaded {len(_SOUNDS)} clips")


def play_voice(*names, cooldown=0.8):
    """Play one of the given clips at random (only ones that exist). Speaker cooldown in seconds."""
    have = [n for n in names if n in _SOUNDS]
    if not have:
        return
    name = random.choice(have)
    speaker = name.split("_")[0]
    now = pygame.time.get_ticks() / 1000.0
    if now - _last_spoke.get(speaker, -99) < cooldown:
        return
    _last_spoke[speaker] = now
    _SOUNDS[name].play()
