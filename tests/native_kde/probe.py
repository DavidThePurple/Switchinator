import os, sys, time, subprocess, json
from pathlib import Path
sys.path.insert(0,'/tmp/protocols')
sys.path.insert(0,'/app/tools')
from pywayland.client import Display
from fake_input import OrgKdeKwinFakeInput
from PyQt6.QtGui import QGuiApplication
from PyQt6.QtQml import QQmlEngine, QQmlComponent
from PyQt6.QtCore import QUrl
from prepare_kde_runtime import prepare
import kde_shortcuts

app=QGuiApplication([]);engine=QQmlEngine();components=[];windows=[]
for title,color in [('ProbeA','red'),('ProbeB','blue')]:
 c=QQmlComponent(engine);c.setData(('import QtQuick; import QtQuick.Window; Window {visible:true;width:640;height:480;title:"'+title+'";Rectangle {anchors.fill:parent;color:"'+color+'"}}').encode(),QUrl())
 assert not c.isError(),[e.toString() for e in c.errors()]
 components.append(c);windows.append(c.create())
focus=[]
app.focusWindowChanged.connect(lambda w:focus.append(w.title() if w else None))
def pump(seconds):
 end=time.monotonic()+seconds
 while time.monotonic()<end: app.processEvents();time.sleep(.01)
def dbus(path,method,*args):
 return subprocess.run(['gdbus','call','--session','--dest','org.kde.KWin','--object-path',path,'--method',method,*args],capture_output=True,text=True,check=True,timeout=5).stdout

def active():
 return "'switchinator'" in dbus('/Effects','org.freedesktop.DBus.Properties.Get','org.kde.kwin.Effects','activeEffects')
def wait_state(value,seconds=3):
 end=time.monotonic()+seconds
 while time.monotonic()<end:
  pump(.03)
  if active()==value:return True
 return False

display=Display();display.connect();registry=display.get_registry();inputs=[]
def global_handler(registry,name,interface,version):
 if interface==OrgKdeKwinFakeInput.name:
  inputs.append(registry.bind(name,OrgKdeKwinFakeInput,min(version,OrgKdeKwinFakeInput.version)))
registry.dispatcher['global']=global_handler;display.roundtrip();assert inputs,'Fake input protocol not offered'
fake=inputs[0];fake.authenticate('Switchinator isolated probe','Native lifecycle regression');display.roundtrip()
def key(code,state,delay=.08):
 fake.keyboard_key(code,state);display.flush();pump(delay)
pump(1)
revision=prepare('/app/kde/switchinator',Path.home()/'.local/share')
for group,name,value in [('Plugins','switchinatorEnabled','false'),('Effect-switchinator','RuntimeRevision',revision),('Effect-switchinator','AutoRotate','false')]:
 subprocess.run(['kwriteconfig6','--file','kwinrc','--group',group,'--key',name,value],check=True)
dbus('/KWin','org.kde.KWin.reconfigure');print(dbus('/Effects','org.kde.kwin.Effects.loadEffect','switchinator'),flush=True)
kde_shortcuts.setup()
for iteration in range(15):
 key(56,1);key(15,1);key(15,0)
 assert wait_state(True),'Overlay did not open'
 key(56,0)
 if not wait_state(False):
  print('STUCK at iteration',iteration,'Focus:',focus[-8:],flush=True)
  print(Path('/tmp/kwin.log').read_text()[-12000:],flush=True)
  sys.exit(2)
 pump(.1)
 print('Native open/select/close:',iteration,'focus:',focus[-3:],flush=True)
print('Native repeated activation passed',flush=True)
for iteration in range(30):
 before=app.focusWindow().title()
 for code,state in [(56,1),(15,1),(15,0),(56,0)]:
  fake.keyboard_key(code,state)
 display.flush();pump(.5)
 if active():
  print('FAST TAP STUCK at iteration',iteration,flush=True)
  print(Path('/tmp/kwin.log').read_text()[-6000:],flush=True)
  sys.exit(3)
 assert app.focusWindow().title()!=before,('Quick tap failed to focus next window',iteration,focus[-5:])
 print('Native quick tap selected and closed:',iteration,flush=True)
# Release at varying points in asynchronous view creation.
for delay in [0,.002,.005,.015,.03,.06]*3:
 before=app.focusWindow().title()
 key(56,1,0);key(15,1,0);key(15,0,delay);key(56,0,0)
 assert wait_state(False),'Release during view creation trapped input'
 pump(.35)
 assert not active(),'Delayed view creation reopened the overlay'
 assert app.focusWindow().title()!=before,'Early release failed to select next window'
print('Native release-during-incubation timing cases passed',flush=True)
# Reload in the same compositor/QQmlEngine with a new content hash.
import shutil
source=Path.home()/'upgrade-probe'
shutil.rmtree(source,ignore_errors=True);shutil.copytree('/app/kde/switchinator',source)
runtime=source/'contents/ui/Runtime.qml';runtime.write_text(runtime.read_text()+'\n// isolated upgrade probe\n')
revision=prepare(source,Path.home()/'.local/share')
dbus('/Effects','org.kde.kwin.Effects.unloadEffect','switchinator')
subprocess.run(['kwriteconfig6','--file','kwinrc','--group','Effect-switchinator','--key','RuntimeRevision',revision],check=True)
dbus('/KWin','org.kde.KWin.reconfigure');dbus('/Effects','org.kde.kwin.Effects.loadEffect','switchinator')
for iteration in range(5):
 key(56,1);key(15,1);key(15,0)
 assert wait_state(True),'Reloaded overlay did not open'
 key(56,0);assert wait_state(False),'Reloaded overlay trapped input'
print('Native same-engine upgrade and repeated selection passed',flush=True)
# Exercise the actual independent watchdog, with only its deadline shortened.
log=open('/tmp/watchdog-probe.log','w')
watcher=subprocess.Popen([sys.executable,'-c',
 'import sys;sys.path.insert(0,"/app/tools");import kde_watchdog as w;D=w.Deadline;w.Deadline=lambda:D(2);w.monitor()'],stdout=log,stderr=log)
try:
 key(56,1);key(15,1);key(15,0)
 assert wait_state(True),'Watchdog test overlay did not open'
 assert wait_state(False,9),'External watchdog did not unload native input grab'
 key(56,0);pump(.3)
 assert "'switchinator'" not in dbus('/Effects','org.freedesktop.DBus.Properties.Get','org.kde.kwin.Effects','loadedEffects')
 assert 'original shortcuts restored' in Path('/tmp/watchdog-probe.log').read_text(),Path('/tmp/watchdog-probe.log').read_text()
 before=app.focusWindow().title()
 key(56,1);key(15,1);key(15,0);key(56,0);pump(.3)
 assert app.focusWindow().title()!=before,'Restored native Alt+Tab did not focus another window'
 print('Native external watchdog unloaded grab and restored working Alt+Tab',flush=True)
finally:
 watcher.terminate();watcher.wait(timeout=3);log.close()
for w in windows:w.close()
pump(.2)
