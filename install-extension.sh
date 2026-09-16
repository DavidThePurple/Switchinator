#!/bin/bash
set -e
bundle_dir="$(cd -- "$(dirname -- "$0")" && pwd)"
extension_dir="$HOME/.local/share/cinnamon/extensions/card-switcher@everlasting.media"
/usr/bin/python3 -c 'import PyQt5, Xlib'
mkdir -p "$extension_dir"
cp "$bundle_dir/extension/card-switcher@everlasting.media/"{extension.js,metadata.json,settings-schema.json,switcher.py} "$extension_dir/"
/usr/bin/python3 - <<'PY'
from gi.repository import Gio
s=Gio.Settings.new('org.cinnamon')
e=list(s.get_strv('enabled-extensions'))
if 'card-switcher@everlasting.media' not in e:e.append('card-switcher@everlasting.media')
s.set_strv('enabled-extensions',e);Gio.Settings.sync()
PY
