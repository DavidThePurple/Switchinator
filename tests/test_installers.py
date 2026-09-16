import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]

class InstallerTests(unittest.TestCase):
    def route(self,desktop,session='x11',extra=()):
        env=dict(os.environ,XDG_CURRENT_DESKTOP=desktop,XDG_SESSION_TYPE=session,XDG_SESSION_DESKTOP='')
        return subprocess.run([str(ROOT/'install.sh'),*extra,'--dry-run'],env=env,capture_output=True,text=True)
    def test_routes_without_loading_other_backend(self):
        self.assertIn('cinnamon',self.route('X-Cinnamon').stdout)
        self.assertIn('kde',self.route('KDE','wayland').stdout)
        self.assertNotEqual(self.route('gamescope','wayland').returncode,0)
        self.assertNotEqual(self.route('Cinnamon','wayland').returncode,0)
        self.assertIn('kde',self.route('unknown','wayland',('--backend','kde')).stdout)
    def test_kde_package_install_does_not_touch_cinnamon(self):
        with tempfile.TemporaryDirectory() as directory:
            directory=Path(directory);commands=directory/'bin';commands.mkdir()
            marker=directory/'data/cinnamon/extensions/original';marker.parent.mkdir(parents=True);marker.write_text('keep')
            log=directory/'calls'
            (commands/'kwin_wayland').write_text('#!/bin/sh\necho "kwin 6.4.3"\n')
            (commands/'kpackagetool6').write_text('#!/bin/sh\nprintf "%s\\n" "$*" >> "$SWITCHINATOR_TEST_LOG"\ncase "$*" in *--show*) exit 1;; esac\n')
            (commands/'gdbus').write_text("""#!/bin/sh
printf '%s\n' "$*" >> "$SWITCHINATOR_TEST_LOG"
case "$*" in
 *Properties.Get*)
  if [ -f "$SWITCHINATOR_TEST_STATE" ];then echo "(<['switchinator']>,)";else echo "(<[]>,)";fi ;;
 *unloadEffect*) rm -f "$SWITCHINATOR_TEST_STATE";echo '()' ;;
 *loadEffect*)
  if [ "${SWITCHINATOR_TEST_FAIL:-0}" = 1 ];then echo '(false,)';else touch "$SWITCHINATOR_TEST_STATE";echo '(true,)';fi ;;
esac
""")
            (commands/'kwriteconfig6').write_text('#!/bin/sh\nprintf "%s\\n" "$*" >> "$SWITCHINATOR_TEST_LOG"\n')
            (commands/'python3').write_text('#!/bin/sh\nprintf "%s\\n" "$*" >> "$SWITCHINATOR_TEST_LOG"\n')
            for command in commands.iterdir():command.chmod(0o755)
            env=dict(os.environ,PATH=str(commands)+':'+os.environ['PATH'],XDG_DATA_HOME=str(directory/'data'),SWITCHINATOR_TEST_LOG=str(log),SWITCHINATOR_TEST_STATE=str(directory/'loaded'))
            result=subprocess.run([str(ROOT/'install-kde.sh')],env=env,capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertEqual(marker.read_text(),'keep')
            self.assertIn('--type KWin/Effect --install',log.read_text())
            self.assertNotIn('cinnamon',log.read_text())
            self.assertIn('loadEffect',log.read_text())
            self.assertIn('--key switchinatorEnabled true',log.read_text())
            self.assertIn('installed and loaded',result.stdout)
            self.assertIn('kde_shortcuts.py',log.read_text())
            # A load failure must not print success or enable a broken effect.
            log.unlink();env['SWITCHINATOR_TEST_FAIL']='1'
            result=subprocess.run([str(ROOT/'install-kde.sh')],env=env,capture_output=True,text=True)
            self.assertNotEqual(result.returncode,0)
            self.assertIn('did not load',result.stderr)
            self.assertNotIn('installed and loaded',result.stdout)
            self.assertNotIn('switchinatorEnabled',log.read_text())
            # Unsupported KWin fails before the package manager can mutate anything.
            (commands/'kwin_wayland').write_text('#!/bin/sh\necho "kwin 6.2.5"\n');log.unlink()
            result=subprocess.run([str(ROOT/'install-kde.sh')],env=env,capture_output=True,text=True)
            self.assertNotEqual(result.returncode,0)
            self.assertFalse(log.exists())

if __name__=='__main__':unittest.main()
