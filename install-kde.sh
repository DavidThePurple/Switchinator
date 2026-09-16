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
command -v python3 >/dev/null && command -v gdbus >/dev/null && command -v systemctl >/dev/null || {
    echo 'KDE installation requires python3, gdbus and a user systemd session for input recovery.' >&2;exit 1;
}
package="$root_dir/kde/switchinator"
package_root="${XDG_DATA_HOME:-$HOME/.local/share}/kwin-wayland/effects"
if kpackagetool6 --type KWin/Effect --show switchinator --packageroot "$package_root" >/dev/null 2>&1;then
    kpackagetool6 --type KWin/Effect --upgrade "$package" --packageroot "$package_root"
else
    kpackagetool6 --type KWin/Effect --install "$package" --packageroot "$package_root"
fi
# Start recovery outside the compositor before enabling the effect.
python3 "$root_dir/tools/install_kde_watchdog.py"
runtime_revision="$(python3 "$root_dir/tools/prepare_kde_runtime.py" "$package")"
# Remove the obsolete fallback package so settings list a single effect.
legacy_root="${XDG_DATA_HOME:-$HOME/.local/share}/kwin/effects"
if [[ -f "$legacy_root/switchinator/metadata.json" ]];then
    kpackagetool6 --type KWin/Effect --remove switchinator --packageroot "$legacy_root"
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
# Refresh KWin's in-memory KConfig before constructing the new runtime.
# Disabling during the refresh prevents reconfigure from auto-loading a copy.
kwriteconfig6 --file kwinrc --group Plugins --key switchinatorEnabled false
kwriteconfig6 --file kwinrc --group Effect-switchinator --key RuntimeRevision "$runtime_revision"
gdbus call --session --dest org.kde.KWin --object-path /KWin --method org.kde.KWin.reconfigure >/dev/null
reply="$(loaded_effects)"
if is_loaded "$reply";then
    effect_call unloadEffect >/dev/null
    reply="$(loaded_effects)"
    if is_loaded "$reply";then echo 'KWin did not unload the old effect; activation stopped.' >&2;exit 1;fi
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
command -v python3 >/dev/null && command -v gdbus >/dev/null || {
    echo 'Effect loaded, but automatic Alt+Tab setup requires python3 and gdbus.' >&2;exit 1;
}
if ! python3 "$root_dir/tools/kde_shortcuts.py";then
    effect_call unloadEffect >/dev/null
    exit 1
fi
kwriteconfig6 --file kwinrc --group Plugins --key switchinatorEnabled true
printf 'Installed runtime: %s\n' "$runtime_revision"
cat <<'MESSAGE'
Switchinator installed and loaded. Enabled for future desktop sessions.
Try Alt+Tab (hold Alt, press Tab; release Alt to select).
A separate watchdog unloads an overlay stuck open for 60 seconds and
restores your original shortcuts. It does not depend on the overlay timer.
Open settings directly: ./configure-kde.sh
Original shortcut backup: ~/.config/switchinator/kde-shortcuts.json
If the overlay does not open, run: ./diagnose-kde.sh
MESSAGE
