# KDE / SteamOS Desktop Mode (experimental)

This package targets **KWin 6.4–6.x** on Wayland or X11. It is separate from the Cinnamon extension and uses a declarative KWin effect. It requires no Python dependencies and installs in the user's KDE package directory. SteamOS's read-only system partition does not need to be unlocked.

It is implemented and tested with mock KWin APIs under Qt 6, **not yet verified on an actual SteamOS/KWin session**. Treat it as an experimental backend until the on-device checklist below passes. SteamOS Gaming Mode is not supported.

## Install

From SteamOS **Desktop Mode**, inside the cloned repository:

```sh
./install.sh
```

Alternatively select explicitly with `./install.sh --backend kde`. The installer checks the KWin version, installs or upgrades the package with `kpackagetool6`, loads it into the running KWin session, verifies that KWin lists it as loaded, and enables it for future desktop sessions. It reloads an existing copy during upgrades. If loading fails, it reports installation as incomplete instead of claiming success. Native shortcuts are not overwritten.

Once installation reports **installed and loaded**, use **Meta+Tab** initially; use **Meta+Shift+Tab** to cycle backward. Hold the modifier to keep the row open, and release it to select.

Open the KDE effect settings directly, without navigating menus:

```sh
./configure-kde.sh
```

This launches `kcmshell6 kcm_kwin_effects` (or the System Settings module directly). Search for Switchinator and use its configure button. These are **KDE Desktop Mode settings**, not the Steam Gaming Mode settings screen.

To use **Alt+Tab**, open **KDE System Settings → Shortcuts → KWin**, remove the conflicting native task-switcher shortcuts, and assign Alt+Tab / Alt+Shift+Tab to **Switchinator: next window / previous window**. This is deliberately a user choice. Record your original shortcuts so they can be restored later.

The installer performs no driver changes and does not alter Cinnamon files, settings, or bindings.

## Features and settings

Run `./configure-kde.sh`, search for Switchinator, and use its configure button for:

- Theme-derived or custom primary, secondary, accent, and text colors.
- Optional row background, 60–200% preview size, independent selected-card enlargement.
- None, tilt with animated entry and rocking, sway, float, or pulse.
- Animation toggle, appearance duration, and return-to-monitor duration.
- Automatic rotation toggle and delay (1–300 seconds).

The row opens near the pointer on its display, includes eligible windows from every display, and keeps the selected window on its original monitor. Escape cancels selection.

When automatic rotation is enabled, click preview cards in order while keeping the modifier held. Badges show the order. Release the modifier to select the first chosen window and begin rotation. Right-click a card to reset to all-window rotation; Escape cancels sequence edits. Closed windows are skipped. An empty custom sequence after windows close does not fall back to unrelated windows. Sequences last until the effect is unloaded.

## Performance

Cards use cached images; moving and tilting them does not continuously render their source windows. On opening the effect, preview requests are staggered rather than captured in one batch. Each window has a five-second minimum between snapshots. While open, the selected preview can be refreshed once every eight seconds. The capture item is detached after each snapshot. No preview capture timer runs while the effect is hidden, and rotation does not capture previews.

KWin's `SceneEffect` replaces the normal desktop scene while open, so the effect also renders the desktop background, panels, and visible windows at their normal positions. Those underlying windows remain live; they are separate from the cached card previews. This rendering path needs real-device performance testing.

Minimized or capture-excluded windows may lack a preview. Capture-excluded windows are omitted from the switcher. This backend uses KWin's stable internal window IDs, not X11 IDs, so native Wayland windows can be included.

## Disable or uninstall

Run `./configure-kde.sh` and disable Switchinator first. If you reassigned Alt+Tab, restore your native task-switcher shortcuts in Shortcuts. Then remove only this package:

```sh
kpackagetool6 --type KWin/Effect --remove switchinator
```

## On-device verification checklist

1. Install, confirm the loaded verification succeeds, and test Meta+Tab; verify native Alt+Tab is still available.
2. Test one display, docked displays, mixed scaling, and negative monitor coordinates.
3. Test native Wayland and XWayland apps, obscured windows, and minimized windows.
4. Check selection growth, in-tilt, rocking, all optional styles, and disabled animations.
5. Release the modifier to windows on each monitor; confirm Escape never activates a window.
6. Enable rotation at a comfortable delay, test the default order, then click a custom sequence.
7. Close one chosen window and then all chosen windows; confirm no unrelated windows activate.
8. Check frame pacing with animated wallpapers and many windows; confirm hiding the effect stops capture work.
9. Disable and re-enable; verify shortcuts, focus, and ordinary KDE desktop behavior.

## Development checks

```sh
/usr/bin/python3 -m unittest discover -s tests -v
node tests/test_kde_logic.js
```

Python checks need PyQt5/python-xlib for Cinnamon and PyQt6 with QtQuick/QML for the headless KDE smoke test. Neither Python test dependencies nor the mock QML modules are installed by the KDE installer. The smoke test substitutes KWin APIs and cannot prove real compositor compatibility.

KDE reference APIs: [declarative effects](https://develop.kde.org/docs/plasma/kwineffect/), [Workspace](https://api.kde.org/qml-org-kde-kwin-workspace.html), [WindowThumbnail](https://api.kde.org/qml-org-kde-kwin-windowthumbnail.html).
