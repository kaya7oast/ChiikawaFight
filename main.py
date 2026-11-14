"""
Run on PC:      python main.py
Web / phone:    built automatically by GitHub Actions with pygbag (see README).
"""
import asyncio

import pygame  # noqa: F401  (pygbag scans main.py's imports to know it must load pygame)

from ballfight.game import main

asyncio.run(main())
