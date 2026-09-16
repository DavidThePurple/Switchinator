# KDE modifier bridge

`InputState` observes KWin's keyboard-modifier signal before input filters run.
This covers Alt release before an asynchronous SceneEffect view exists, and
shortcut callbacks delivered after Alt is already released. It does not grab
input, poll windows, or render anything. The Cinnamon backend does not use it.

The bridge dynamically locates KWin's exported InputRedirection singleton,
validates its QObject class, and connects its reflected modifier signal. It
uses no KWin private headers or linked private methods, but the singleton
symbol and signal are implementation details. If either is unavailable, the
switcher refuses to open rather than taking an input grab without release
tracking. Native integration has been verified with KWin 6.4.3 on Wayland.

A prebuilt x86-64 Linux module is included in the KDE package. It requires
Qt 6.4 or newer and glibc 2.34 or newer; SteamOS installation needs no compiler
or changes to the system partition. The module was built with Qt 6.4.2 and
verified with Qt 6.4.2 and the newer Qt shipped alongside KWin 6.4.3.

To rebuild with Qt Core/QML development packages and CMake:

```sh
cmake -S native -B native/build -DCMAKE_BUILD_TYPE=Release
cmake --build native/build
cp native/build/libswitchinatorinput.so native/build/qmldir kde/switchinator/contents/ui/InputBridge/
```

Rebuild on the target architecture when it is not x86-64. Keep the QML plugin
in the content-addressed runtime: a global import directory would let KWin
reuse an old module across upgrades. Source and bundled module use the
repository's MIT license.
