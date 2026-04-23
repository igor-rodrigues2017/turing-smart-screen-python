#!/usr/bin/env python3
"""
Generates the OmarchySync theme from the current Omarchy colors.toml + wallpaper.
Run this script whenever you change your Omarchy theme.

Usage:
    ./venv/bin/python3 generate_omarchy_theme.py
"""

import tomllib
import os
from PIL import Image, ImageDraw, ImageFont

OMARCHY_COLORS = os.path.expanduser("~/.config/omarchy/current/theme/colors.toml")
OMARCHY_BG     = os.path.expanduser("~/.config/omarchy/current/background")
THEME_DIR      = os.path.join(os.path.dirname(__file__), "res", "themes", "OmarchySync")
FONTS_DIR      = os.path.join(os.path.dirname(__file__), "res", "fonts")

W, H = 800, 480  # 5" landscape

# ── Layout ────────────────────────────────────────────────────────────────
HEADER_H = 44
COL_SEP  = 400

# Left column
CPU_TOP  = HEADER_H   # 44
CPU_BOT  = 254
MEM_TOP  = CPU_BOT + 1
MEM_BOT  = 355
DISK_TOP = MEM_BOT + 1
DISK_BOT = H

# Right column
NET_TOP  = HEADER_H
NET_BOT  = 282
GPU_TOP  = NET_BOT + 1
GPU_BOT  = H

PAD = 12


def hex_to_rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def blend(rgb: tuple, bg: tuple, alpha: float) -> tuple[int, int, int]:
    return tuple(int(c * alpha + b * (1 - alpha)) for c, b in zip(rgb, bg))


def load_wallpaper() -> Image.Image | None:
    try:
        path = os.path.realpath(OMARCHY_BG)
        img  = Image.open(path).convert("RGB")
        iw, ih = img.size
        scale  = max(W / iw, H / ih)
        nw, nh = int(iw * scale), int(ih * scale)
        img    = img.resize((nw, nh), Image.LANCZOS)
        x, y   = (nw - W) // 2, (nh - H) // 2
        return img.crop((x, y, x + W, y + H))
    except Exception as e:
        print(f"  [warn] could not load wallpaper: {e}")
        return None


def build_background(colors: dict) -> Image.Image:
    bg     = hex_to_rgb(colors["background"])
    fg     = hex_to_rgb(colors["foreground"])
    accent = hex_to_rgb(colors["accent"])
    sep    = blend(fg, bg, 0.25)

    wall = load_wallpaper()
    if wall:
        overlay = Image.new("RGB", (W, H), bg)
        # 73% overlay keeps wallpaper subtle but readable
        img = Image.blend(wall, overlay, 0.73)
    else:
        img = Image.new("RGB", (W, H), bg)

    draw = ImageDraw.Draw(img)

    # header bottom accent glow
    for i, a in [(0, 0.35), (1, 0.16), (2, 0.06)]:
        draw.line([(0, HEADER_H - i), (W, HEADER_H - i)], fill=blend(accent, bg, a))

    # column separator
    draw.line([(COL_SEP, HEADER_H), (COL_SEP, H)], fill=sep)

    # left horizontal separators
    draw.line([(0, CPU_BOT),  (COL_SEP, CPU_BOT)],  fill=sep)
    draw.line([(0, MEM_BOT),  (COL_SEP, MEM_BOT)],  fill=sep)

    # right horizontal separator
    draw.line([(COL_SEP, NET_BOT), (W, NET_BOT)], fill=sep)

    return img


