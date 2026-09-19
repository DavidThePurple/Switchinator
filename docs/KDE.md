# KDE / SteamOS Desktop Mode (experimental)

This package targets **KWin 6.4–6.x**. The native input path is verified on Wayland; X11 remains unverified. It is separate from the Cinnamon extension and uses a declarative KWin effect. Shortcut setup and external recovery require Python 3 (standard library only), `gdbus`, and a user systemd session; no PyQt or python-xlib is needed and installs in the user's KDE package directory. SteamOS's read-only system partition does not need to be unlocked.

It is tested with mock KWin APIs under Qt 6 and in an isolated **real KWin 6.4.3 Wayland session**. Repeated normal/rapid selection, same-session upgrades, and external watchdog recovery are exercised there. Steam Deck hardware and docked-display behavior still need on-device verification. Treat it as an experimental backend until the on-device checklist below passes. SteamOS Gaming Mode is not supported.

## Install

From SteamOS **Desktop Mode**, inside the cloned repository:

```sh
./install.sh
```

Alternatively select explicitly with `./install.sh --backend kde`. The installer checks the KWin version, copies the package and versioned runtime directly into KWin's preferred user package directory, loads it into the running KWin session, verifies that KWin lists it as loaded, and enables it for future desktop sessions. It verifies that the previous copy is unloaded during upgrades, refreshes KWin's configuration, and starts the external recovery service before assigning shortcuts. If loading fails, it reports installation as incomplete instead of claiming success. It backs up the conflicting KWin shortcuts and assigns Alt+Tab / Shift+Alt+Tab to Switchinator. Shortcut registration and assignment are verified before reporting success.

Once installation reports **installed and loaded**, use **Alt+Tab**; use **Shift+Alt+Tab** to cycle backward. Hold the modifier to keep the row open, and release it to select.

Open the KDE effect settings directly, without navigating menus:

```sh
./configure-kde.sh
```

This launches `kcmshell6 kcm_kwin_effects` (or the System Settings module directly). Search for Switchinator and use its configure button. These are **KDE Desktop Mode settings**, not the Steam Gaming Mode settings screen.

The original bindings are saved in `~/.config/switchinator/kde-shortcuts.json` (or your configured XDG config directory). Reinstalling retains that original backup. The installer assigns only Alt+Tab and Shift+Alt+Tab; it does not require an additional Meta-key binding.

If the overlay does not open, run `./diagnose-kde.sh` after trying Alt+Tab and share its output. This reports the loaded effect, registered shortcut, stored rotation toggle, and recent KWin/QML errors.

The installer performs no driver changes and does not alter Cinnamon files, settings, or bindings.

## Features and settings

Run `./configure-kde.sh`, search for Switchinator, and use its configure button for:

- Theme-derived or custom primary, secondary, accent, and text colors.
- Flat-row or 3D-carousel layout, optional background, 60–200% preview size, and independent selected-card enlargement.
- None, tilt with animated entry and rocking, sway, float, or pulse.
- Animation toggle, appearance duration, and return-to-monitor duration.
- Automatic rotation toggle and delay (1–300 seconds).

A small native modifier bridge tracks Alt release before KWin finishes creating its asynchronous view. Very quick Alt+Tab taps select directly when the view is not ready; they do not leave an overlay waiting for a release event that has already happened. The bundled x86-64 module requires Qt 6.4+ and glibc 2.34+; [source and rebuild instructions](../native/README.md) are included.

The selected layout opens near the pointer on its display, includes eligible windows from every display, and keeps the selected window on its original monitor. Escape cancels selection. The top-right **Select** and **Close** buttons work independently of keyboard focus. With automatic rotation off, clicking a preview selects it and closes the row. With rotation on, clicks continue to record the chosen sequence.

The effect has a 60-second cancellation timer and a stalled-animation completion timeout. A separate **user service**, `switchinator-watchdog.service`, also checks KWin's native `activeEffects` property every two seconds. If the overlay remains active for 60 seconds, this service disables and unloads Switchinator, releasing its keyboard/mouse grabs, and restores the saved native shortcuts. It runs outside the QML engine and does not rely on card clicks, key events, or the effect's timers. Reinstall to enable Switchinator again after watchdog recovery. If KWin itself stops answering D-Bus, this service cannot force a safe recovery.

