# Native KWin regression test

This test runs a real KWin 6.4.3 compositor, real Wayland Qt windows and
KWin fake-input events. It does not use the mock KWin QML modules. Run it
only in a disposable Docker container with the repository mounted read-only
at `/app`; never mount host display sockets, GPUs or input devices.

The verified environment was the official `archlinux:base` image at digest
`sha256:204e91950fd364961088a01773eee9012243b7e965fed42b1d82d12416190782`,
with packages from `https://archive.archlinux.org/repos/2025/07/20/$repo/os/$arch`.
Set that URL as the container's pacman mirror and synchronize its packages
with `pacman -Syyuu --ignore base --overwrite '*' --noconfirm`. The ignored
`base` metapackage has an obsolete signing key in this snapshot. Signature
verification stays enabled; overwrite resolves old/new package file splits
inside the disposable container only.

Install these container packages:

```
kwin qt6-wayland qt6-tools mesa python-pywayland python-pyqt6
plasma-wayland-protocols kglobalacceld libcap
```

Prepare the container, as root:

```sh
setcap -r /usr/bin/kwin_wayland
useradd -m kwintest
mkdir /tmp/kwin-runtime
chown kwintest:kwintest /tmp/kwin-runtime
chmod 700 /tmp/kwin-runtime
python -m pywayland.scanner -i /usr/share/plasma-wayland-protocols/fake-input.xml -o /tmp/protocols
```

Removing the executable's scheduling capability avoids Docker's capability
restriction; it affects only this container. Then run:

```sh
runuser -u kwintest -- env SWITCHINATOR_ISOLATED_TEST=1 \
    dbus-run-session -- bash /app/tests/native_kde/session.sh
```

The session uses a virtual output and software Mesa. Fake-input permission
checks are disabled only inside this isolated compositor. The probe writes
only the container user's settings. It checks normal and rapid selection,
correct real-window focus, reload with a new runtime in the same compositor,
and the external watchdog unloading the effect and restoring usable native
Alt+Tab. Its watchdog deadline is shortened to two seconds in the test
process; the installed watchdog remains sixty seconds.

Before the modifier bridge, the first fully batched Alt-down/Tab/Alt-up sequence
left `activeEffects` containing Switchinator indefinitely. With the bridge,
the same test selects another real window and closes. On 2026-09-16 the native
run passed 15 normal cycles, 30 rapid cycles, 18 releases during asynchronous
view creation, five cycles after an in-session
upgrade, and watchdog recovery. This proves the tested software/input path,
not Steam Deck hardware, multi-monitor performance or an unresponsive KWin.
