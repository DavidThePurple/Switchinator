import QtQuick
import org.kde.kwin as KWin

// Keep this entry point stable: KWin retains it in its shared QML engine.
// Each installed runtime has its own content-addressed URL, including imports.
KWin.SceneEffect {
    id: nativeEffect
    property var runtime: null
    property string loadedRevision: ""
    delegate: runtime ? runtime.delegate : null
    onVisibleChanged: {
        console.log("Switchinator: native visibility",visible);
        if (runtime && runtime.visible!==visible) runtime.visible=visible;
    }
    Component.onCompleted: {
        var revision=configuration.RuntimeRevision || "";
        var path=revision ? "runtime/"+revision+"/Runtime.qml" : "Runtime.qml";
        var component=Qt.createComponent(Qt.resolvedUrl(path));
        if (component.status!==Component.Ready) {
            console.error("Switchinator: runtime load failed",path,component.errorString());
            return;
        }
        runtime=component.createObject(nativeEffect,{nativeEffect:nativeEffect});
        if (!runtime) {
            console.error("Switchinator: runtime creation failed",component.errorString());
            return;
        }
        loadedRevision=revision || "development";
        console.log("Switchinator: runtime loaded",loadedRevision);
    }
}
