#!/usr/bin/env bash
set -euo pipefail
root_dir="$(cd -- "$(dirname -- "$0")" && pwd)"
[[ "${EUID}" -ne 0 ]] || { echo 'Run as your normal desktop user, not root.' >&2;exit 2; }
command -v kpackagetool6 >/dev/null || { echo 'This backend requires Plasma 6 and kpackagetool6.' >&2;exit 2; }
version_command=""
for candidate in kwin_wayland kwin_x11; do
    if command -v "$candidate" >/dev/null;then version_command="$candidate";break;fi
done
[[ -n "$version_command" ]] || { echo 'KWin was not found.' >&2;exit 2; }
version="$($version_command --version 2>/dev/null)"
if [[ "$version" =~ ([0-9]+)\.([0-9]+) ]];then
    major="${BASH_REMATCH[1]}";minor="${BASH_REMATCH[2]}"
    ((major==6 && minor>=4)) || { echo 'The experimental KDE backend requires KWin 6.4 or later in the 6.x series.' >&2;exit 2; }
else echo 'Could not determine the KWin version.' >&2;exit 2;fi
package="$root_dir/kde/switchinator"
if kpackagetool6 --type KWin/Effect --show switchinator >/dev/null 2>&1;then
    kpackagetool6 --type KWin/Effect --upgrade "$package"
else
    kpackagetool6 --type KWin/Effect --install "$package"
fi
# Load the package in this desktop session, then persist its enabled state.
# Package installation alone does not activate a KWin effect.
command -v kwriteconfig6 >/dev/null || { echo 'Package installed, but kwriteconfig6 is missing; activation was not completed.' >&2;exit 1; }
if command -v gdbus >/dev/null;then
    effect_call() { gdbus call --session --dest org.kde.KWin --object-path /Effects --method "org.kde.kwin.Effects.$1" switchinator; }
    loaded_effects() { gdbus call --session --dest org.kde.KWin --object-path /Effects --method org.freedesktop.DBus.Properties.Get org.kde.kwin.Effects loadedEffects; }
elif command -v dbus-send >/dev/null;then
    effect_call() { dbus-send --session --print-reply --dest=org.kde.KWin /Effects "org.kde.kwin.Effects.$1" string:switchinator; }
    loaded_effects() { dbus-send --session --print-reply --dest=org.kde.KWin /Effects org.freedesktop.DBus.Properties.Get string:org.kde.kwin.Effects string:loadedEffects; }
else echo 'Package installed, but no D-Bus command tool is available; activation was not completed.' >&2;exit 1;fi
is_loaded() { [[ "$1" == *"'switchinator'"* || "$1" == *'"switchinator"'* ]]; }
if ! reply="$(loaded_effects 2>&1)";then
    echo "Package installed, but the running KWin desktop could not be reached: $reply" >&2;exit 1
fi
if is_loaded "$reply";then
    effect_call unloadEffect >/dev/null
fi
if ! reply="$(effect_call loadEffect 2>&1)";then
    echo "Package installed, but KWin could not load it: $reply" >&2;exit 1
fi
if ! reply="$(loaded_effects 2>&1)" || ! is_loaded "$reply";then
    echo 'Package installed, but KWin did not load Switchinator. Installation is incomplete.' >&2
    echo "KWin response: $reply" >&2
    echo 'Inspect the desktop log for QML errors: journalctl --user -b | grep -i switchinator' >&2
    exit 1
fi
kwriteconfig6 --file kwinrc --group Plugins --key switchinatorEnabled true
cat <<'MESSAGE'
Switchinator installed and loaded. Enabled for future desktop sessions.
Try Meta+Tab (hold Meta, press Tab; release Meta to select).
Open settings directly: ./configure-kde.sh
To assign Alt+Tab, open KDE Shortcuts and replace the conflicting native
window-switcher shortcuts with Switchinator's next/previous shortcuts.
MESSAGE
