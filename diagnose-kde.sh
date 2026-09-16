#!/usr/bin/env bash
set -u
printf '%s\n' '--- Switchinator desktop diagnostics ---'
printf 'Desktop: %s; session: %s\n' "${XDG_CURRENT_DESKTOP:-unknown}" "${XDG_SESSION_TYPE:-unknown}"
if command -v gdbus >/dev/null;then
    gdbus call --session --dest org.kde.KWin --object-path /Effects --method org.freedesktop.DBus.Properties.Get org.kde.kwin.Effects loadedEffects
    gdbus call --session --dest org.kde.kglobalaccel --object-path /kglobalaccel --method org.kde.KGlobalAccel.shortcut "['kwin','SwitchinatorForward','KWin','Switchinator: next window']"
fi
if command -v kreadconfig6 >/dev/null;then
    printf 'Stored rotation setting: '
    kreadconfig6 --file kwinrc --group Effect-switchinator --key AutoRotate --default false
fi
if command -v kwin_wayland >/dev/null; then kwin_wayland --version; elif command -v kwin_x11 >/dev/null; then kwin_x11 --version; fi
journalctl --user -b --since '10 minutes ago' --no-pager 2>/dev/null | grep -Ei 'switchinator|SceneEffect|ShortcutHandler|qml.*(error|reference|typeerror)' | tail -50
