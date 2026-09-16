import importlib.util
from pathlib import Path
import tempfile
import unittest

path=Path(__file__).resolve().parents[1]/'tools/kde_shortcuts.py'
spec=importlib.util.spec_from_file_location('kde_shortcuts',path)
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)

class ShortcutTests(unittest.TestCase):
    def test_bind_backup_and_restore(self):
        actions=[['kwin',name,'KWin',name] for name in ['Walk Through Windows','Walk Through Windows (Reverse)','SwitchinatorForward','SwitchinatorBackward']]
        state={tuple(a[:2]):keys for a,keys in zip(actions,[[module.ALT_TAB],[module.ALT_SHIFT_TAB],[module.META_TAB],[module.META_SHIFT_TAB]])}
        def call(method,*args):
            import json
            if method=='allActionsForComponent':return actions
            if method=='action':return next((a for a in actions if int(args[0]) in state[tuple(a[:2])]),[])
            action=json.loads(args[0]);key=tuple(action[:2])
            if method=='shortcut':return list(reversed(state[key])) or [0]
            if method=='setShortcut':state[key]=json.loads(args[1]);return list(reversed(state[key])) or [0]
            if method=='setForeignShortcut':return None
            raise AssertionError(method)
        original={key:value.copy() for key,value in state.items()}
        old_call,old_backup=module.call,module.BACKUP
        try:
            with tempfile.TemporaryDirectory() as directory:
                module.call=call;module.BACKUP=Path(directory)/'bindings.json'
                module.setup()
                self.assertEqual(state[('kwin','Walk Through Windows')],[])
                self.assertIn(module.ALT_TAB,state[('kwin','SwitchinatorForward')])
                backup=module.BACKUP.read_text();module.setup()
                self.assertEqual(module.BACKUP.read_text(),backup)
                module.restore();self.assertEqual(state,original)
        finally:module.call=old_call;module.BACKUP=old_backup

    def test_failed_assignment_restores_existing_bindings(self):
        import json
        actions=[['kwin',name,'KWin',name] for name in ['Walk Through Windows','SwitchinatorForward','SwitchinatorBackward']]
        state={tuple(a[:2]):keys for a,keys in zip(actions,[[module.ALT_TAB],[module.META_TAB],[module.META_SHIFT_TAB]])}
        original={key:value.copy() for key,value in state.items()}
        rejected=False
        def call(method,*args):
            nonlocal rejected
            if method=='allActionsForComponent':return actions
            if method=='action':return next((a for a in actions if int(args[0]) in state[tuple(a[:2])]),[])
            action=json.loads(args[0]);key=tuple(action[:2])
            if method=='shortcut':return state[key].copy()
            if method=='setShortcut':
                keys=json.loads(args[1])
                if not rejected and action[1]=='SwitchinatorForward' and module.ALT_TAB in keys:
                    rejected=True
                    raise RuntimeError('Simulated shortcut rejection')
                state[key]=keys;return keys.copy()
            if method=='setForeignShortcut':return None
            raise AssertionError(method)
        old_call,old_backup=module.call,module.BACKUP
        try:
            with tempfile.TemporaryDirectory() as directory:
                module.call=call;module.BACKUP=Path(directory)/'bindings.json'
                with self.assertRaisesRegex(RuntimeError,'Simulated'):module.setup()
                self.assertEqual(state,original)
        finally:module.call=old_call;module.BACKUP=old_backup

if __name__=='__main__':unittest.main()
