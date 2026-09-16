#!/usr/bin/env bash
set -euo pipefail
root_dir="$(cd -- "$(dirname -- "$0")" && pwd)"
backend="auto"
dry_run=false
while (($#)); do
    case "$1" in
        --backend) [[ $# -ge 2 ]] || { echo 'Missing backend.' >&2;exit 2; };backend="$2";shift 2 ;;
        --dry-run) dry_run=true;shift ;;
        *) echo 'Usage: ./install.sh [--backend cinnamon|kde] [--dry-run]' >&2;exit 2 ;;
    esac
done
if [[ "$backend" == auto ]]; then
    desktop="${XDG_CURRENT_DESKTOP:-${XDG_SESSION_DESKTOP:-}}"
    case ":${desktop,,}:" in
        *:cinnamon:*|*:x-cinnamon:*) backend=cinnamon ;;
        *:kde:*|*:plasma:*) backend=kde ;;
        *) echo 'Cannot identify desktop. Use --backend cinnamon or --backend kde.' >&2;exit 2 ;;
    esac
fi
case "$backend" in
    cinnamon)
        [[ "${XDG_SESSION_TYPE:-x11}" != wayland ]] || { echo 'Cinnamon backend requires X11.' >&2;exit 2; }
        installer="$root_dir/install-extension.sh" ;;
    kde) installer="$root_dir/install-kde.sh" ;;
    *) echo 'Unknown backend.' >&2;exit 2 ;;
esac
if "$dry_run"; then echo "Selected backend: $backend";else exec "$installer";fi