Upgrades use a stable entry point at `~/.local/share/kwin-wayland/effects/switchinator/contents/ui/main.qml` and content-addressed runtime directories. This avoids KWin reusing cached QML and JavaScript after an update. The first migration uses KWin's preferred `kwin-wayland` package path to bypass the old cached entry point under `kwin/effects`. The obsolete installed directory is moved into `~/.local/share/switchinator/backups/legacy-*/switchinator`; the repository and saved settings remain intact. Installation does not depend on the package manager's `--show`, `--upgrade`, or `--remove` lookup, which can resolve the wrong package root during this migration. The installer prints the installed runtime revision; `diagnose-kde.sh` includes that revision, watchdog state, active effects, and the loaded-runtime log.

This update problem is reported [by KWin effect developers](https://discuss.kde.org/t/proper-way-to-reload-a-kwin-effect/46880) and matches [Qt's component-cache behavior](https://doc.qt.io/qt-6/qqmlengine.html#clearComponentCache). The regression test keeps one Qt engine and entry URL across upgrades and verifies that changed imported code loads without clearing that engine's cache.

When automatic rotation is enabled, click preview cards in order while keeping the modifier held. Badges show the order. Release the modifier to select the first chosen window and begin rotation. Right-click a card to reset to all-window rotation; Escape cancels sequence edits. Closed windows are skipped. An empty custom sequence after windows close does not fall back to unrelated windows. Sequences last until the effect is unloaded.

## Performance

Cards use frozen GPU textures; moving and tilting them does not continuously render their source windows. On opening the effect, preview requests are staggered rather than captured in one batch. Within an open switcher, each window has a five-second minimum between snapshots. KWin unloads the view when it closes, so the next opening creates fresh textures. While open, the selected preview can be refreshed once every eight seconds. The source window is detached after each texture snapshot; the cache is independent of the card so it survives the return animation. No preview capture timer runs while the effect is hidden, and rotation does not capture previews.

KWin's `SceneEffect` replaces the normal desktop scene while open, so the effect also renders the desktop background, panels, and visible windows at their normal positions. Those underlying windows remain live; they are separate from the cached card previews. This rendering path needs real-device performance testing.

Minimized or capture-excluded windows may lack a preview. Capture-excluded windows are omitted from the switcher. This backend uses KWin's stable internal window IDs, not X11 IDs, so native Wayland windows can be included.

## Disable or uninstall

Run `./configure-kde.sh` and disable Switchinator first. Restore the saved native shortcuts, then remove only this package:

```sh
systemctl --user disable --now switchinator-watchdog.service
python3 tools/kde_shortcuts.py --restore
rm -r -- "${XDG_DATA_HOME:-$HOME/.local/share}/kwin-wayland/effects/switchinator"
```

## On-device verification checklist

1. Install, confirm the loaded verification succeeds, and test Alt+Tab and Shift+Alt+Tab; verify the original shortcut backup exists.
2. Test one display, docked displays, mixed scaling, and negative monitor coordinates.
3. Test native Wayland and XWayland apps, obscured windows, and minimized windows.
4. Check both flat-row and 3D-carousel layouts, selection growth, in-tilt, rocking, all optional styles, and disabled animations.
5. Release the modifier to windows on each monitor; confirm Escape never activates a window.
6. Enable rotation at a comfortable delay, test the default order, then click a custom sequence.
7. Close one chosen window and then all chosen windows; confirm no unrelated windows activate.
8. Check frame pacing with animated wallpapers and many windows; confirm hiding the effect stops capture work.
9. Disable automatic rotation, open and cancel the switcher, and wait beyond the delay; confirm no window activates automatically. Disable and re-enable the effect; verify shortcuts and ordinary KDE desktop behavior.

## Development checks

```sh
/usr/bin/python3 -m unittest discover -s tests -v
node tests/test_kde_logic.js
# Optional: requires PySide6; exercises a real invisible QQuickRenderControl window.
python3 tests/check_kde_rendercontrol.py
```

Python checks need PyQt5/python-xlib for Cinnamon and PyQt6 with QtQuick/QML for the headless KDE smoke test. Neither Python test dependencies nor the mock QML modules are installed by the KDE installer. The smoke test substitutes KWin APIs and tests focus clearing, actual Alt-release and Escape events, animated activation, and the off toggle. The optional rendering-window check verifies frozen pixels and capture throttling inside a real invisible Qt window. The upgrade test additionally uses one real Qt engine to load successive content-addressed runtimes and imports. The recovery tests check native unload ordering and timing. These checks cannot prove real compositor compatibility or recovery on a nonresponsive KWin process.

KDE reference APIs: [declarative effects](https://develop.kde.org/docs/plasma/kwineffect/), [Workspace](https://api.kde.org/qml-org-kde-kwin-workspace.html), [WindowThumbnail](https://api.kde.org/qml-org-kde-kwin-windowthumbnail.html).
