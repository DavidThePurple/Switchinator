import QtQuick

Item {
    id: preview
    property var source: null
    ShaderEffect {
        property var source: preview.source
        anchors.centerIn: parent
        width: Math.min(parent.width,parent.height*600/450)
        height: width*450/600
    }
}
