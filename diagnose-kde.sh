#!/usr/bin/env bash
set -u
printf '%s\n' '--- Switchinator desktop diagnostics ---'
printf 'Desktop: %s; session: %s\n' "${XDG_CURRENT_DESKTOP:-unknown}" "${XDG_SESSION_TYPE:-unknown}"
printf 'Repository revision: '; git -C "$(dirname -- "$0")" rev-parse --short HEAD 2>/dev/null || true
if command -v gdbus >/dev/null;then
    gdbus call --session --dest org.kde.KWin --object-path /Effects --method org.freedesktop.DBus.Properties.Get org.kde.kwin.Effects loadedEffects
    printf 'Active effects (separate from installed/loaded):\n'
    gdbus call --session --dest org.kde.KWin --object-path /Effects --method org.freedesktop.DBus.Properties.Get org.kde.kwin.Effects activeEffects
    printf 'Forward shortcut (150994945 = Alt+Tab, 0 = unbound):\n'
    gdbus call --session --dest org.kde.kglobalaccel --object-path /kglobalaccel --method org.kde.KGlobalAccel.shortcut "['kwin','SwitchinatorForward','KWin','Switchinator: next window']"
    printf 'Current Alt+Tab owner:\n'
    gdbus call --session --dest org.kde.kglobalaccel --object-path /kglobalaccel --method org.kde.KGlobalAccel.action 150994945
fi
if command -v kreadconfig6 >/dev/null;then
    printf 'Stored rotation setting: '
    kreadconfig6 --file kwinrc --group Effect-switchinator --key AutoRotate --default false
    printf 'Configured runtime revision: '
    kreadconfig6 --file kwinrc --group Effect-switchinator --key RuntimeRevision
fi
printf 'External recovery service:\n'
systemctl --user is-active switchinator-watchdog.service 2>/dev/null || true
journalctl --user -b -u switchinator-watchdog.service --no-pager -n 10 2>/dev/null
printf 'Installed entry points:\n'
for backend_path in kwin-wayland kwin;do
    installed="${XDG_DATA_HOME:-$HOME/.local/share}/$backend_path/effects/switchinator/contents/ui/main.qml"
    if [[ -f "$installed" ]];then sha256sum "$installed";fi
done
if command -v kwin_wayland >/dev/null; then kwin_wayland --version; elif command -v kwin_x11 >/dev/null; then kwin_x11 --version; fi
# SteamOS may log the compositor outside the user journal.
journalctl -b --since '10 minutes ago' --no-pager _COMM=kwin_wayland + _COMM=kwin_x11 2>/dev/null | grep -Ei 'switchinator|SceneEffect|ShortcutHandler|qml.*(error|reference|typeerror)' | tail -50
