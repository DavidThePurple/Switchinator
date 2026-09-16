pragma Singleton
import QtQml
QtObject {
    property QtObject output: QtObject {property string name: "MockDisplay";property rect geometry: Qt.rect(0,0,1920,1080)}
    property var activeScreen: output
    property var screens: [output]
    property point cursorPos: Qt.point(960,540)
    property var stackingOrder: [first,second]
    property var activeWindow: first
    property var currentDesktop: null
    signal windowRemoved(var client)
    property QtObject first: QtObject {
        property string internalId: "first"
        property string caption: "First window"
        property rect frameGeometry: Qt.rect(20,30,800,600)
        property bool normalWindow: true
        property bool dialog: false
        property bool deleted: false
        property bool skipSwitcher: false
        property bool skipTaskbar: false
        property bool excludeFromCapture: false
        property bool minimized: false
        property bool hidden: false
        property bool onAllDesktops: true
        property var desktops: []
    }
    property QtObject second: QtObject {
        property string internalId: "second"
        property string caption: "Second window"
        property rect frameGeometry: Qt.rect(120,130,800,600)
        property bool normalWindow: true
        property bool dialog: false
        property bool deleted: false
        property bool skipSwitcher: false
        property bool skipTaskbar: false
        property bool excludeFromCapture: false
        property bool minimized: false
        property bool hidden: false
        property bool onAllDesktops: true
        property var desktops: []
    }
}
