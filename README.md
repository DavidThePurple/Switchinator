# Switchinator

An animated Alt+Tab replacement for Cinnamon on X11, with a separate experimental KDE/SteamOS Desktop Mode backend. A row of window preview cards opens near your cursor and includes windows from every display. Hold Alt and press Tab to cycle; release Alt to activate the selected window on its original monitor. Shift+Alt+Tab cycles backward; Escape cancels.

The installed extension currently appears as **Card Switcher**, with UUID `card-switcher@everlasting.media`.

## Desktop support

| Desktop | Backend | Status |
| --- | --- | --- |
| Cinnamon 6.6 / X11 | Existing Python/Qt extension | Current version; unchanged by the KDE addition |
| KDE Plasma / KWin 6.4–6.x, Wayland or X11 | Native QML effect | Experimental; real-device verification pending |
| SteamOS Gaming Mode | — | Unsupported |

Run `./install.sh` to detect the desktop, or use `--backend cinnamon` / `--backend kde`. The original `./install-extension.sh` remains the Cinnamon installer. KDE packaging does not change Cinnamon files or configuration. See [KDE installation and verification](docs/KDE.md).

## Features

- Window snapshots with a five-second minimum between captures of each window.
- Staggered background prefetch of one system-window preview every eight seconds.
- Separate controls for card size and selected-card enlargement.
- Tilt with animated entry and rocking, sway, float, pulse, or no effect.
- Optional animations and row background.
- Current-theme colors or custom primary, secondary, accent, and text colors.

The cards animate cached images; animation does not continuously capture the source windows.

## Install

Tested on Linux Mint with Cinnamon 6.6 and X11. Requires Python 3, PyQt5, and python-xlib.

```sh
sudo apt install python3-pyqt5 python3-xlib
git clone https://github.com/DavidThePurple/Switchinator.git
cd Switchinator
./install-extension.sh
```

Run the installer as your normal user. It copies the extension into your user Cinnamon extensions directory and enables it. If it does not appear immediately, open **System Settings → Extensions** and enable **Card Switcher**. When updating an already loaded extension, disable and re-enable it to load the new files.

## Configure

Open **System Settings → Extensions → Card Switcher → Configure**. Settings apply the next time the switcher opens.

Preview size ranges from 60–200%; selected-card enlargement ranges from 1–3.5×. Both are limited to fit the display. Theme colors are enabled by default; the accent can be overridden independently. Disable theme colors to select every color yourself.

## Automatic rotation

Open **Configure → Automatic window rotation**, enable **Automatically rotate between windows**, and choose a delay from 1–300 seconds (default: 5). Rotation starts after that delay and normally includes all eligible windows across displays.

To choose an order, hold **Alt+Tab**, keep **Alt** held, and **left-click preview cards in the desired sequence**. Numbered badges show the order. The first click starts a new sequence; repeated clicks on the same card do not duplicate it. Use Tab to reach cards outside the visible row. Release Alt to activate the first chosen window and start cycling through the sequence.

Rotation pauses while Alt is held or the switcher is open. **Escape** cancels sequence edits. **Right-click** a card while holding Alt, then release Alt, to return to all-window rotation. Disable the rotation toggle to stop automatic switching. Closed windows are skipped; if all chosen windows close, custom rotation waits rather than switching to unrelated windows.

Custom sequences last for the current extension session. Rotation uses window IDs and never captures thumbnails on its timer.

## Disable or uninstall

Disable **Card Switcher** in Extensions to stop the helper process and restore the saved Cinnamon Alt+Tab bindings. To uninstall, disable it first, then remove `~/.local/share/cinnamon/extensions/card-switcher@everlasting.media`.

## How it works

The Cinnamon extension manages configuration, theme integration, system-window thumbnail capture, and shortcut restoration. A separate Python/Qt process handles the overlay, cached XComposite previews, animation, and keyboard input. No driver or compositor configuration changes are installed.

## Current limitations

This is an early version. The Cinnamon backend does not support Wayland. The experimental KDE backend targets Wayland and X11 but has not yet been verified on SteamOS. Minimized windows may not have a preview. System-window snapshots are supplied by Cinnamon; other windows use XComposite. Multi-monitor behavior and long-term NVIDIA stability need broader testing.

## License

MIT. See [LICENSE](LICENSE).
