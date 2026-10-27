"""Orientation layouts: sim once in world coords, render per orientation.

The arena (circle) is the world; each layout says how big the canvas is and
where the arena sits on it. Scenes must take positions from the layout, never
hardcode pixels, so the same simulation renders to 9:16 and 16:9.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class Layout:
    tag: str          # file suffix: 9x16 | 16x9
    w: int
    h: int
    arena_cx: float
    arena_cy: float
    arena_R: float    # arena inner radius in canvas pixels
    # text anchors — 9:16 uses the empty bands above/below the arena;
    # 16:9's arena spans almost the full height, so text lives in the
    # empty side panels instead
    cap_x: float = 0.0
    cap_y: float = 0.0
    cap_maxw: float = 0.0
    cnt_x: float = 0.0
    cnt_y: float = 0.0
    cnt_maxw: float = 0.0
    wm_size: float = 31.0   # watermark font size (px)
    tease: bool = True      # switch caption to the tease ("Just wait...")?


def get_layout(orient: str) -> Layout:
    if orient in ("vertical", "9x16"):
        w, h = 1080, 1920
        # cnt_y sits in the band between the arena bottom (~0.71h) and
        # YouTube Shorts' bottom title/description overlay: at 0.87h the
        # counter overlapped the Shorts title (Luka, 2026-07-08), so keep it
        # up here — the Shorts UI eats roughly the bottom ~18-20% of a vertical
        # frame. Don't push it back down.
        return Layout("9x16", w, h, w / 2, h * 0.48, w * 0.415,
                      cap_x=w / 2, cap_y=h * 0.14, cap_maxw=w * 0.92,
                      cnt_x=w / 2, cnt_y=h * 0.78, cnt_maxw=w * 0.92,
                      wm_size=31.0, tease=True)
    if orient in ("horizontal", "16x9"):
        w, h = 1920, 1080
        cx, R = w / 2, h * 0.415
        side = (w / 2 - R) / 2          # center of each empty side panel
        # bigger watermark for big-screen viewing; keep the rule caption the
        # whole time (no "Just wait..." switch) — Luka 2026-07-04
        return Layout("16x9", w, h, cx, h * 0.52, R,
                      cap_x=side, cap_y=h * 0.42, cap_maxw=side * 1.8,
                      cnt_x=w - side, cnt_y=h * 0.58, cnt_maxw=side * 1.8,
                      wm_size=46.0, tease=False)
    raise ValueError(f"unknown orientation {orient!r}")
