import QtQuick
import org.kde.kwin as KWin
import "Logic.js" as Logic

KWin.SceneEffect {
    id: effect
    readonly property bool autoRotateEnabled: configuration.AutoRotate === true
    property var windows: []
    property var sequence: []
    property var draft: null
    property bool customSequence: false
    property int selected: 0
    property var pointer: Qt.point(0,0)
    property string host: ""
    property var snapshots: ({})
    property var captureQueue: []
    property bool captureBusy: false
    property bool returning: false
    property real returnProgress: 0
    property rect returnSource: Qt.rect(0,0,0,0)
    property rect returnDestination: Qt.rect(0,0,0,0)
    property var pendingActivation: null
    property var returnWindow: null
    property string returnKey: ""
    signal captureRequested(var client)

    function availableWindows() { return KWin.Workspace.stackingOrder.filter(Logic.eligible).reverse(); }
    function findWindow(id) {
        var live=availableWindows();
        for (var i=0;i<live.length;i++) if (Logic.key(live[i])===id) return live[i];
        return null;
    }
    function activate(client) {
        if (!client || client.deleted) return;
        client.minimized=false;
        if (!client.onAllDesktops && client.desktops.length) KWin.Workspace.currentDesktop=client.desktops[0];
        KWin.Workspace.activeWindow=client;
    }
    function begin(backward) {
        console.log("Switchinator: shortcut received",backward);
        if (visible) { cycle(backward);return; }
        windows=availableWindows();
        console.log("Switchinator: eligible windows",windows.length);
        if (!windows.length) return;
        pointer=KWin.Workspace.cursorPos;
        var output=KWin.Workspace.activeScreen;
        for (var i=0;i<KWin.Workspace.screens.length;i++)
            if (Logic.contains(KWin.Workspace.screens[i].geometry,pointer)) output=KWin.Workspace.screens[i];
        host=output.name;draft=null;returning=false;returnProgress=0;
        var active=windows.indexOf(KWin.Workspace.activeWindow);
        selected=((active<0 ? 0 : active)+(backward ? windows.length-1 : 1))%windows.length;
        captureQueue=windows.map(Logic.key);captureBusy=false;visible=true;
    }
    function cycle(backward) {
        if (!returning && windows.length) selected=(selected+(backward ? windows.length-1 : 1))%windows.length;
    }
    function choose(id) {
        if (!autoRotateEnabled) return;
        draft=Logic.append(draft===null ? [] : draft,id);
    }
    function cancel() {
        activateLater.stop();pendingActivation=null;returnAnimation.stop();draft=null;returnWindow=null;returning=false;
        captureQueue=[];visible=false;
    }
    function finishSelection() {
        var client=returnWindow;
        // Release KWin's scene/input grab before activating the real window.
        // An activation exception must never leave the overlay visible.
        returnAnimation.stop();visible=false;returning=false;captureQueue=[];
        pendingActivation=client;activateLater.restart();
    }
    function release(source) {
        if (returning || !windows.length) return;
        if (draft!==null) {
            sequence=draft.slice();customSequence=sequence.length>0;
            if (sequence.length) {
                for (var i=0;i<windows.length;i++) if (Logic.key(windows[i])===sequence[0]) selected=i;
            }
            draft=null;
        }
        returnWindow=windows[selected];returnKey=Logic.key(returnWindow);
        returnSource=source;returnDestination=returnWindow.frameGeometry;
        if (!configuration.Animations) {finishSelection();return;}
        returning=true;returnAnimation.restart();
    }
    function captureNext() {
        if (captureBusy || !captureQueue.length || returning) return;
        var id=captureQueue.shift();captureQueue=captureQueue.slice();
        var client=findWindow(id), cached=snapshots[id];
        if (!client || client.minimized || (cached && Date.now()-cached.time<5000)) return;
        captureBusy=true;captureRequested(client);
    }
    function captured(id,texture) {
        if (visible && texture && findWindow(id)) {
            var copy=Object.assign({},snapshots);
            copy[id]={texture:texture,time:texture.capturedAt};snapshots=copy;
        }
        captureBusy=false;
    }
    onVisibleChanged: if (!visible) {
        captureQueue=[];captureBusy=false;snapshots={};
    }
    SystemPalette { id: palette; colorGroup: SystemPalette.Active }
    property color primary: configuration.UseTheme ? palette.window : configuration.PrimaryColor
    property color secondary: configuration.UseTheme ? palette.button : configuration.SecondaryColor
    property color accent: configuration.UseTheme && !configuration.CustomAccent ? palette.highlight : configuration.AccentColor
    property color textColor: configuration.UseTheme ? palette.windowText : configuration.TextColor

    // The installer assigns Alt+Tab after backing up conflicting KWin shortcuts.
    KWin.ShortcutHandler {
        name: "SwitchinatorForward";text: "Switchinator: next window";sequence: "Meta+Tab"
        onActivated: effect.begin(false)
    }
    KWin.ShortcutHandler {
        name: "SwitchinatorBackward";text: "Switchinator: previous window";sequence: "Meta+Shift+Tab"
        onActivated: effect.begin(true)
    }
    Timer { interval: 150;repeat: true;running: effect.visible && effect.captureQueue.length>0;onTriggered: effect.captureNext() }
    Timer {
        interval: 8000;repeat: true;running: effect.visible && !effect.returning
        onTriggered: { if (effect.windows.length) effect.captureQueue=effect.captureQueue.concat([Logic.key(effect.windows[effect.selected])]); }
    }
    Timer {
        id: rotation
        interval: Math.max(1,effect.configuration.RotationDelay)*1000
        repeat: true;running: effect.autoRotateEnabled && !effect.visible
        onTriggered: {
            if (!effect.autoRotateEnabled || effect.visible) return;
            var live=effect.availableWindows();
            effect.sequence=Logic.nextOrder(effect.sequence,live,effect.customSequence);
            var target=Logic.nextTarget(effect.sequence,KWin.Workspace.activeWindow ? Logic.key(KWin.Workspace.activeWindow) : "");
            if (target!==null) effect.activate(effect.findWindow(target));
        }
    }
    NumberAnimation {
        id: returnAnimation;objectName: "ReturnAnimation";target: effect;property: "returnProgress";from: 0;to: 1
        duration: effect.configuration.FinishMs;easing.type: Easing.OutCubic
        onFinished: effect.finishSelection()
    }
    Timer {
        id: activateLater;interval: 20
        onTriggered: {
            var client=effect.pendingActivation;effect.pendingActivation=null;
            try {effect.activate(client);}
            catch(error) {console.warn("Switchinator: activation failed:",String(error));}
        }
    }
    // This runs on the effect itself, independent of focus and view key handlers.
    // A failed keyboard route cannot hold the desktop indefinitely.
    Timer {
        objectName: "SafetyExit";interval: 60000;running: effect.visible
        onTriggered: {console.warn("Switchinator: safety timeout closed the overlay");effect.cancel();}
    }
    Timer {
        objectName: "FinishGuard"
        interval: Math.max(50,effect.configuration.FinishMs)+1000
        running: effect.visible && effect.returning
        onTriggered: effect.finishSelection()
    }
    Connections {
        target: KWin.Workspace
        function onWindowRemoved(client) {
            var id=Logic.key(client);var cache=Object.assign({},effect.snapshots);delete cache[id];effect.snapshots=cache;
            effect.windows=effect.windows.filter(function(w) {return Logic.key(w)!==id;});
            effect.selected=Math.min(effect.selected,Math.max(0,effect.windows.length-1));
            if (!effect.windows.length || effect.returnKey===id && effect.returning) effect.cancel();
        }
    }

    delegate: Item {
        id: scene
        readonly property var output: KWin.SceneView.screen
        readonly property rect geometry: output ? output.geometry : Qt.rect(0,0,1,1)
        readonly property bool isHost: output && output.name===effect.host
        readonly property real baseWidth: Math.min(244*effect.configuration.PreviewSize/100,width-40)
        readonly property real baseHeight: baseWidth*186/244
        readonly property real enlargement: Math.min(effect.configuration.SelectedScale,(height-80)/baseHeight,(width-60)/baseWidth)
        readonly property real spacing: baseWidth+26
        readonly property real rowWidth: Math.min(width-40,effect.windows.length*spacing)
        readonly property real centerX: Logic.clamp(effect.pointer.x-geometry.x,rowWidth/2+20,width-rowWidth/2-20)
        readonly property real centerY: Logic.clamp(effect.pointer.y-geometry.y,baseHeight*enlargement*.65+25,height-baseHeight*enlargement*.65-25)
        focus: isHost && !effect.returning
        clip: true
        // KWin clears its content item's focus after component completion.
        // Restore it on the next event-loop turn, after the view is installed.
        Component.onCompleted: focusRestore.start()
        onIsHostChanged: if (isHost) focusRestore.restart()
        Connections {
            target: effect
            function onVisibleChanged() {if(effect.visible) focusRestore.restart();}
        }
        function restoreInput() {
            if (!isHost || !effect.visible || effect.returning) return;
            // Focus the native KWin view first; item focus alone is insufficient
            // for its never-shown rendering window, especially across outputs.
            var view=effect.viewForScreen(scene.output);
            if (!view) {focusRestore.restart();return;}
            effect.activateView(view);
            scene.forceActiveFocus();
        }
        Timer {id: focusRestore; interval: 20; onTriggered: scene.restoreInput()}
        function acceptSelection() {
            var selectedCard=cards.itemAt(effect.selected);
            if (selectedCard) effect.release(selectedCard.globalRect());
            else effect.cancel();
        }
        // SceneEffect replaces the normal scene. Preserve the desktop, panels, and
        // visible windows at their actual coordinates on each output.
        Repeater {
            model: KWin.Workspace.stackingOrder
            delegate: KWin.WindowThumbnail {
                required property var modelData
                client: modelData || null
                readonly property rect frame: modelData ? modelData.frameGeometry : Qt.rect(0,0,0,0)
                x: frame.x-scene.geometry.x;y: frame.y-scene.geometry.y
                width: frame.width;height: frame.height
                visible: modelData && !modelData.deleted && !modelData.minimized && !modelData.hidden
                    && Logic.intersects(frame,scene.geometry)
                    && (modelData.onAllDesktops || modelData.desktops.indexOf(KWin.Workspace.currentDesktop)>=0)
            }
        }
        Keys.onPressed: function(event) {
            if (event.key===Qt.Key_Escape) {effect.cancel();event.accepted=true;}
            else if (event.key===Qt.Key_Return || event.key===Qt.Key_Enter) {scene.acceptSelection();event.accepted=true;}
            else if (event.key===Qt.Key_Tab || event.key===Qt.Key_Backtab) {effect.cycle(event.key===Qt.Key_Backtab || Boolean(event.modifiers & Qt.ShiftModifier));event.accepted=true;}
        }
        Keys.onReleased: function(event) {
            // Both modifiers are supported if the user changes the shortcut.
            if ((event.key===Qt.Key_Alt || event.key===Qt.Key_Meta) && !event.isAutoRepeat) {
                scene.acceptSelection();
                event.accepted=true;
            }
        }
        Rectangle {
            visible: scene.isHost && !effect.returning && effect.configuration.ShowBackground
            x: scene.centerX-scene.rowWidth/2;y: scene.centerY-scene.baseHeight/2-18
            width: scene.rowWidth;height: scene.baseHeight+36;radius: 22;color: effect.primary
        }
        Repeater {
            id: cards
            model: effect.visible && scene.isHost && !effect.returning ? effect.windows : []
            delegate: Rectangle {
                id: card
                required property int index
                required property var modelData
                readonly property bool selected: index===effect.selected
                readonly property var snapshot: effect.snapshots[Logic.key(modelData)]
                property real sizeScale: selected ? scene.enlargement : 1
                property real angle: 0
                x: scene.centerX+(index-effect.selected)*scene.spacing-width/2
                y: scene.centerY-height/2
                width: scene.baseWidth*sizeScale;height: scene.baseHeight*sizeScale
                color: effect.secondary;radius: 16;border.width: selected ? 3 : 1
                border.color: selected ? effect.accent : Qt.darker(effect.secondary,1.3)
                z: selected ? 100 : 1;rotation: angle
                visible: x+width>=scene.centerX-scene.rowWidth/2 && x<=scene.centerX+scene.rowWidth/2
                function globalRect() {return Qt.rect(scene.geometry.x+x,scene.geometry.y+y,width,height);}
                Behavior on x { NumberAnimation {duration: effect.configuration.Animations ? 180 : 0} }
                Behavior on sizeScale { NumberAnimation {duration: effect.configuration.Animations ? 220 : 0;easing.type: Easing.OutCubic} }
                onSelectedChanged: {rock.stop();entry.stop();angle=0;if(selected && effect.configuration.Animations && effect.configuration.SelectedStyle===1) entry.start();}
                opacity: effect.configuration.Animations ? 0 : 1
                Component.onCompleted: {
                    if(selected && effect.configuration.Animations && effect.configuration.SelectedStyle===1) entry.start();
                    if(effect.configuration.Animations) appear.start();
                }
                NumberAnimation {id: appear;target: card;property: "opacity";from: 0;to: 1;duration: effect.configuration.OpenMs;easing.type: Easing.OutCubic}
                NumberAnimation {id: entry;target: card;property: "angle";to: -effect.configuration.StyleStrength;duration: 1000;easing.type: Easing.InOutCubic;onFinished: if(card.selected) rock.start()}
                SequentialAnimation {
                    id: rock;loops: Animation.Infinite
                    NumberAnimation {target: card;property: "angle";to: effect.configuration.StyleStrength;duration: 1500;easing.type: Easing.InOutSine}
                    NumberAnimation {target: card;property: "angle";to: -effect.configuration.StyleStrength;duration: 1500;easing.type: Easing.InOutSine}
                }
                SequentialAnimation on angle {
                    running: card.selected && effect.configuration.Animations && effect.configuration.SelectedStyle===2;loops: Animation.Infinite
                    NumberAnimation {to: effect.configuration.StyleStrength;duration: 1400;easing.type: Easing.InOutSine}
                    NumberAnimation {to: -effect.configuration.StyleStrength;duration: 1400;easing.type: Easing.InOutSine}
                }
                transform: Translate {
                    id: floatOffset
                    SequentialAnimation on y {
                        running: card.selected && effect.configuration.Animations && effect.configuration.SelectedStyle===3;loops: Animation.Infinite
                        NumberAnimation {to: -effect.configuration.StyleStrength*1.5;duration: 1200;easing.type: Easing.InOutSine}
                        NumberAnimation {to: effect.configuration.StyleStrength*1.5;duration: 1200;easing.type: Easing.InOutSine}
                    }
                }
                SequentialAnimation on scale {
                    running: card.selected && effect.configuration.Animations && effect.configuration.SelectedStyle===4;loops: Animation.Infinite
                    NumberAnimation {to: 1+effect.configuration.StyleStrength*.004;duration: 1200;easing.type: Easing.InOutSine}
                    NumberAnimation {to: 1;duration: 1200;easing.type: Easing.InOutSine}
                }
                TexturePreview {anchors.fill: parent;anchors.margins: 9;anchors.bottomMargin: 36;source: card.snapshot ? card.snapshot.texture : null}
                Text {anchors.centerIn: parent;visible: !card.snapshot || !card.snapshot.time;text: modelData.minimized ? "Minimized" : "Loading preview…";color: effect.textColor}
                Text {anchors.left: parent.left;anchors.right: parent.right;anchors.bottom: parent.bottom;anchors.margins: 12;text: modelData.caption;color: effect.textColor;elide: Text.ElideRight;font.pixelSize: 13}
                Rectangle {
                    readonly property var order: effect.draft!==null ? effect.draft : effect.customSequence ? effect.sequence : []
                    readonly property int position: order.indexOf(Logic.key(modelData))
                    visible: effect.autoRotateEnabled && position>=0
                    width: 26;height: 26;radius: 13;color: effect.accent;anchors.right: parent.right;anchors.top: parent.top;anchors.margins: 10
                    Text {anchors.centerIn: parent;text: parent.position+1;color: effect.textColor}
                }
                MouseArea {
                    objectName: "PreviewMouse-"+card.index
                    anchors.fill: parent;acceptedButtons: Qt.LeftButton | Qt.RightButton
                    onClicked: function(mouse) {
                        if (mouse.button===Qt.RightButton) effect.draft=[];
                        else {
                            effect.selected=card.index;
                            if (effect.autoRotateEnabled) effect.choose(Logic.key(card.modelData));
                            else effect.release(card.globalRect());
                        }
                    }
                }
            }
        }
        Row {
            objectName: "ExitControls"
            visible: effect.visible && scene.isHost
            anchors.top: parent.top;anchors.right: parent.right;anchors.margins: 12
            spacing: 8;z: 10000
            Rectangle {
                width: 86;height: 36;radius: 10;color: effect.secondary
                visible: !effect.returning
                Text {anchors.centerIn: parent;text: "Select";color: effect.textColor}
                MouseArea {objectName: "SelectButton";anchors.fill: parent;onClicked: scene.acceptSelection()}
            }
            Rectangle {
                width: 86;height: 36;radius: 10;color: effect.secondary
                Text {anchors.centerIn: parent;text: "Close";color: effect.textColor}
                MouseArea {objectName: "CloseButton";anchors.fill: parent;onClicked: effect.cancel()}
            }
        }
        // Cache items live in the scene, independent of card delegates, so the
        // selected texture survives while the cards disappear for the exit animation.
        property var previewTextures: ({})
        Component {id: previewComponent;PreviewTexture {}}
        Connections {
            target: effect;enabled: scene.isHost
            function onCaptureRequested(client) {
                var id=Logic.key(client),texture=scene.previewTextures[id];
                if (!texture) {
                    texture=previewComponent.createObject(scene);
                    var copy=Object.assign({},scene.previewTextures);copy[id]=texture;scene.previewTextures=copy;
                    texture.captured.connect(function() {effect.captured(id,texture);});
                    texture.failed.connect(function() {effect.captureBusy=false;console.warn("Switchinator: preview capture timed out");});
                }
                if (!texture.capture(client)) effect.captureBusy=false;
            }
        }
        Rectangle {
            visible: effect.returning
            x: Logic.mix(effect.returnSource.x,effect.returnDestination.x,effect.returnProgress)-scene.geometry.x
            y: Logic.mix(effect.returnSource.y,effect.returnDestination.y,effect.returnProgress)-scene.geometry.y
            width: Logic.mix(effect.returnSource.width,effect.returnDestination.width,effect.returnProgress)
            height: Logic.mix(effect.returnSource.height,effect.returnDestination.height,effect.returnProgress)
            radius: 16*(1-effect.returnProgress);color: effect.secondary;z: 1000
            TexturePreview {anchors.fill: parent;source: effect.snapshots[effect.returnKey] ? effect.snapshots[effect.returnKey].texture : null}
        }
    }
}
