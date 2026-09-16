const Gio = imports.gi.Gio;
const GLib = imports.gi.GLib;
const St = imports.gi.St;
const Main = imports.ui.main;
const Settings = imports.ui.settings;
const Mainloop = imports.mainloop;
let metadata, settings, wm, previous, pid = 0, themeSignal = 0, active = false, captureTimer = 0, captureMonitor = null;
let options = {};
let prefetchCursor = 0;
let capturedAt = new Map();
function init(meta) { metadata = meta; }
function hex(c) { return '#' + [c.red,c.green,c.blue].map(v => v.toString(16).padStart(2,'0')).join(''); }
function themeColors() {
    let panel = new St.BoxLayout({style_class:'menu'});
    let item = new St.BoxLayout({style_class:'popup-menu-item'});
    panel.add_actor(item); Main.uiGroup.add_actor(panel);
    panel.opacity = 0;
    try {
        let bg = panel.get_theme_node().get_background_color();
        let fg = item.get_theme_node().get_foreground_color();
        let secondary = item.get_theme_node().get_background_color();
        let switcher = new St.BoxLayout({style_class:'switcher-list'});
        let selected = new St.BoxLayout({style_class:'item-box'});
        switcher.add_actor(selected);Main.uiGroup.add_actor(switcher);switcher.opacity=0;
        selected.add_style_pseudo_class('selected');
        let accent = selected.get_theme_node().get_background_color();
        switcher.destroy();
        return {primary:bg.alpha ? hex(bg) : '#202020',
                secondary:secondary.alpha ? hex(secondary) : '#' + [bg.red,bg.green,bg.blue].map(v=>Math.min(255,v+12).toString(16).padStart(2,'0')).join(''),
                text:hex(fg),accent:accent.alpha ? hex(accent) : '#79b8ff'};
    } finally { panel.destroy(); }
}
function captureSystemWindows(limit = 0) {
    let dir=GLib.build_filenamev([GLib.get_user_runtime_dir(),metadata.uuid]);
    GLib.mkdir_with_parents(dir,448);
    let actors=global.get_window_actors();
    let start=limit && actors.length ? prefetchCursor % actors.length : 0;
    let captured=0;
    for (let offset=0;offset<actors.length;offset++) {
        let index=(start+offset)%actors.length;
        let actor=actors[index];
        try {
            let win=actor.meta_window;
            if (!win) continue;
            let key=win.get_stable_sequence();
            let now=GLib.get_monotonic_time();
            if (now-(capturedAt.get(key)||0)<5000000) continue;
            let title=win.get_title() || '';
            let klass=win.get_wm_class() || '';
            if (!/cinnamon|nemo|gnome|mint|xed|xreader|xviewer/i.test(klass) && !/Extensions|System Settings/.test(title)) continue;
            if (win.minimized || !actor.mapped || actor.width<=0 || actor.height<=0) continue;
            // A mapped actor can still lack a backing texture during transitions.
            // Calling get_image then aborts CJS before JavaScript can catch it.
            let shaped=actor.get_texture();
            if (!shaped || !shaped.get_texture()) continue;
            // Budget GPU readbacks, including failed attempts, to one per prefetch.
            captured++;
            capturedAt.set(key,now);
            if (limit) prefetchCursor=(index+1)%actors.length;
            let surface=actor.get_image(null);
            if (!surface) {if(limit) break;continue;}
            let hash=GLib.compute_checksum_for_string(GLib.ChecksumType.SHA256,title,-1);
            let path=dir+'/'+hash+'.png';
            surface.writeToPNG(path+'.tmp');
            Gio.File.new_for_path(path+'.tmp').move(Gio.File.new_for_path(path),Gio.FileCopyFlags.OVERWRITE,null,null);
        } catch(e) { /* A window may disappear while capturing. */ }
        if (limit && captured>=limit) break;
    }
    return true;
}
function writeConfig() {
    let colors = {primary:options.primaryColor, secondary:options.secondaryColor,accent:options.accentColor,text:options.customText};
    if (options.useTheme) {
        try { colors = themeColors(); } catch(e) { global.logError(e); }
        if (options.customAccent) colors.accent = options.accentColor;
    }
    colors.auto_rotate=options.autoRotate;colors.rotation_delay=options.rotationDelay;
    colors.native_dir=GLib.build_filenamev([GLib.get_user_runtime_dir(),metadata.uuid]);
    colors.open_ms=options.openMs;colors.finish_ms=options.finishMs;colors.selected_scale=options.selectedScale;colors.preview_size=options.previewSize;colors.animations_enabled=options.animationsEnabled;colors.selected_style=options.selectedStyle;colors.style_strength=options.styleStrength;colors.show_background=options.showBackground;
    let dir=GLib.build_filenamev([GLib.get_user_config_dir(),metadata.uuid]);
    GLib.mkdir_with_parents(dir,448);
    GLib.file_set_contents(dir+'/appearance.json',JSON.stringify(colors));
    return dir+'/appearance.json';
}
function restoreBindings() {
    if (wm && previous) {
        for (let key of Object.keys(previous)) {
            // Respect a shortcut the user has changed while the extension ran.
            if (wm.get_strv(key).length === 0) wm.set_strv(key,previous[key]);
        }
        previous=null;
    }
}
function stopSwitcherProcesses() {
    let pattern='^/usr/bin/python3 '+metadata.path.replace(/[.*+?^${}()|[\]\\]/g,'\\$&')+'/switcher\\.py( |$)';
    GLib.spawn_sync(null,['/usr/bin/pkill','-f',pattern],null,GLib.SpawnFlags.SEARCH_PATH,null);
}
function enable() {
    stopSwitcherProcesses();
    active=true;
    settings=new Settings.ExtensionSettings(options,metadata.uuid);
    for (let [key,property] of [['use-theme','useTheme'],['primary-color','primaryColor'],['secondary-color','secondaryColor'],['accent-color','accentColor'],['custom-accent','customAccent'],['custom-text','customText'],['open-ms','openMs'],['finish-ms','finishMs'],['selected-scale','selectedScale'],['preview-size','previewSize'],['animations-enabled','animationsEnabled'],['selected-style','selectedStyle'],['style-strength','styleStrength'],['show-background','showBackground'],['auto-rotate','autoRotate'],['rotation-delay','rotationDelay']])
        settings.bindProperty(Settings.BindingDirection.IN,key,property,()=>{ if(active)writeConfig(); },null);
    wm=new Gio.Settings({schema_id:'org.cinnamon.desktop.keybindings.wm'});
    previous={};
    for(let key of ['switch-windows','switch-windows-backward']) {previous[key]=wm.get_strv(key);wm.set_strv(key,[]);}
    try {
        let config=writeConfig();
        // Full refresh on demand; background prefetch has a single-window budget.
        let nativeDir=GLib.build_filenamev([GLib.get_user_runtime_dir(),metadata.uuid]);
        GLib.mkdir_with_parents(nativeDir,448);
        captureMonitor=Gio.File.new_for_path(nativeDir).monitor_directory(Gio.FileMonitorFlags.NONE,null);
        captureMonitor.connect('changed',(_monitor,file)=>{
            if (file.get_basename()!=='capture-request' || !active) return;
            let request=nativeDir+'/capture-request';
            if (!GLib.file_test(request,GLib.FileTest.EXISTS)) return;
            GLib.unlink(request);
            captureSystemWindows();
        });
        prefetchCursor=0;
        capturedAt.clear();
        captureTimer=Mainloop.timeout_add(8000,()=>{captureSystemWindows(1);return true;});
        let result=GLib.spawn_async(metadata.path,['/usr/bin/python3',metadata.path+'/switcher.py','--config',config],null,GLib.SpawnFlags.DO_NOT_REAP_CHILD,null);
        pid=result[1];
        GLib.child_watch_add(GLib.PRIORITY_DEFAULT,pid,(child,status)=>{
            GLib.spawn_close_pid(child);
            if(pid===child) {pid=0;restoreBindings();if(active && status!==0)Main.notifyError('Card Switcher','The switcher stopped. Original Alt-Tab shortcuts have been restored.');}
        });
        themeSignal=St.ThemeContext.get_for_stage(global.stage).connect('changed',()=>writeConfig());
    } catch(e) {restoreBindings();global.logError(e);Main.notifyError('Card Switcher',String(e));}
}
function disable() {
    active=false;
    if(captureMonitor) {captureMonitor.cancel();captureMonitor=null;}
    if(captureTimer) {Mainloop.source_remove(captureTimer);captureTimer=0;}
    if(themeSignal) {St.ThemeContext.get_for_stage(global.stage).disconnect(themeSignal);themeSignal=0;}
    if(pid) {GLib.spawn_command_line_async('/bin/kill '+pid);pid=0;}
    stopSwitcherProcesses();
    restoreBindings();
    if(settings) {settings.finalize();settings=null;}
}
