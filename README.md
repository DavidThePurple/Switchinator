# Switchinator

An animated Alt+Tab replacement for Cinnamon on X11. A row of window preview cards opens near your cursor and includes windows from every display. Hold Alt and press Tab to cycle; release Alt to activate the selected window on its original monitor. Shift+Alt+Tab cycles backward; Escape cancels.

The installed extension currently appears as **Card Switcher**, with UUID `card-switcher@everlasting.media`.

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

## Disable or uninstall

Disable **Card Switcher** in Extensions to stop the helper process and restore the saved Cinnamon Alt+Tab bindings. To uninstall, disable it first, then remove `~/.local/share/cinnamon/extensions/card-switcher@everlasting.media`.

## How it works

The Cinnamon extension manages configuration, theme integration, system-window thumbnail capture, and shortcut restoration. A separate Python/Qt process handles the overlay, cached XComposite previews, animation, and keyboard input. No driver or compositor configuration changes are installed.

## Current limitations

This is an early version. Wayland is unsupported. Minimized windows may not have a preview. System-window snapshots are supplied by Cinnamon; other windows use XComposite. Multi-monitor behavior and long-term NVIDIA stability need broader testing.

## License

MIT. See [LICENSE](LICENSE).
