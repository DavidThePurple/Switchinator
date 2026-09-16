import importlib.util
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


def module(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'tools' / (name + '.py'))
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


class RecoveryTests(unittest.TestCase):
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


if __name__ == '__main__':
    unittest.main()
