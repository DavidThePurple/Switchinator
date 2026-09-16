#!/bin/bash
set -euo pipefail
[[ "${SWITCHINATOR_ISOLATED_TEST:-}" == 1 && -e /.dockerenv ]] || { echo "Run only in the documented isolated test container." >&2; exit 2; }
export XDG_RUNTIME_DIR=/tmp/kwin-runtime
export XDG_CURRENT_DESKTOP=KDE XDG_SESSION_TYPE=wayland
export KWIN_WAYLAND_NO_PERMISSION_CHECKS=1 QT_LOGGING_TO_CONSOLE=1
export QT_LOGGING_RULES="kwin*.debug=true"
export LIBGL_ALWAYS_SOFTWARE=1 GALLIUM_DRIVER=llvmpipe KWIN_COMPOSE=O2
mkdir -p "$XDG_RUNTIME_DIR";chmod 700 "$XDG_RUNTIME_DIR"
kwin_wayland --virtual --no-lockscreen --width 1280 --height 800 --socket kwin-test > /tmp/kwin.log 2>&1 &
compositor=$!
trap 'kill "$compositor" 2>/dev/null || true' EXIT
for attempt in $(seq 1 100);do
 if gdbus call --session --dest org.kde.KWin --object-path /Effects --method org.freedesktop.DBus.Properties.Get org.kde.kwin.Effects loadedEffects >/tmp/loaded 2>/dev/null;then break;fi
 sleep .1
done
export WAYLAND_DISPLAY=kwin-test
python3 /app/tests/native_kde/probe.py
