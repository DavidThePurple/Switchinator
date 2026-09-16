#!/usr/bin/env python3
"""Recover a trapped switcher from outside KWin's QML/input event handling."""
import os
from pathlib import Path
import subprocess
import sys
import time


def effect_call(method, *args):
    return subprocess.run(['gdbus', 'call', '--session', '--dest', 'org.kde.KWin',
        '--object-path', '/Effects', '--method', method, *args],
        capture_output=True, text=True, check=True, timeout=5).stdout


def active():
    reply = effect_call('org.freedesktop.DBus.Properties.Get',
                        'org.kde.kwin.Effects', 'activeEffects')
    return "'switchinator'" in reply or '"switchinator"' in reply


def recover():
    # KWin's native destroyEffect() releases keyboard and mouse grabs, even
    # when the effect's own handlers and timers cannot close its scene.
    subprocess.run(['kwriteconfig6', '--file', 'kwinrc', '--group', 'Plugins',
                    '--key', 'switchinatorEnabled', 'false'], check=True, timeout=5)
    effect_call('org.kde.kwin.Effects.unloadEffect', 'switchinator')
    if active():
        raise RuntimeError('KWin still reports Switchinator active after unload')
    subprocess.run([sys.executable, str(Path(__file__).with_name('kde_shortcuts.py')),
                    '--restore'], check=True, timeout=20)
    print('Switchinator watchdog: trapped overlay unloaded; original shortcuts restored.', flush=True)


class Deadline:
    def __init__(self, seconds=60):
        self.seconds = seconds
        self.started = None

    def expired(self, is_active, now):
        if not is_active:
            self.started = None
            return False
        if self.started is None:
            self.started = now
        return now - self.started >= self.seconds


def monitor():
    deadline = Deadline()
    while True:
        try:
            if deadline.expired(active(), time.monotonic()):
                recover()
                deadline.started = None
        except (OSError, RuntimeError, subprocess.SubprocessError) as error:
            print('Switchinator watchdog:', error, file=sys.stderr, flush=True)
        time.sleep(2)


if __name__ == '__main__':
    if '--recover' in sys.argv:
        recover()
    else:
        monitor()
