#!/usr/bin/env bash
set -euo pipefail
if command -v kcmshell6 >/dev/null;then
    exec kcmshell6 kcm_kwin_effects
elif command -v systemsettings >/dev/null;then
    exec systemsettings kcm_kwin_effects
else
    echo 'KDE settings launcher was not found on this system.' >&2
    exit 1
fi
