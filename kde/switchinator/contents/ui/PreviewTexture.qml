import QtQuick
import org.kde.kwin as KWin

// A frozen GPU texture works inside KWin's invisible QQuickRenderControl window.
ShaderEffectSource {
    id: preview
    width: 600; height: 450
    // Render the cache node during capture, underneath the desktop scene.
    // Otherwise an unreferenced invisible texture is never initialized.
    visible: pending
    z: -1000
    live: false
    hideSource: true
    sourceItem: thumbnail
    textureSize: Qt.size(600,450)
    property bool pending: false
    property bool scheduled: false
    property real capturedAt: 0
    signal captured()
    signal failed()

    function capture(client) {
        if (pending || !client || client.deleted || client.minimized) return false;
        if (capturedAt && Date.now()-capturedAt<5000) return false;
        pending=true;scheduled=false;thumbnail.client=client;
        // KWin produces a thumbnail on its next compositor frame. Warm it up
        // before freezing it; do not detach the client until the texture is ready.
        warmup.restart();watchdog.restart();
        return true;
    }
    function abort() {
        warmup.stop();watchdog.stop();
        pending=false;scheduled=false;thumbnail.client=null;
    }
    onScheduledUpdateCompleted: {
        if (!pending || !scheduled) return;
        capturedAt=Date.now();abort();captured();
    }
    KWin.WindowThumbnail {id: thumbnail; width: 600; height: 450; client: null}
    Timer {id: warmup; interval: 100; onTriggered: {preview.scheduled=true;preview.scheduleUpdate();}}
    Timer {id: watchdog; interval: 1500; onTriggered: {preview.abort();preview.failed();}}
}
