#!/usr/bin/env python3
"""
Generates the OmarchySync theme from the current Omarchy colors.toml + wallpaper.
Run this script whenever you change your Omarchy theme.

Usage:
    ./venv/bin/python3 generate_omarchy_theme.py
"""

import tomllib
import os
import re
import subprocess
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
CPU_BOT  = 275        # expanded to fit 20px model name + radial + freq/temp
MEM_TOP  = CPU_BOT + 1
MEM_BOT  = 376
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


def get_cpu_model() -> str:
    try:
        for line in open("/proc/cpuinfo").read().splitlines():
            if "model name" in line:
                name = line.split(":", 1)[1].strip()
                name = re.sub(r"\([RTM]+\)", "", name)
                name = re.sub(r"\s+CPU\s+@\s+[\d.]+GHz", "", name)
                name = re.sub(r"\s+\d+-Core Processor", "", name)
                return re.sub(r"\s+", " ", name).strip()
    except Exception:
        pass
    return "Unknown CPU"


def get_gpu_model() -> str:
    try:
        out = subprocess.check_output(
            ["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"],
            text=True, stderr=subprocess.DEVNULL).strip().splitlines()[0]
        return out.replace("NVIDIA ", "")
    except Exception:
        pass
    try:
        for line in subprocess.check_output(["lspci"], text=True).splitlines():
            if "VGA" in line or "3D" in line:
                part = line.split(":", 2)[-1].strip()
                part = re.sub(r"\(rev [0-9a-f]+\)", "", part).strip()
                return part[:40]
    except Exception:
        pass
    return "Unknown GPU"


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
        img = Image.blend(wall, overlay, 0.73)
    else:
        img = Image.new("RGB", (W, H), bg)

    draw = ImageDraw.Draw(img)

    for i, a in [(0, 0.35), (1, 0.16), (2, 0.06)]:
        draw.line([(0, HEADER_H - i), (W, HEADER_H - i)], fill=blend(accent, bg, a))

    draw.line([(COL_SEP, HEADER_H), (COL_SEP, H)],    fill=sep)
    draw.line([(0, CPU_BOT),  (COL_SEP, CPU_BOT)],    fill=sep)
    draw.line([(0, MEM_BOT),  (COL_SEP, MEM_BOT)],    fill=sep)
    draw.line([(COL_SEP, NET_BOT), (W, NET_BOT)],     fill=sep)

    return img


