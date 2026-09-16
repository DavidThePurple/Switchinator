"""Check frozen preview pixels in a real invisible Qt rendering window.

Run separately with PySide6 installed. System PyQt6 omits the
QQuickWindow(QQuickRenderControl*) constructor. KWin thumbnails are stubs;
this verifies Qt caching behavior, not KWin's native window texture provider.
"""
import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
os.environ.setdefault('QT_QUICK_BACKEND','software')
from pathlib import Path
from PySide6.QtCore import QUrl,QEvent
from PySide6.QtGui import QGuiApplication,QImage
from PySide6.QtQml import QQmlEngine,QQmlComponent
from PySide6.QtQuick import QQuickWindow,QQuickRenderControl,QQuickRenderTarget
from PySide6.QtTest import QTest

root=Path(__file__).resolve().parents[1]
app=QGuiApplication([])
engine=QQmlEngine();engine.addImportPath(str(root/'tests/qml_stubs'))
warnings=[];engine.warnings.connect(lambda errors:warnings.extend(error.toString() for error in errors))
component=QQmlComponent(engine)
component.setData(b'''import QtQuick
Item {
    width: 600; height: 450
    PreviewTexture {id: cache}
    function capture() {cache.capture({deleted:false,minimized:false});}
    function ready() {return cache.capturedAt>0 && cache.sourceItem.client===null && !cache.live;}
    function showCache() {cache.visible=true;}
    function time() {return cache.capturedAt;}
}''',QUrl.fromLocalFile(str(root/'kde/switchinator/contents/ui/render-test.qml')))
assert not component.isError(),component.errors()
scene=component.create();assert scene is not None,component.errors()
control=QQuickRenderControl();window=QQuickWindow(control);window.resize(600,450)
image=QImage(600,450,QImage.Format.Format_ARGB32_Premultiplied)
window.setRenderTarget(QQuickRenderTarget.fromPaintDevice(image));scene.setParentItem(window.contentItem())
def pump(milliseconds):
    for _ in range(milliseconds//20):
        QTest.qWait(20);control.polishItems();control.sync();control.render()
scene.capture();pump(300)
assert not window.isVisible()
assert scene.ready(),'Frozen texture did not complete and detach in the invisible window'
scene.showCache();pump(100)
assert image.pixelColor(100,100).name()=='#445566',image.pixelColor(100,100).name()
before=scene.time();scene.capture();pump(300)
assert scene.time()==before,'Five-second capture limit was ignored'
assert image.pixelColor(100,100).name()=='#445566','Frozen texture changed after its detached source became green'
assert not warnings,'\n'.join(warnings)
control.invalidate();scene.setParentItem(None)
for obj in [scene,component,window,control,engine]:obj.deleteLater()
app.sendPostedEvents(None,QEvent.Type.DeferredDelete)
app.processEvents()
print('Invisible rendering-window capture, detached frozen pixels and five-second limit passed')
