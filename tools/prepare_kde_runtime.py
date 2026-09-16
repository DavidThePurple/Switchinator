#!/usr/bin/env python3
"""Install a fresh runtime URL without restarting KWin's shared QML engine."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile


def archive_legacy(data_home):
    legacy = Path(data_home) / 'kwin/effects/switchinator'
    if not legacy.exists() and not legacy.is_symlink():
        return
    metadata = legacy / 'metadata.json'
    if not metadata.exists() or json.loads(metadata.read_text())['KPlugin']['Id'] != 'switchinator':
        raise RuntimeError('Refusing to move an unrelated legacy effect at ' + str(legacy))
    backups = Path(data_home) / 'switchinator/backups'
    backups.mkdir(parents=True, exist_ok=True)
    archive = Path(tempfile.mkdtemp(prefix='legacy-', dir=backups)) / 'switchinator'
    # Rename the installed directory/link itself. Never follow it to the repo,
    # and never pass the source checkout to a package-manager uninstall job.
    legacy.rename(archive)
    print('Previous KDE package preserved at ' + str(archive), file=sys.stderr)


def prepare(source, data_home):
    source = Path(source)
    target = Path(data_home) / 'kwin-wayland/effects/switchinator'
    if target.is_symlink():
        raise RuntimeError('Refusing to write through an effect-directory symlink at ' + str(target))
    metadata = target / 'metadata.json'
    if target.exists() and (not metadata.exists() or
            json.loads(metadata.read_text())['KPlugin']['Id'] != 'switchinator'):
        raise RuntimeError('Refusing to replace an unrelated effect at ' + str(target))
    ui = source / 'contents/ui'
    digest = hashlib.sha256()
    for file in sorted(ui.rglob("*")):
        if file.is_file():
            digest.update(file.relative_to(ui).as_posix().encode()); digest.update(file.read_bytes())
    revision = digest.hexdigest()[:20]
    target.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source / 'metadata.json', metadata)
    shutil.copytree(source / 'contents/config', target / 'contents/config', dirs_exist_ok=True)
    runtime = target / 'contents/ui/runtime' / revision
    shutil.copytree(ui, runtime, dirs_exist_ok=True)
    # The preferred kwin-wayland URL also bypasses the old cached entry point
    # under kwin/effects when migrating from installations before this loader.
    shutil.copy2(ui / 'main.qml', target / 'contents/ui/main.qml')
    shutil.copy2(ui / 'config.ui', target / 'contents/ui/config.ui')
    archive_legacy(data_home)
    return revision


if __name__ == '__main__':
    data = os.environ.get('XDG_DATA_HOME', str(Path.home() / '.local/share'))
    print(prepare(sys.argv[1], data))