def draw_baked_labels(draw, colors, cpu_model: str, gpu_model: str):
    bg     = hex_to_rgb(colors["background"])
    fg     = hex_to_rgb(colors["foreground"])
    green  = hex_to_rgb(colors["color2"])
    accent = hex_to_rgb(colors["accent"])
    dim    = blend(fg, bg, 0.55)
    dim2   = blend(fg, bg, 0.40)

    try:
        font_bold = ImageFont.truetype(
            os.path.join(FONTS_DIR, "jetbrains-mono", "JetBrainsMono-Bold.ttf"), 20)
        font_model = ImageFont.truetype(
            os.path.join(FONTS_DIR, "jetbrains-mono", "JetBrainsMono-Regular.ttf"), 20)
    except Exception:
        return

    rx = COL_SEP + PAD

    # section labels
    draw.text((PAD, CPU_TOP  + 5), "CPU",     fill=dim,  font=font_bold)
    draw.text((PAD, MEM_TOP  + 5), "MEM",     fill=dim,  font=font_bold)
    draw.text((PAD, MEM_TOP + 56), "SWP",     fill=dim,  font=font_bold)
    draw.text((PAD, DISK_TOP + 5), "DISK",    fill=dim,  font=font_bold)
    draw.text((rx,  NET_TOP  + 5), "NETWORK", fill=dim,  font=font_bold)
    draw.text((rx,  GPU_TOP  + 5), "GPU",     fill=dim,  font=font_bold)

    # hardware model names (baked so they don't get overwritten by stats)
    draw.text((PAD, CPU_TOP + 30), cpu_model, fill=dim2, font=font_model)
    draw.text((rx,  GPU_TOP + 30), gpu_model, fill=dim2, font=font_model)

    # ↑ / ↓ network arrows
    def arrow(x, y, up, color, size=12):
        pts = ([(x, y+size), (x+size//2, y), (x+size, y+size)] if up
               else [(x, y), (x+size//2, y+size), (x+size, y)])
        draw.line([pts[0], pts[1]], fill=color, width=2)
        draw.line([pts[1], pts[2]], fill=color, width=2)

    arrow(rx + 4, NET_TOP + 38,  True,  green)
    arrow(rx + 4, NET_TOP + 148, False, accent)


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

    # CPU radial — model name at CPU_TOP+30 (20px, ~24px tall, ends ~54)
    # radial top starts at CPU_TOP+60, giving 6px gap after model text
    cpu_cx = COL_SEP // 2
    cpu_r  = 68
    cpu_cy = CPU_TOP + 60 + cpu_r   # 44+60+68 = 172; bottom=240; freq/temp at 248

    # MEM/DISK bars
    bar_w      = COL_SEP - PAD * 2   # 376
    bar_h      = 14
    mem_bar_y  = MEM_TOP + 30
    swap_bar_y = MEM_TOP + 76
    disk_bar_y = DISK_TOP + 30

    # NET — spaced for font-size 37
    rx         = COL_SEP + PAD       # 412
    net_up_y   = NET_TOP + 32        # 76
    net_dn_y   = NET_TOP + 140       # 184

    # GPU — model name at GPU_TOP+30 (20px, ends ~54); bars pushed below
    gpu_bar_w  = W - COL_SEP - PAD * 2   # 376
    gpu_bar_y  = GPU_TOP + 60
    gpu_mem_y  = GPU_TOP + 104

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
        Y: 10
        FONT: {FONT}
        FONT_SIZE: 26
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
        FONT_SIZE: 52
        FONT_COLOR: {c(fg)}
        BACKGROUND_IMAGE: {BG}
    FREQUENCY:
      INTERVAL: 1
      TEXT:
        SHOW: True
        SHOW_UNIT: True
        X: {cpu_cx - 84}
        Y: {cpu_cy + cpu_r + 8}
        FONT: {FONT}
        FONT_SIZE: 20
        FONT_COLOR: {c(cyan)}
        BACKGROUND_IMAGE: {BG}
    TEMPERATURE:
      INTERVAL: 1
      TEXT:
        SHOW: True
        SHOW_UNIT: True
        X: {cpu_cx + 12}
        Y: {cpu_cy + cpu_r + 8}
        FONT: {FONT}
        FONT_SIZE: 20
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
        X: {PAD + 50}
        Y: {MEM_TOP + 5}
        FONT: {FONT}
        FONT_SIZE: 20
        FONT_COLOR: {c(cyan)}
        BACKGROUND_IMAGE: {BG}
      FREE:
        SHOW: True
        SHOW_UNIT: True
        X: {PAD + 195}
        Y: {MEM_TOP + 5}
        FONT: {FONT}
        FONT_SIZE: 20
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
        X: {PAD + 50}
        Y: {MEM_TOP + 56}
        FONT: {FONT}
        FONT_SIZE: 20
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
        X: {PAD + 50}
        Y: {DISK_TOP + 5}
        FONT: {FONT}
        FONT_SIZE: 20
        FONT_COLOR: {c(red)}
        BACKGROUND_IMAGE: {BG}
    TOTAL:
      TEXT:
        SHOW: True
        SHOW_UNIT: True
        X: {PAD + 195}
        Y: {DISK_TOP + 5}
        FONT: {FONT}
        FONT_SIZE: 20
        FONT_COLOR: {c(dim)}
        BACKGROUND_IMAGE: {BG}
    FREE:
      TEXT:
        SHOW: True
        SHOW_UNIT: True
        X: {PAD + 310}
        Y: {DISK_TOP + 5}
        FONT: {FONT}
        FONT_SIZE: 20
        FONT_COLOR: {c(dim)}
        BACKGROUND_IMAGE: {BG}

  NET:
    INTERVAL: 1
    ETH:
      UPLOAD:
        TEXT:
          SHOW: True
          X: {rx + 24}
          Y: {net_up_y}
          FONT: {FONT_BOLD}
          FONT_SIZE: 37
          FONT_COLOR: {c(green)}
          BACKGROUND_IMAGE: {BG}
      UPLOADED:
        TEXT:
          SHOW: True
          X: {rx + 24}
          Y: {net_up_y + 46}
          FONT: {FONT}
          FONT_SIZE: 19
          FONT_COLOR: {c(dim)}
          BACKGROUND_IMAGE: {BG}
      DOWNLOAD:
        TEXT:
          SHOW: True
          X: {rx + 24}
          Y: {net_dn_y}
          FONT: {FONT_BOLD}
          FONT_SIZE: 37
          FONT_COLOR: {c(accent)}
          BACKGROUND_IMAGE: {BG}
      DOWNLOADED:
        TEXT:
          SHOW: True
          X: {rx + 24}
          Y: {net_dn_y + 46}
          FONT: {FONT}
          FONT_SIZE: 19
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
        X: {rx + 50}
        Y: {GPU_TOP + 5}
        FONT: {FONT}
        FONT_SIZE: 20
        FONT_COLOR: {c(yellow)}
        BACKGROUND_IMAGE: {BG}
    TEMPERATURE:
      INTERVAL: 1
      TEXT:
        SHOW: True
        SHOW_UNIT: True
        X: {rx + 195}
        Y: {GPU_TOP + 5}
        FONT: {FONT}
        FONT_SIZE: 20
        FONT_COLOR: {c(dim)}
        BACKGROUND_IMAGE: {BG}
    MEMORY:
      INTERVAL: 1
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
        X: {rx + 50}
        Y: {GPU_TOP + 60}
        FONT: {FONT}
        FONT_SIZE: 20
        FONT_COLOR: {c(dim)}
        BACKGROUND_IMAGE: {BG}
"""
    with open(path, "w") as f:
        f.write(yaml)


def main():
    with open(OMARCHY_COLORS, "rb") as f:
        colors = tomllib.load(f)

    cpu_model = get_cpu_model()
    gpu_model = get_gpu_model()
    print(f"  CPU: {cpu_model}")
    print(f"  GPU: {gpu_model}")

    os.makedirs(THEME_DIR, exist_ok=True)

    img  = build_background(colors)
    draw = ImageDraw.Draw(img)
    draw_baked_labels(draw, colors, cpu_model, gpu_model)

    bg_path = os.path.join(THEME_DIR, "background.png")
    img.save(bg_path)
    print(f"✓ background.png  ({W}x{H})")

    yaml_path = os.path.join(THEME_DIR, "theme.yaml")
    write_theme_yaml(colors, yaml_path)
    print(f"✓ theme.yaml")
    print(f"\nSet THEME: OmarchySync in config.yaml to activate.")


if __name__ == "__main__":
    main()
