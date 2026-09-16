"""Headless Qt 6 smoke test with mock KWin APIs; not a compositor integration test."""
import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
os.environ.setdefault('QT_QUICK_BACKEND','software')
from pathlib import Path
from PyQt6.QtCore import QUrl,QMetaObject,Q_ARG,Qt
from PyQt6.QtGui import QGuiApplication
from PyQt6.QtQml import QQmlEngine,QQmlComponent
from PyQt6.QtQuick import QQuickWindow
from PyQt6.QtTest import QTest
from PyQt6 import sip
import unittest

class KdeQmlTests(unittest.TestCase):
    def test_effect_and_cards_load(self):
        root=Path(__file__).resolve().parents[1]
        app=QGuiApplication.instance() or QGuiApplication([])
        engine=QQmlEngine();warnings=[];engine.warnings.connect(lambda errors:warnings.extend(error.toString() for error in errors));engine.addImportPath(str(root/'tests/qml_stubs'))
        component=QQmlComponent(engine,QUrl.fromLocalFile(str(root/'kde/switchinator/contents/ui/main.qml')))
        self.assertFalse(component.isError(),'\n'.join(error.toString() for error in component.errors()))
        effect=component.create()
        self.assertIsNotNone(effect,'\n'.join(error.toString() for error in component.errors()))
        QMetaObject.invokeMethod(effect,'begin',Q_ARG('QVariant',False))
        self.assertTrue(effect.property('visible'))
        delegate=effect.property('delegate');scene=delegate.create(delegate.creationContext())
        self.assertIsNotNone(scene,'\n'.join(error.toString() for error in delegate.errors()))
        scene.setProperty('width',1920);scene.setProperty('height',1080)
        window=QQuickWindow();window.resize(1920,1080);scene.setParentItem(window.contentItem());window.show()
        # Reproduce KWin's focus clearing after installing the delegate.
        window.contentItem().setFocus(False)
        def pump(milliseconds): QTest.qWait(milliseconds)
        pump(600)
        self.assertTrue(scene.hasActiveFocus())
        self.assertEqual(len(effect.property('snapshots').toVariant()),2)
        configuration=effect.property('configuration').toVariant();configuration.update(AutoRotate=True,Animations=False,RotationDelay=1)
        effect.setProperty('configuration',configuration)
        QMetaObject.invokeMethod(effect,'choose',Q_ARG('QVariant','first'))
        QMetaObject.invokeMethod(effect,'choose',Q_ARG('QVariant','second'))
        QMetaObject.invokeMethod(effect,'choose',Q_ARG('QVariant','first'))
        self.assertEqual(effect.property('draft').toVariant(),['first','second'])
        QTest.keyRelease(window,Qt.Key.Key_Alt)
        self.assertFalse(effect.property('visible'))
        self.assertTrue(effect.property('customSequence'))
        self.assertEqual(effect.property('sequence').toVariant(),['first','second'])
        probe_component=QQmlComponent(engine)
        probe_component.setData(b'import QtQml; import org.kde.kwin as KWin; QtObject {property QtObject workspace: KWin.Workspace}',QUrl())
        probe=probe_component.create();workspace=probe.property('workspace')
        self.assertEqual(workspace.property('activeWindow'),workspace.property('first'))
        pump(1150)
        self.assertEqual(workspace.property('activeWindow'),workspace.property('second'))
        configuration.update(AutoRotate=False)
        effect.setProperty('configuration',configuration)
        # Cancel used to restart rotation even with the setting switched off.
        QMetaObject.invokeMethod(effect,'begin',Q_ARG('QVariant',False))
        QMetaObject.invokeMethod(effect,'cancel')
        before=workspace.property('activeWindow');pump(1150)
        self.assertEqual(workspace.property('activeWindow'),before)
        self.assertFalse(effect.property('visible'))
        # Exercise keyboard cancellation and the animated Alt-release path too.
        QMetaObject.invokeMethod(effect,'begin',Q_ARG('QVariant',False))
        QTest.keyClick(window,Qt.Key.Key_Escape)
        self.assertFalse(effect.property('visible'))
        configuration.update(Animations=True)
        effect.setProperty('configuration',configuration)
        QMetaObject.invokeMethod(effect,'begin',Q_ARG('QVariant',False))
        QTest.keyRelease(window,Qt.Key.Key_Alt)
        self.assertTrue(effect.property('returning'))
        pump(configuration['FinishMs']+80)
        self.assertFalse(effect.property('visible'))
        self.assertEqual(workspace.property('activeWindow'),workspace.property('first'))
        self.assertEqual(warnings,[],"\n".join(warnings))
        window.close();scene.setParentItem(None);sip.delete(scene);sip.delete(window);sip.delete(effect);sip.delete(probe);app.processEvents()

if __name__=='__main__':unittest.main()
