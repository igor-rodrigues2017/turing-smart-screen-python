# ![Icon](https://raw.githubusercontent.com/mathoudebine/turing-smart-screen-python/main/res/icons/monitor-icon-17865/24.png) turing-smart-screen-python

> [!WARNING]
> 
> This project is **not affiliated, associated, authorized, endorsed by, or in any way officially connected with Turing / XuanFang / Kipye brands**, or any of theirs subsidiaries, affiliates, manufacturers or sellers of their products. All product and company names are the registered trademarks of their original owners.
> 
> This project is an open-source alternative software, NOT the original software provided for the smart screens. **Please do not open issues for USBMonitor.exe/ExtendScreen.exe or for the smart screens hardware here**.
> * for Turing Smart Screen, use the official forum here: http://discuz.turzx.com/
> * for other smart screens, contact your reseller

---

## 🖥️ Personal fork — OmarchySync (Turing 5" Rev C on Omarchy/Arch Linux)

This fork adds the **OmarchySync** theme: a system monitor that reads the colors and wallpaper from the active [Omarchy](https://github.com/basecamp/omarchy) theme and automatically generates a matching layout for the Turing 5" screen.

> Hardware: **Turing Smart Screen 5" Rev C** (`/dev/ttyACM0`, VID=`0x2bc5`, PID=`0x529`)

---

### Files changed in this fork

| File | What changed |
|---|---|
| `config.yaml` | `THEME: OmarchySync`, `REVISION: C`, `ETH: enp7s0`, `COM_PORT: AUTO` |
| `library/lcd/lcd_comm_rev_c.py` | `ScreenOff()` uses `SetBrightness(0)` instead of `TURNOFF` |
| `library/lcd/lcd_comm.py` | `rtscts=False`, `write_timeout=5` |
| `library/display.py` | lazy-reset strategy (tries HELLO before triggering a hardware reset) |
| `generate_omarchy_theme.py` | script that generates the theme (new file) |
| `res/themes/OmarchySync/` | generated theme directory (new) |

---

### Prerequisites

```bash
# Clone the fork
git clone https://github.com/igor-rodrigues2017/turing-smart-screen-python.git
cd turing-smart-screen-python

# Create the venv and install dependencies
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install Pillow  # required for theme generation
```

---

### Initial setup

#### 1. `config.yaml` — adjust for your hardware

```yaml
config:
  COM_PORT: AUTO          # AUTO detects /dev/ttyACM0 or ttyACM1 automatically
  THEME: OmarchySync

  # Network interface (use `ip link` to find yours)
  ETH: enp7s0             # ← change to your Ethernet interface
  WLO: ''                 # ← or fill with your Wi-Fi interface (e.g. wlan0)

display:
  REVISION: C             # Turing 5" Rev C
  BRIGHTNESS: 62
  RESET_ON_STARTUP: true
```

#### 2. Generate the theme for the first time

The script reads `~/.config/omarchy/current/theme/colors.toml` and the active wallpaper symlink (`~/.config/omarchy/current/background`), then writes `background.png` + `theme.yaml` into `res/themes/OmarchySync/`.

```bash
./venv/bin/python3 generate_omarchy_theme.py
```

The generated layout is a btop-inspired 800×480 landscape design:

```
┌─────────────────────────────────────────────────────┐
│  HH:MM:SS          Day  DD/Mon/YYYY                  │  header
├──────────────────────────┬──────────────────────────┤
│  CPU                     │  NETWORK                 │
│    [radial gauge]        │    ↑  upload speed       │
│    freq      temp        │    ↓  download speed     │
├──────────────────────────┤──────────────────────────┤
│  MEM  [bar] used / free  │  GPU                     │
│  SWP  [bar] used         │    [bar] % / temp        │
├──────────────────────────┤    [bar] VRAM            │
│  DISK [bar] used / total │                          │
└──────────────────────────┴──────────────────────────┘
```

Colors and wallpaper update automatically with each Omarchy theme change.

---

### Systemd service (auto-start with graphical session)

Create `~/.config/systemd/user/turing-smart-screen.service`:

```ini
[Unit]
Description=Turing Smart Screen
After=graphical-session.target

[Service]
Type=simple
WorkingDirectory=/home/YOUR_USER/Projects/turing-smart-screen-python
Environment=PYSTRAY_BACKEND=gtk
ExecStartPre=/bin/sleep 10
ExecStart=/home/YOUR_USER/Projects/turing-smart-screen-python/venv/bin/python main.py
Restart=on-failure
RestartSec=10

[Install]
WantedBy=graphical-session.target
```

```bash
systemctl --user daemon-reload
systemctl --user enable --now turing-smart-screen.service
```

> The `sleep 10` gives the USB display time to enumerate after login.

---

### Manual sync alias

Add to `~/.bashrc`:

```bash
alias turing-sync='cd ~/Projects/turing-smart-screen-python && ./venv/bin/python3 generate_omarchy_theme.py && systemctl --user restart turing-smart-screen.service && echo "Turing screen updated!"'
```

```bash
source ~/.bashrc
# usage:
turing-sync
```

---

### Automatic Omarchy hook (syncs on theme change)

Create `~/.config/omarchy/hooks/theme-set` and make it executable:

```bash
mkdir -p ~/.config/omarchy/hooks
cat > ~/.config/omarchy/hooks/theme-set << 'EOF'
#!/bin/bash
TURING_DIR="$HOME/Projects/turing-smart-screen-python"
"$TURING_DIR/venv/bin/python3" "$TURING_DIR/generate_omarchy_theme.py" \
  && systemctl --user restart turing-smart-screen.service \
  && notify-send -u low "Turing Screen" "Theme updated to $1"
EOF
chmod +x ~/.config/omarchy/hooks/theme-set
```

From now on, every `omarchy-theme-set <name>` call will automatically regenerate and reload the screen theme.

---

### Fix: display unresponsive after service restart

**Symptom:** after `systemctl --user restart`, the screen goes dark and the service crashes with `OSError: Display did not return a valid ID after 10 retries`.

**Cause:** the `TURNOFF` command puts the Rev C display into a non-responsive state. On the next startup, the HELLO handshake fails because the display firmware is offline.

**Fix applied** in `library/lcd/lcd_comm_rev_c.py`:

```python
# Before (broken):
def ScreenOff(self):
    self._send_command(Command.STOP_VIDEO)
    self._send_command(Command.STOP_MEDIA, readsize=1024)
    self._send_command(Command.TURNOFF)  # puts display in unresponsive state

# After (fixed):
def ScreenOff(self):
    self._send_command(Command.STOP_VIDEO)
    self._send_command(Command.STOP_MEDIA, readsize=1024)
    self.SetBrightness(0)  # turns off backlight, display stays responsive
```

If the display gets stuck anyway (e.g. after a hard kill), unplug and replug the USB cable, then:

```bash
systemctl --user start turing-smart-screen.service
```

---

### Fix: freq/temp text overwritten by the CPU radial gauge

**Cause:** `CPU.PERCENTAGE.RADIAL` has `INTERVAL: 1` and repaints its bounding box (via `BACKGROUND_IMAGE`) every second, erasing the `FREQUENCY` and `TEMPERATURE` text elements that only refresh every 5 seconds.

**Fix applied** in `generate_omarchy_theme.py`:
- Radial radius reduced to `cpu_r = 78` so the circle does not reach the text area
- Text positioned at `Y = cpu_cy + cpu_r + 8` — below the bottom edge of the circle
- `FREQUENCY` and `TEMPERATURE` set to `INTERVAL: 1` so they always redraw right after the radial

---

![Linux](https://img.shields.io/badge/Linux-FCC624?style=for-the-badge&logo=linux&logoColor=black) ![Windows](https://img.shields.io/badge/Windows%2010%2F11-0078D6?style=for-the-badge&logoColor=white&logo=data:image/svg%2bxml;base64,PHN2ZyByb2xlPSJpbWciIHZpZXdCb3g9IjAgMCAyNCAyNCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48dGl0bGU+V2luZG93czwvdGl0bGU+PHBhdGggZmlsbCA9ICIjRkZGRkZGIiBkPSJNMCwwSDExLjM3N1YxMS4zNzJIMFpNMTIuNjIzLDBIMjRWMTEuMzcySDEyLjYyM1pNMCwxMi42MjNIMTEuMzc3VjI0SDBabTEyLjYyMywwSDI0VjI0SDEyLjYyMyIvPjwvc3ZnPg==) [![macOS](https://img.shields.io/badge/mac%20os%20(⚠️major%20bug)-000000?style=for-the-badge&logo=apple&logoColor=white)](https://github.com/mathoudebine/turing-smart-screen-python/issues/7) ![Raspberry Pi](https://img.shields.io/badge/Raspberry%20Pi-A22846?style=for-the-badge&logo=Raspberry%20Pi&logoColor=white) ![Python](https://img.shields.io/badge/Python-3.X-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54) [![Licence](https://img.shields.io/github/license/mathoudebine/turing-smart-screen-python?style=for-the-badge)](./LICENSE)
  
A Python system monitor program and an abstraction library for **small IPS USB-C displays.**    

Supported operating systems : macOS, Windows, Linux (incl. Raspberry Pi), basically all OS that support Python 3.9+  

### ✅ Supported smart screens models:

| ✅ Turing Smart Screen / TURZX                                                                                                                                                                                                                                                                                                                                                                  |
|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| <img src="res/docs/turing.webp" width="30%" height="30%"/> <img src="res/docs/turing46inch.png" width="30%" height="30%"/> <img src="res/docs/turing5inch.png" width="30%" height="30%"/> <br/> <img src="res/docs/turing2inch.webp" width="30%" height="30%"/> <img src="res/docs/turing8inch.png" width="30%" height="30%"/> <img src="res/docs/turing8inch.webp" width="30%" height="30%"/> |
| All available sizes and hardware revisions supported: **2.1" / 2.8" / 3.5" / 4.6" / 5" / 5.2" / 8.0" / 8.8" / 9.2" / 12.3"** <br/>UART and USB protocols supported. Note: no video or storage support for now                                                                                                                                                                                  |

| ✅ XuanFang 3.5"                                   | ✅ [UsbPCMonitor 3.5" / 5"](https://aliexpress.com/item/1005003931363455.html)                       | ✅ Kipye Qiye Smart Display 3.5"                                                  |
|---------------------------------------------------|-----------------------------------------------------------------------------------------------------|----------------------------------------------------------------------------------|
| <img src="res/docs/xuanfang.webp"/>               | <img src="res/docs/UsbPCMonitor_5inch.webp" width="60%" height="60%"/>                              | <img src="res/docs/kipye-qiye-35.webp" width="60%" height="60%"/>                |
| revision B & flagship (with backplate & RGB LEDs) | Unknown manufacturer, visually similar to Turing 3.5" / 5". Original software is `UsbPCMonitor.exe` | Front panel has an engraved inscription "奇叶智显" Qiye Zhixian (Qiye Smart Display) |

| ✅ WeAct Studio Display FS V1 0.96"                            | ✅ WeAct Studio Display FS V1 3.5"                            |
|---------------------------------------------------------------|--------------------------------------------------------------|
| <img src="res/docs/weact_0.96.jpg" width="60%" height="60%"/> | <img src="res/docs/weact_3.5.png" width="60%" height="60%"/> |

<details>

<summary><h3>❌ Not (yet) supported / not tested smart screen models</h3></summary>

| ❔ _AIDA64 / AX206 / USB2LCD..._                                                                                                                                                                        | ❔ _[ACEMAGIC S1 Mini PC - integrated 1,9″ display](https://acemagic.com/products/acemagic-s1-12th-alder-laker-n95-mini-pc)_                                  |
|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------|
| <img src="res/docs/ax206.jpg" width="45%" height="45%" /> <img src="res/docs/geekteches_ad35.jpg" width="45%" height="45%" /> <br/> <img src="res/docs/smartcool_lcd.webp" width="45%" height="45%" /> | <img src="res/docs/acemagic-s1-mini.jpg"/>                                                                                                                   |
| Not supported for now. Produced by multiple manufacturers, all use the same [Appotech AX206 hacked photo frame firmware](https://github.com/dreamlayers/dpf-ax). Supported by AIDA64 and lcd4linux     | Not supported for now but could be integrated: protocol has been decoded, [see here](https://github.com/mathoudebine/turing-smart-screen-python/issues/677). |

| ❔ _NXElec BeadaPanel 3/4/5/6/7_                                                                                                                                                                                                                                                                                           |
|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| <img src="res/docs/beadapanel-3.jpg" width="30%" height="30%" /> <img src="res/docs/beadapanel-5s.jpg" width="30%" height="30%" /> <img src="res/docs/beadapanel-6.jpg" width="30%" height="30%" />                                                                                                                       |
| Not supported for now but could be integrated: [Pankel-Link V1.0 Protocol Specification](https://www.nxelec.com/documents/bp/Panel-Link_USB_Media_Stream_Transport_Protocol_Rev10.pdf) / [Status-Link V1.1 Protocol Specification](https://www.nxelec.com/documents/bp/Status-Link_USB_Panel_Control_Protocol_Rev11.pdf). |

| ❌ _Waveshare [2.1inch](https://www.waveshare.com/wiki/2.1inch-USB-Monitor) / [2.8inch](https://www.waveshare.com/wiki/2.8inch-USB-Monitor) / [5inch](https://www.waveshare.com/wiki/5inch-USB-Monitor) / [7inch](https://www.waveshare.com/wiki/7inch-USB-Monitor) USB-Monitor_                                                                                                            | ❌ _[GUITION Smart screen 3.5"](https://aliexpress.com/item/1005006169962183.html)_                                                                                                                                                                                                          |
|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| <img src="res/docs/waveshare-21inch-28inch.png"/>                                                                                                                                                                                                                                                                                                                                          | <img src="res/docs/guition.webp"/>                                                                                                                                                                                                                                                          |
| Sold on [Waveshare shop](https://www.waveshare.com/2.8inch-usb-monitor.htm) or [Aliexpress](https://fr.aliexpress.com/item/1005006071685067.html). Managed by [proprietary Windows software "Waveshare PC Monitor"](https://github.com/mathoudebine/turing-smart-screen-python/wiki/Vendor-apps#waveshare-pc-monitor---vendor-app). Cannot be supported by this project: needs a firmware. | Managed by [proprietary Windows software "GUITION Smart screen"](https://github.com/mathoudebine/turing-smart-screen-python/wiki/Vendor-apps#guition---vendor-app). Cannot be supported by this project: [see here](https://github.com/mathoudebine/turing-smart-screen-python/issues/426). |

| ❌ _[(Fuldho?) 3.5" IPS Screen](https://aliexpress.com/item/1005005632018367.html)_                                                                                                                                                     |
|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| <img src="res/docs/fuldho_3.5.jpg" width="40%" height="40%" />                                                                                                                                                                         |
| Managed by [proprietary Windows software `SmartMonitor.exe`](https://smartdisplay.lanzouo.com/b04jvavkb). Cannot be supported by this project: [see here](https://github.com/mathoudebine/turing-smart-screen-python/discussions/298). |

</details>

### [> What is my smart screen model?](https://github.com/mathoudebine/turing-smart-screen-python/wiki/Hardware-revisions)  

**Please note all listed smart screens are different products** designed and produced by different companies, despite having a similar appearance. Their communication protocol is also different.  
This project offers an abstraction layer to manage all of these products in a unified way, including some product-specific features like backplate RGB LEDs for available models!

If you haven't received your screen yet but want to start developing your theme now, you can use the [**"simulated LCD" mode!**](https://github.com/mathoudebine/turing-smart-screen-python/wiki/Simulated-display)

## How to start

### [> Follow instructions on the wiki to configure and start this project.](https://github.com/mathoudebine/turing-smart-screen-python/wiki)

There are 2 possible uses of this project Python code:
* **[as a System Monitor](#system-monitor)**, a standalone program working with themes to display your computer HW info and custom data in an elegant way.
[Check if your hardware is supported.](https://github.com/mathoudebine/turing-smart-screen-python/wiki/System-monitor-:-hardware-support)
* **[integrated in your project](#control-the-display-from-your-python-projects)**, to fully control the display from your own Python code.

## System monitor

This project is mainly a complete standalone program to use your screen as a system monitor, like the original vendor app.  
Some themes are already included for a quick start!  
### [> Configure and start system monitor](https://github.com/mathoudebine/turing-smart-screen-python/wiki/System-monitor-:-how-to-start)
<img src="res/docs/config_wizard.png"/>  

* Fully functional multi-OS code base (operates out of the box, tested on Windows, Linux & MacOS).
* Display configuration using GUI configuration wizard or `config.yaml` file: no Python code to edit.
* Compatible with [multiple smart screen models (Turing, XuanFang...)](https://github.com/mathoudebine/turing-smart-screen-python/wiki/Hardware-revisions). Backplate RGB LEDs are also supported for available models!
* Support [multiple hardware sensors and metrics (CPU/GPU usage, temperatures, memory, disks, etc)](https://github.com/mathoudebine/turing-smart-screen-python/wiki/System-monitor-:-themes#stats-entry) with configurable refresh intervals.
* Allow [creation of themes (see `res/themes`) with `theme.yaml` files using theme editor](https://github.com/mathoudebine/turing-smart-screen-python/wiki/System-monitor-:-themes) to be [shared with the community!](https://github.com/mathoudebine/turing-smart-screen-python/discussions/categories/themes)
* Easy to expand: [custom Python data sources](https://github.com/mathoudebine/turing-smart-screen-python/wiki/System-monitor-:-themes#add-custom-stats-to-a-theme) can be written to pull specific information and display it on themes like any other sensor.
* Auto-detect COM port based on the selected smart screen model.
* Tray icon with Exit option, useful when the program is running in background.

### [> List and preview of included themes](res/themes/themes.md)
<img src="res/themes/3.5inchTheme2/preview.png" height="150" /> <img src="res/themes/Terminal/preview.png" height="150" /> <img src="res/themes/Cyberpunk-net/preview.png" height="150" /> <img src="res/themes/bash-dark-green-gpu/preview.png" height="150" /> <img src="res/themes/Landscape6Grid/preview.png" width="150" /> <img src="res/themes/LandscapeMagicBlue/preview.png" width="150" /> <img src="res/themes/LandscapeEarth/preview.png" width="150" /> ... [view full list](res/themes/themes.md)
### [> Themes creation/edition (using theme editor)](https://github.com/mathoudebine/turing-smart-screen-python/wiki/System-monitor-:-themes)
### [> Themes shared by the community](https://github.com/mathoudebine/turing-smart-screen-python/discussions/categories/themes)
<img src="https://user-images.githubusercontent.com/79225820/203648707-6f043068-5c9d-454d-9c0a-3d9ea02ece77.jpg" height="150" /> <img src="https://user-images.githubusercontent.com/121983479/210663324-994c987a-6489-4482-8883-db74ef566014.jpg" height="150" />
<img src="https://user-images.githubusercontent.com/120036534/208128675-897f60cd-5647-40b7-b074-b56b67e775dd.png" height="150" /> <img src="https://user-images.githubusercontent.com/65172896/217549510-149913ac-ef4e-4f61-8f5e-6d768483a02c.png" height="150" /> and more... Share yours!

## Control the display from your Python projects

If you don't want to use your screen for system monitoring, you can just use this project as a module from any Python code to do some simple operations on the display:
- **Display custom picture**
- **Display text**
- **Display horizontal / radial progress bar**
- **Screen rotation**
- Clear the screen (blank)
- Turn the screen on/off
- Display soft reset
- Set brightness
- Set backplate RGB LEDs color (on supported hardware rev.) 

This project will act as an abstraction library to handle specific protocols and capabilities of each supported smart screen models in a transparent way for the user.
Check `simple-program.py` as an example.

### [> Control the display from your code](https://github.com/mathoudebine/turing-smart-screen-python/wiki/Control-screen-from-your-own-code)

## Troubleshooting
If you have trouble running the program as described in the wiki, please check [open/closed issues](https://github.com/mathoudebine/turing-smart-screen-python/issues) & [the wiki Troubleshooting page](https://github.com/mathoudebine/turing-smart-screen-python/wiki/Troubleshooting)

## They're talking about it!

* [Hackaday - Cheap LCD Uses USB Serial](https://hackaday.com/2023/09/11/cheap-lcd-uses-usb-serial/)  


* [CNX Software - Turing Smart Screen – A low-cost 3.5-inch USB Type-C information display](https://www.cnx-software.com/2022/04/29/turing-smart-screen-a-low-cost-3-5-inch-usb-type-c-information-display/)


* [Phazer Tech - Turing Smart Screen Python ](https://phazertech.com/tutorials/turing-smart-screen.html)

## Star History

[![Star History Chart](https://api.star-history.com/svg?repos=mathoudebine/turing-smart-screen-python&type=Date)](https://star-history.com/#mathoudebine/turing-smart-screen-python&Date)
