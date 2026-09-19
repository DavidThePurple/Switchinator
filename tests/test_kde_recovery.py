import importlib.util
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]


def module(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'tools' / (name + '.py'))
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


class RecoveryTests(unittest.TestCase):
    def test_carousel_setting_is_declared_and_exposed(self):
        config = ET.parse(ROOT / 'kde/switchinator/contents/config/main.xml').getroot()
        entries = {entry.attrib['name']: entry for entry in config.iter() if entry.tag.endswith('entry')}
        self.assertEqual(entries['LayoutMode'].find('{http://www.kde.org/standards/kcfg/1.0}default').text, '0')
        ui = (ROOT / 'kde/switchinator/contents/ui/config.ui').read_text()
        self.assertIn('name="kcfg_LayoutMode"', ui)
        self.assertIn('<string>3D carousel</string>', ui)

    def test_service_is_independent_of_checkout_and_preserves_config_location(self):
        installer = module('install_kde_watchdog')
        with tempfile.TemporaryDirectory() as directory:
            directory = Path(directory)
            data, config = directory / 'data with spaces', directory / 'config'
            with patch.dict(os.environ, {'XDG_DATA_HOME': str(data), 'XDG_CONFIG_HOME': str(config)}), \
                 patch.object(installer.subprocess, 'run') as run:
                installer.install()
            unit = (config / 'systemd/user/switchinator-watchdog.service').read_text()
            self.assertIn(str(data / 'switchinator/recovery/kde_watchdog.py'), unit)
            self.assertNotIn(str(ROOT), unit)
            self.assertIn('XDG_CONFIG_HOME=' + str(config), unit)
            self.assertIn('After=graphical-session-pre.target', unit)
            self.assertTrue((data / 'switchinator/recovery/kde_shortcuts.py').exists())
            self.assertEqual(run.call_args.args[0], ['systemctl', '--user', 'is-active', '--quiet', 'switchinator-watchdog.service'])

    def test_watchdog_uses_native_activity_and_resets_between_openings(self):
        watchdog = module('kde_watchdog')
        deadline = watchdog.Deadline()
        self.assertFalse(deadline.expired(False, 10))
        self.assertFalse(deadline.expired(True, 20))
        self.assertFalse(deadline.expired(True, 79))
        self.assertTrue(deadline.expired(True, 80))
        self.assertFalse(deadline.expired(False, 81))
        self.assertFalse(deadline.expired(True, 100))
        self.assertFalse(deadline.expired(True, 159))
        self.assertTrue(deadline.expired(True, 160))

    def test_recovery_unloads_input_grab_before_restoring_shortcuts(self):
        watchdog = module('kde_watchdog')
        events = []
        with patch.object(watchdog.subprocess, 'run', side_effect=lambda *a, **kw: events.append(a[0])), \
             patch.object(watchdog, 'effect_call', side_effect=lambda *a: events.append(a)), \
             patch.object(watchdog, 'active', return_value=False):
            watchdog.recover()
        self.assertIn('switchinatorEnabled', events[0])
        self.assertEqual(events[1], ('org.kde.kwin.Effects.unloadEffect', 'switchinator'))
        self.assertIn('--restore', events[2])
        with patch.object(watchdog.subprocess, 'run'), patch.object(watchdog, 'effect_call'), \
             patch.object(watchdog, 'active', return_value=True):
            with self.assertRaisesRegex(RuntimeError, 'still reports'):
                watchdog.recover()

    def test_runtime_revisions_include_imported_files(self):
        prepare = module('prepare_kde_runtime')
        import shutil
        with tempfile.TemporaryDirectory() as directory:
            directory = Path(directory)
            source = directory / 'package'
            shutil.copytree(ROOT / 'kde/switchinator', source)
            first = prepare.prepare(source, directory / 'data')
            self.assertEqual(first, prepare.prepare(source, directory / 'data'))
            logic = source / 'contents/ui/Logic.js'
            logic.write_text(logic.read_text() + '\n// updated dependency\n')
            second = prepare.prepare(source, directory / 'data')
            self.assertNotEqual(first, second)
            runtime = directory / 'data/kwin-wayland/effects/switchinator/contents/ui/runtime'
            self.assertTrue((runtime / first / 'Runtime.qml').exists())
            self.assertTrue((runtime / second / 'Logic.js').exists())
            bridge = source / 'contents/ui/InputBridge/qmldir'
            bridge.write_text(bridge.read_text() + '\n# bridge update\n')
            third = prepare.prepare(source, directory / 'data')
            self.assertNotEqual(second, third)
            self.assertTrue((runtime / third / 'InputBridge/libswitchinatorinput.so').exists())

    def test_migration_preserves_legacy_files_and_repeated_install_succeeds(self):
        prepare = module('prepare_kde_runtime')
        import shutil
        with tempfile.TemporaryDirectory() as directory:
            directory = Path(directory)
            data = directory / 'data'
            source = directory / 'checkout/kde/switchinator'
            shutil.copytree(ROOT / 'kde/switchinator', source)
            legacy = data / 'kwin/effects/switchinator'
            shutil.copytree(source, legacy)
            (legacy / 'old-file').write_text('preserve')
            first = prepare.prepare(source, data)
            self.assertFalse(legacy.exists())
            backups = list((data / 'switchinator/backups').glob('legacy-*/switchinator'))
            self.assertEqual(len(backups), 1)
            self.assertEqual((backups[0] / 'old-file').read_text(), 'preserve')
            self.assertEqual(first, prepare.prepare(source, data))
            self.assertTrue((source / 'contents/ui/main.qml').exists())

    def test_migration_moves_legacy_symlink_without_touching_checkout(self):
        prepare = module('prepare_kde_runtime')
        import shutil
        with tempfile.TemporaryDirectory() as directory:
            directory = Path(directory)
            source = directory / 'checkout'
            shutil.copytree(ROOT / 'kde/switchinator', source)
            legacy = directory / 'data/kwin/effects/switchinator'
            legacy.parent.mkdir(parents=True)
            legacy.symlink_to(source, target_is_directory=True)
            prepare.prepare(source, directory / 'data')
            self.assertTrue((source / 'metadata.json').exists())
            backup = next((directory / 'data/switchinator/backups').glob('legacy-*/switchinator'))
            self.assertTrue(backup.is_symlink())


if __name__ == '__main__':
    unittest.main()
