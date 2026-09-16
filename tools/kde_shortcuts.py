#!/usr/bin/env python3
"""Configure only Switchinator's keys and their KWin owners; keep a restore record."""
import ast,json,os,re,subprocess,sys
from pathlib import Path

ALT_TAB=150994945
ALT_SHIFT_TAB=184549377
ALT_SHIFT_BACKTAB=184549378
META_TAB=285212673
META_SHIFT_TAB=318767105
BACKUP=Path(os.environ.get('XDG_CONFIG_HOME',Path.home()/'.config'))/'switchinator/kde-shortcuts.json'

def call(method,*args):
    result=subprocess.run(['gdbus','call','--session','--dest','org.kde.kglobalaccel','--object-path','/kglobalaccel',
                          '--method','org.kde.KGlobalAccel.'+method,*args],capture_output=True,text=True,check=True)
    text=re.sub(r'@[a-z()]+\s*','',result.stdout.strip())
    return ast.literal_eval(text)[0] if text not in ['()',''] else None

def shortcut(action):return call('shortcut',json.dumps(action))

def key_set(keys):
    # KDE stores bindings in a QSet; list order is unspecified. Zero means unbound.
    return {key for key in keys if key}

def assign(action,keys):
    actual=call('setShortcut',json.dumps(action),json.dumps(keys),'6') # SetPresent | NoAutoloading
    call('setForeignShortcut',json.dumps(action),json.dumps(actual)) # notify the running QAction owner
    if key_set(actual)!=key_set(keys):raise RuntimeError('KDE rejected a requested shortcut for '+action[1])
    if key_set(shortcut(action))!=key_set(keys):raise RuntimeError('Shortcut verification failed for '+action[1])

def setup():
    actions=call('allActionsForComponent',json.dumps(['kwin','','','']))
    by_name={action[1]:action for action in actions}
    for name in ['SwitchinatorForward','SwitchinatorBackward']:
        if name not in by_name:raise RuntimeError('KWin has not registered '+name+'; the effect did not initialize correctly.')
    changes={}
    for key in [ALT_TAB,ALT_SHIFT_TAB,ALT_SHIFT_BACKTAB]:
        owner=call('action',str(key))
        if not owner:continue
        if owner[0]!='kwin':raise RuntimeError('Alt+Tab is owned by another application; it was left unchanged.')
        if owner[1] not in ['SwitchinatorForward','SwitchinatorBackward']:
            changes[owner[1]]=(owner,[value for value in shortcut(owner) if value not in [ALT_TAB,ALT_SHIFT_TAB,ALT_SHIFT_BACKTAB]])
    changes['SwitchinatorForward']=(by_name['SwitchinatorForward'],[ALT_TAB,META_TAB])
    changes['SwitchinatorBackward']=(by_name['SwitchinatorBackward'],[ALT_SHIFT_TAB,META_SHIFT_TAB])
    original=[{'action':action,'keys':shortcut(action)} for action,_ in changes.values()]
    BACKUP.parent.mkdir(mode=0o700,parents=True,exist_ok=True)
    # Retain the original bindings across reinstallations; include newly affected actions.
    saved=json.loads(BACKUP.read_text()) if BACKUP.exists() else []
    names={tuple(entry['action'][:2]) for entry in saved}
    saved.extend(entry for entry in original if tuple(entry['action'][:2]) not in names)
    with BACKUP.open('w') as out:os.chmod(BACKUP,0o600);json.dump(saved,out,indent=2)
    try:
        for action,keys in changes.values():assign(action,keys)
    except Exception:
        # Release the new keys before restoring their original owners.
        for action,_ in changes.values():
            try:assign(action,[])
            except Exception:pass
        for entry in original:assign(entry['action'],entry['keys'])
        raise
    print('Alt+Tab and Shift+Alt+Tab assigned to Switchinator. Backup:',BACKUP)

def restore():
    saved=json.loads(BACKUP.read_text())
    for entry in saved:assign(entry['action'],[])
    for entry in saved:assign(entry['action'],entry['keys'])
    print('Original KDE shortcuts restored.')

if __name__=='__main__':
    try:restore() if '--restore' in sys.argv else setup()
    except (OSError,ValueError,RuntimeError,subprocess.CalledProcessError) as error:
        if isinstance(error,subprocess.CalledProcessError):print(error.stderr.strip(),file=sys.stderr)
        print('Shortcut setup failed:',error,file=sys.stderr);sys.exit(1)
