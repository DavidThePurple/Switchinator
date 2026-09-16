"""Headless Qt 6 smoke test with mock KWin APIs; not a compositor integration test."""
import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
os.environ.setdefault('QT_QUICK_BACKEND','software')
from pathlib import Path
from PyQt6.QtCore import QUrl,QMetaObject,Q_ARG,QRectF
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
        QTest.qWait(600)
        self.assertEqual(len(effect.property('snapshots').toVariant()),2)
        configuration=effect.property('configuration').toVariant();configuration.update(AutoRotate=True,Animations=False)
        effect.setProperty('configuration',configuration)
        QMetaObject.invokeMethod(effect,'choose',Q_ARG('QVariant','first'))
        QMetaObject.invokeMethod(effect,'choose',Q_ARG('QVariant','second'))
        QMetaObject.invokeMethod(effect,'choose',Q_ARG('QVariant','first'))
        self.assertEqual(effect.property('draft').toVariant(),['first','second'])
        QMetaObject.invokeMethod(effect,'release',Q_ARG('QVariant',QRectF(500,300,400,300)))
        self.assertTrue(effect.property('customSequence'))
        self.assertEqual(effect.property('sequence').toVariant(),['first','second'])
        QMetaObject.invokeMethod(effect,'cancel')
        self.assertFalse(effect.property('visible'))
        self.assertEqual(warnings,[],"\n".join(warnings))
        window.close();scene.setParentItem(None);sip.delete(scene);sip.delete(window);sip.delete(effect);app.processEvents()

if __name__=='__main__':unittest.main()
