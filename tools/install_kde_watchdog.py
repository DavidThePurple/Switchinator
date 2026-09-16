#!/usr/bin/env python3
"""Install and start the recovery service before taking over Alt+Tab."""
import os
from pathlib import Path
import shutil
import subprocess


def install():
    data = Path(os.environ.get('XDG_DATA_HOME', Path.home() / '.local/share'))
    config = Path(os.environ.get('XDG_CONFIG_HOME', Path.home() / '.config'))
    target = data / 'switchinator/recovery'
    target.mkdir(parents=True, exist_ok=True)
    for name in ('kde_watchdog.py', 'kde_shortcuts.py'):
        shutil.copy2(Path(__file__).with_name(name), target / name)
    # A fixed launcher location keeps the service independent of the checkout.
    unit = config / 'systemd/user/switchinator-watchdog.service'
    unit.parent.mkdir(parents=True, exist_ok=True)
    script = str(target / 'kde_watchdog.py')
    if '\n' in script or '\r' in script:
        raise RuntimeError('Unsupported newline in recovery directory')
    script = script.replace('\\', '\\\\').replace('"', '\\"').replace('%', '%%').replace('$', '$$')
    config_value = str(config).replace('\\', '\\\\').replace('"', '\\"').replace('%', '%%')
    if '\n' in config_value or '\r' in config_value:
        raise RuntimeError('Unsupported newline in configuration directory')
    unit.write_text('[Unit]\nDescription=Switchinator input recovery\n'
        'After=graphical-session-pre.target\nPartOf=graphical-session.target\n\n'
        '[Service]\nType=simple\nEnvironment="XDG_CONFIG_HOME=' + config_value + '"\n'
        'ExecStart=/usr/bin/python3 "' + script + '"\n'
        'Restart=on-failure\nRestartSec=5\n\n[Install]\nWantedBy=graphical-session.target\n')
    subprocess.run(['systemctl', '--user', 'daemon-reload'], check=True)
    subprocess.run(['systemctl', '--user', 'enable', 'switchinator-watchdog.service'], check=True)
    subprocess.run(['systemctl', '--user', 'restart', 'switchinator-watchdog.service'], check=True)
    subprocess.run(['systemctl', '--user', 'is-active', '--quiet', 'switchinator-watchdog.service'], check=True)


if __name__ == '__main__':
    install()
