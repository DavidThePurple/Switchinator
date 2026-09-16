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
cat <<'MESSAGE'
Installed Switchinator for KDE (experimental). Cinnamon was not modified.
Enable Switchinator in System Settings → Desktop Effects.
The initial shortcut is Meta+Tab. To use Alt+Tab, assign Switchinator's
shortcuts in System Settings → Shortcuts → KWin and remove conflicting
native task-switcher shortcuts. The installer does not overwrite them.
SteamOS Gaming Mode is not supported by this package.
MESSAGE