def draw_baked_labels(draw, colors):
    bg     = hex_to_rgb(colors["background"])
    fg     = hex_to_rgb(colors["foreground"])
    green  = hex_to_rgb(colors["color2"])
    accent = hex_to_rgb(colors["accent"])
    dim    = blend(fg, bg, 0.55)

    try:
        font_bold = ImageFont.truetype(
            os.path.join(FONTS_DIR, "jetbrains-mono", "JetBrainsMono-Bold.ttf"), 17)
    except Exception:
        return

    rx = COL_SEP + PAD

    # section labels
    draw.text((PAD, CPU_TOP  + 5), "CPU",     fill=dim, font=font_bold)
    draw.text((PAD, MEM_TOP  + 5), "MEM",     fill=dim, font=font_bold)
    draw.text((PAD, MEM_TOP + 48), "SWP",     fill=dim, font=font_bold)
    draw.text((PAD, DISK_TOP + 5), "DISK",    fill=dim, font=font_bold)
    draw.text((rx,  NET_TOP  + 5), "NETWORK", fill=dim, font=font_bold)
    draw.text((rx,  GPU_TOP  + 5), "GPU",     fill=dim, font=font_bold)

    # ↑ / ↓ network arrows
    def arrow(x, y, up, color, size=11):
        if up:
            pts = [(x, y + size), (x + size // 2, y), (x + size, y + size)]
        else:
            pts = [(x, y), (x + size // 2, y + size), (x + size, y)]
        draw.line([pts[0], pts[1]], fill=color, width=2)
        draw.line([pts[1], pts[2]], fill=color, width=2)

    arrow(rx + 4, NET_TOP + 34,  True,  green)
    arrow(rx + 4, NET_TOP + 132, False, accent)


def write_theme_yaml(colors: dict, path: str):
    bg     = hex_to_rgb(colors["background"])
    fg     = hex_to_rgb(colors["foreground"])
    accent = hex_to_rgb(colors["accent"])
    red    = hex_to_rgb(colors["color1"])
    green  = hex_to_rgb(colors["color2"])
    yellow = hex_to_rgb(colors["color3"])
    cyan   = hex_to_rgb(colors["color6"])
    dim    = blend(fg, bg, 0.55)

    def c(rgb): return f"{rgb[0]}, {rgb[1]}, {rgb[2]}"

    FONT      = "jetbrains-mono/JetBrainsMono-Regular.ttf"
    FONT_BOLD = "jetbrains-mono/JetBrainsMono-Bold.ttf"
    BG        = "background.png"

    # CPU radial — radius shrunk to leave ~28px below circle for freq/temp text
    cpu_cx = COL_SEP // 2           # 200
    cpu_r  = 78
    cpu_cy = CPU_TOP + 25 + cpu_r   # top of circle at CPU_TOP+25, gives room for label above

    # MEM/DISK bars
    bar_w     = COL_SEP - PAD * 2   # 376
    bar_h     = 14
    mem_bar_y  = MEM_TOP + 26
    swap_bar_y = MEM_TOP + 68
    disk_bar_y = DISK_TOP + 26

    # NET (right column) — spaced for font-size 31
    rx         = COL_SEP + PAD      # 412
    net_up_y   = NET_TOP + 28       # 72
    net_dn_y   = NET_TOP + 126      # 170
    net_arr_up = NET_TOP + 34
    net_arr_dn = NET_TOP + 132

    # GPU (right column)
    gpu_bar_w = W - COL_SEP - PAD * 2   # 376
    gpu_bar_y = GPU_TOP + 26
    gpu_mem_y = GPU_TOP + 68

    yaml = f"""\
---
author: "OmarchySync (auto-generated)"

display:
  DISPLAY_SIZE: 5"
  DISPLAY_ORIENTATION: landscape
  DISPLAY_RGB_LED: {c(accent)}

static_images:
  BACKGROUND:
    PATH: background.png
    X: 0
    Y: 0
    WIDTH: {W}
    HEIGHT: {H}

STATS:
  DATE:
    INTERVAL: 1
    HOUR:
      TEXT:
        SHOW: True
        X: {PAD}
        Y: 4
        FONT: {FONT_BOLD}
        FONT_SIZE: 32
        FONT_COLOR: {c(fg)}
        BACKGROUND_IMAGE: {BG}
        WIDTH: 200
        ANCHOR: lt
    DAY:
      TEXT:
        SHOW: True
        X: 228
        Y: 11
        FONT: {FONT}
        FONT_SIZE: 22
        FONT_COLOR: {c(dim)}
        BACKGROUND_IMAGE: {BG}
        WIDTH: 360
        ANCHOR: lt

  CPU:
    PERCENTAGE:
      INTERVAL: 1
      RADIAL:
        SHOW: True
        X: {cpu_cx}
        Y: {cpu_cy}
        RADIUS: {cpu_r}
        WIDTH: 8
        MIN_VALUE: 0
        MAX_VALUE: 100
        ANGLE_START: -90
        ANGLE_END: 270
        ANGLE_STEPS: 1
        ANGLE_SEP: 0
        CLOCKWISE: True
        BAR_COLOR: {c(green)}
        SHOW_TEXT: True
        SHOW_UNIT: False
        FONT: {FONT_BOLD}
        FONT_SIZE: 43
        FONT_COLOR: {c(fg)}
        BACKGROUND_IMAGE: {BG}
    FREQUENCY:
      INTERVAL: 1
      TEXT:
        SHOW: True
        SHOW_UNIT: True
        X: {cpu_cx - 80}
        Y: {cpu_cy + cpu_r + 8}
        FONT: {FONT}
        FONT_SIZE: 17
        FONT_COLOR: {c(cyan)}
        BACKGROUND_IMAGE: {BG}
    TEMPERATURE:
      INTERVAL: 1
      TEXT:
        SHOW: True
        SHOW_UNIT: True
        X: {cpu_cx + 10}
        Y: {cpu_cy + cpu_r + 8}
        FONT: {FONT}
        FONT_SIZE: 17
        FONT_COLOR: {c(yellow)}
        BACKGROUND_IMAGE: {BG}

  MEMORY:
    INTERVAL: 5
    VIRTUAL:
      GRAPH:
        SHOW: True
        X: {PAD}
        Y: {mem_bar_y}
        WIDTH: {bar_w}
        HEIGHT: {bar_h}
        MIN_VALUE: 0
        MAX_VALUE: 100
        BAR_COLOR: {c(cyan)}
        BAR_OUTLINE: False
        BACKGROUND_IMAGE: {BG}
      USED:
        SHOW: True
        SHOW_UNIT: True
        X: {PAD + 46}
        Y: {MEM_TOP + 5}
        FONT: {FONT}
        FONT_SIZE: 17
        FONT_COLOR: {c(cyan)}
        BACKGROUND_IMAGE: {BG}
      FREE:
        SHOW: True
        SHOW_UNIT: True
        X: {PAD + 180}
        Y: {MEM_TOP + 5}
        FONT: {FONT}
        FONT_SIZE: 17
        FONT_COLOR: {c(dim)}
        BACKGROUND_IMAGE: {BG}
    SWAP:
      GRAPH:
        SHOW: True
        X: {PAD}
        Y: {swap_bar_y}
        WIDTH: {bar_w}
        HEIGHT: {bar_h}
        MIN_VALUE: 0
        MAX_VALUE: 100
        BAR_COLOR: {c(accent)}
        BAR_OUTLINE: False
        BACKGROUND_IMAGE: {BG}
      USED:
        SHOW: True
        SHOW_UNIT: True
        X: {PAD + 46}
        Y: {MEM_TOP + 48}
        FONT: {FONT}
        FONT_SIZE: 17
        FONT_COLOR: {c(accent)}
        BACKGROUND_IMAGE: {BG}

  DISK:
    INTERVAL: 30
    USED:
      GRAPH:
        SHOW: True
        X: {PAD}
        Y: {disk_bar_y}
        WIDTH: {bar_w}
        HEIGHT: {bar_h}
        MIN_VALUE: 0
        MAX_VALUE: 100
        BAR_COLOR: {c(red)}
        BAR_OUTLINE: False
        BACKGROUND_IMAGE: {BG}
      TEXT:
        SHOW: True
        SHOW_UNIT: True
        X: {PAD + 46}
        Y: {DISK_TOP + 5}
        FONT: {FONT}
        FONT_SIZE: 17
        FONT_COLOR: {c(red)}
        BACKGROUND_IMAGE: {BG}
    TOTAL:
      TEXT:
        SHOW: True
        SHOW_UNIT: True
        X: {PAD + 180}
        Y: {DISK_TOP + 5}
        FONT: {FONT}
        FONT_SIZE: 17
        FONT_COLOR: {c(dim)}
        BACKGROUND_IMAGE: {BG}
    FREE:
      TEXT:
        SHOW: True
        SHOW_UNIT: True
        X: {PAD + 295}
        Y: {DISK_TOP + 5}
        FONT: {FONT}
        FONT_SIZE: 17
        FONT_COLOR: {c(dim)}
        BACKGROUND_IMAGE: {BG}

  NET:
    INTERVAL: 1
    ETH:
      UPLOAD:
        TEXT:
          SHOW: True
          X: {rx + 22}
          Y: {net_up_y}
          FONT: {FONT_BOLD}
          FONT_SIZE: 31
          FONT_COLOR: {c(green)}
          BACKGROUND_IMAGE: {BG}
      UPLOADED:
        TEXT:
          SHOW: True
          X: {rx + 22}
          Y: {net_up_y + 40}
          FONT: {FONT}
          FONT_SIZE: 16
          FONT_COLOR: {c(dim)}
          BACKGROUND_IMAGE: {BG}
      DOWNLOAD:
        TEXT:
          SHOW: True
          X: {rx + 22}
          Y: {net_dn_y}
          FONT: {FONT_BOLD}
          FONT_SIZE: 31
          FONT_COLOR: {c(accent)}
          BACKGROUND_IMAGE: {BG}
      DOWNLOADED:
        TEXT:
          SHOW: True
          X: {rx + 22}
          Y: {net_dn_y + 40}
          FONT: {FONT}
          FONT_SIZE: 16
          FONT_COLOR: {c(dim)}
          BACKGROUND_IMAGE: {BG}

  GPU:
    INTERVAL: 1
    PERCENTAGE:
      GRAPH:
        SHOW: True
        X: {rx}
        Y: {gpu_bar_y}
        WIDTH: {gpu_bar_w}
        HEIGHT: {bar_h}
        MIN_VALUE: 0
        MAX_VALUE: 100
        BAR_COLOR: {c(yellow)}
        BAR_OUTLINE: False
        BACKGROUND_IMAGE: {BG}
      TEXT:
        SHOW: True
        SHOW_UNIT: True
        X: {rx + 46}
        Y: {GPU_TOP + 5}
        FONT: {FONT}
        FONT_SIZE: 17
        FONT_COLOR: {c(yellow)}
        BACKGROUND_IMAGE: {BG}
    TEMPERATURE:
      INTERVAL: 5
      TEXT:
        SHOW: True
        SHOW_UNIT: True
        X: {rx + 180}
        Y: {GPU_TOP + 5}
        FONT: {FONT}
        FONT_SIZE: 17
        FONT_COLOR: {c(dim)}
        BACKGROUND_IMAGE: {BG}
    MEMORY:
      INTERVAL: 5
      GRAPH:
        SHOW: True
        X: {rx}
        Y: {gpu_mem_y}
        WIDTH: {gpu_bar_w}
        HEIGHT: {bar_h}
        MIN_VALUE: 0
        MAX_VALUE: 100
        BAR_COLOR: {c(yellow)}
        BAR_OUTLINE: False
        BACKGROUND_IMAGE: {BG}
      TEXT:
        SHOW: True
        SHOW_UNIT: True
        X: {rx + 46}
        Y: {GPU_TOP + 48}
        FONT: {FONT}
        FONT_SIZE: 17
        FONT_COLOR: {c(dim)}
        BACKGROUND_IMAGE: {BG}
"""
    with open(path, "w") as f:
        f.write(yaml)


def main():
    with open(OMARCHY_COLORS, "rb") as f:
        colors = tomllib.load(f)

    os.makedirs(THEME_DIR, exist_ok=True)

    img  = build_background(colors)
    draw = ImageDraw.Draw(img)
    draw_baked_labels(draw, colors)

    bg_path = os.path.join(THEME_DIR, "background.png")
    img.save(bg_path)
    print(f"✓ background.png  ({W}x{H})")

    yaml_path = os.path.join(THEME_DIR, "theme.yaml")
    write_theme_yaml(colors, yaml_path)
    print(f"✓ theme.yaml")
    print(f"\nSet THEME: OmarchySync in config.yaml to activate.")


if __name__ == "__main__":
    main()
