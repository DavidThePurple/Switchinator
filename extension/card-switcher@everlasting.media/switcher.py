#!/usr/bin/python3
import sys, time, math, json, os, re, hashlib
from pathlib import Path
from PyQt5 import QtCore, QtGui, QtWidgets
from Xlib import X, XK, display, protocol
from Xlib.ext import composite

def circular_delta(value,center,count):
    if count<2:return 0.0
    delta=value-center
    while delta>count/2:delta-=count
    while delta<-count/2:delta+=count
    return delta

def carousel_pose(index,scroll,count):
    offset=circular_delta(index,scroll,count)
    step=min(48,82/max(1,count//2))
    angle=offset*step
    depth=max(0,math.cos(math.radians(angle)))
    return angle,depth

class AutoRotation:
    def __init__(self):
        self.enabled=False;self.delay=5;self.next_at=0;self.order=[];self.custom=False
    def configure(self,enabled,delay,now):
        delay=max(1,float(delay))
        if enabled!=self.enabled or delay!=self.delay:self.next_at=now+delay
        self.enabled=bool(enabled);self.delay=delay
    def set_sequence(self,sequence,now):
        self.order=list(dict.fromkeys(sequence));self.custom=bool(self.order);self.next_at=now+self.delay
    def next_window(self,windows,active,now,paused=False):
        if not self.enabled:return None
        if paused:self.next_at=now+self.delay;return None
        live=set(windows)
        self.order=[wid for wid in self.order if wid in live]
        if not self.custom:self.order.extend(wid for wid in windows if wid not in self.order)
        if now<self.next_at:return None
        self.next_at=now+self.delay
        if not self.order:return None
        index=(self.order.index(active)+1)%len(self.order) if active in self.order else 0
        target=self.order[index]
        return target if target!=active else None

class Switcher(QtWidgets.QWidget):
    def __init__(self):
        super().__init__(None, QtCore.Qt.FramelessWindowHint | QtCore.Qt.Tool | QtCore.Qt.X11BypassWindowManagerHint | QtCore.Qt.WindowStaysOnTopHint)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.setAttribute(QtCore.Qt.WA_ShowWithoutActivating)
        self.x = display.Display(); self.root = self.x.screen().root
        self.atoms = {};self.redirected=set();self.last_prime=0;self.preview_cache={}
        self.rotation=AutoRotation();self.sequence_draft=None;self.last_config_check=0
        self.items=[]; self.index=0; self.progress=0; self.phase='hidden'; self.scales=[]
        self.tab=self.x.keysym_to_keycode(XK.string_to_keysym('Tab'))
        self.alts={self.x.keysym_to_keycode(XK.string_to_keysym(k)) for k in ('Alt_L','Alt_R')}
        for extra in (0,X.LockMask,X.Mod2Mask,X.LockMask|X.Mod2Mask):
            for shift in (0,X.ShiftMask): self.root.grab_key(self.tab,X.Mod1Mask|extra|shift,False,X.GrabModeAsync,X.GrabModeAsync)
        self.x.sync()
        self.timer=QtCore.QTimer(self);self.timer.timeout.connect(self.tick);self.timer.start(16)
        self.started=0;self.scroll=0;self.configfile=Path(sys.argv[sys.argv.index('--config')+1]) if '--config' in sys.argv else None;self.config={}
        self.loadconfig();self.prime_windows()
    def loadconfig(self):
        try:
            if self.configfile:self.config=json.loads(self.configfile.read_text())
        except Exception:pass
    def color(self,key,default):
        value=self.config.get(key,default)
        match=re.fullmatch(r'rgba?\(([^)]+)\)',str(value))
        if match:
            parts=[float(v.strip()) for v in match.group(1).split(',')]
            c=QtGui.QColor(int(parts[0]),int(parts[1]),int(parts[2]),int(parts[3]*255) if len(parts)>3 else 255)
        else:c=QtGui.QColor(value)
        return c if c.isValid() else QtGui.QColor(default)
    def duration(self,key,default):
        return max(.05,float(self.config.get(key,default))/1000)
    def atom(self,n):
        if n not in self.atoms:self.atoms[n]=self.x.intern_atom(n)
        return self.atoms[n]
    def prop(self,w,n):
        try:
            p=w.get_full_property(self.atom(n),X.AnyPropertyType)
            return p.value if p else None
        except Exception:return None
    def native_path(self,w):
        if not self.config.get('native_dir'):return None
        name=self.prop(w,'_NET_WM_NAME')
        title=(bytes(name).decode('utf-8','replace') if name is not None else w.get_wm_name()) or 'Untitled'
        return Path(self.config['native_dir'])/(hashlib.sha256(title.encode()).hexdigest()+'.png')
    def capture(self,w):
        now=time.monotonic()
        cached=self.preview_cache.get(w.id)
        if cached and now-cached[0]<5:return cached[1]
        pix=self.capture_uncached(w)
        if not pix.isNull():self.preview_cache[w.id]=(now,pix)
        return pix
    def capture_uncached(self,w):
        path=self.native_path(w)
        if path and path.exists():
            pix=QtGui.QPixmap(str(path))
            if not pix.isNull():return pix
        if w.get_attributes().map_state != X.IsViewable:
            return QtGui.QPixmap()
        self.prime_window(w)
        return self.capture_pixmap(w)
    def prime_window(self,w):
        if w.id in self.redirected:return
        path=self.native_path(w)
        if path and path.exists():return
        errors=[]
        w.composite_redirect_window(composite.RedirectAutomatic,onerror=lambda error,request: errors.append(error) or True)
        self.x.sync()
        if not errors:self.redirected.add(w.id)
    def prime_windows(self):
        ids=self.prop(self.root,'_NET_CLIENT_LIST')
        if ids is None:return
        live=set(map(int,ids))
        self.redirected.intersection_update(live)
        self.preview_cache={wid:value for wid,value in self.preview_cache.items() if wid in live}
        for wid in ids:
            try:
                w=self.x.create_resource_object('window',int(wid))
                if w.get_attributes().map_state==X.IsViewable:self.prime_window(w)
            except Exception:pass
    def capture_pixmap(self,w):
        target=w
        for attempt in range(1):
            pixmap=None; errors=[]
            try:
                pixmap=target.composite_name_window_pixmap(onerror=lambda error,request: errors.append(error) or True)
                self.x.sync()
                if errors:
                    pixmap=None
                    raise RuntimeError('Window has no compositor pixmap')
                geometry=pixmap.get_geometry()
                position=target.translate_coords(w,0,0)
                client=w.get_geometry()
                left=max(0,position.x);top=max(0,position.y)
                width=min(client.width,geometry.width-left);height=min(client.height,geometry.height-top)
                if width<=0 or height<=0:raise RuntimeError('Empty capture')
                image=pixmap.get_image(left,top,width,height,X.ZPixmap,0xffffffff)
                formats=self.x.display.info.pixmap_formats
                fmt=next(f for f in formats if f.depth==image.depth)
                if fmt.bits_per_pixel!=32:raise RuntimeError('Unsupported pixel format')
                stride=((width*fmt.bits_per_pixel+fmt.scanline_pad-1)//fmt.scanline_pad)*(fmt.scanline_pad//8)
                qimage=QtGui.QImage(image.data,width,height,stride,(QtGui.QImage.Format_ARGB32_Premultiplied if image.depth==32 else QtGui.QImage.Format_RGB32)).copy()
                return QtGui.QPixmap.fromImage(qimage).scaled(1200,800,QtCore.Qt.KeepAspectRatio,QtCore.Qt.SmoothTransformation)
            except Exception:
                try:
                    parent=target.query_tree().parent
                    if parent.id==self.root.id:break
                    target=parent
                except Exception:break
            finally:
                if pixmap:pixmap.free(onerror=lambda error,request: True)
        return QtGui.QPixmap()
    def collect(self,with_previews=True):
        ids=self.prop(self.root,'_NET_CLIENT_LIST_STACKING');active=self.prop(self.root,'_NET_ACTIVE_WINDOW')
        ids=list(ids) if ids is not None else []
        if active is not None and int(active[0]) in ids:ids.remove(int(active[0]));ids.append(int(active[0]))
        items=[]
        exclude={self.atom(n) for n in ('_NET_WM_WINDOW_TYPE_DOCK','_NET_WM_WINDOW_TYPE_DESKTOP','_NET_WM_WINDOW_TYPE_NOTIFICATION')}
        for wid in reversed(ids):
            try:
                w=self.x.create_resource_object('window',int(wid));types=self.prop(w,'_NET_WM_WINDOW_TYPE')
                if types is not None and exclude.intersection(map(int,types)):continue
                states=self.prop(w,'_NET_WM_STATE')
                if states is not None and self.atom('_NET_WM_STATE_SKIP_TASKBAR') in states:continue
                name=self.prop(w,'_NET_WM_NAME')
                title=(bytes(name).decode('utf-8','replace') if name is not None else w.get_wm_name()) or 'Untitled'
                if title=='Card Switcher':continue
                g=w.get_geometry();pos=self.root.translate_coords(w,0,0)
                rect=QtCore.QRect(pos.x,pos.y,g.width,g.height)
                screen=QtWidgets.QApplication.screenAt(rect.center()) or QtWidgets.QApplication.primaryScreen()
                pix=self.capture(w) if with_previews else QtGui.QPixmap()
                items.append({'id':int(wid),'title':title,'rect':rect,'pix':pix})
            except Exception:continue
        return items
    def begin(self,back=False):
        self.loadconfig();self.sequence_draft=None
        if self.config.get('native_dir'):
            try:
                Path(self.config['native_dir'],'capture-request').write_text(str(time.monotonic()))
                QtCore.QTimer.singleShot(350,self.refresh_native_previews)
            except OSError:pass
        self.items=self.collect()
        if not self.items:return
        self.index=(len(self.items)-1 if back else min(1,len(self.items)-1))
        pointer=QtGui.QCursor.pos();s=QtWidgets.QApplication.screenAt(pointer) or QtWidgets.QApplication.primaryScreen()
        self.host=s.availableGeometry()
        geo=QtCore.QRect()
        for s in QtWidgets.QApplication.screens():geo=geo.united(s.geometry())
        self.setGeometry(geo);self.origin=geo.topLeft()
        self.card_size=max(.6,min(2,float(self.config.get('preview_size',100))/100))
        self.card_size=min(self.card_size,(self.host.height()-100)/186)
        self.selection_scale=max(1,min(3.5,float(self.config.get('selected_scale',1.16)),(self.host.height()-110)/(230*self.card_size),(self.host.width()-60)/(290*self.card_size)))
        self.selection_margin=230*self.card_size*self.selection_scale/2+35
        self.spacing=270*self.card_size
        self.panelheight=max(220,186*self.card_size+84)
        self.rowwidth=min(self.host.width()-48,max(340,len(self.items)*self.spacing+70))
        self.cx=max(self.host.left()+self.rowwidth/2+16,min(pointer.x(),self.host.right()-self.rowwidth/2-16))-geo.x()
        self.cy=max(self.host.top()+self.selection_margin,min(pointer.y(),self.host.bottom()-self.selection_margin))-geo.y()
        self.scales=[1.0]*len(self.items);self.tilts=[0.0]*len(self.items);self.tilt_selected=None;self.scroll=float(self.index);self.progress=0;self.started=time.monotonic();self.phase='row'
        self.last_damage=QtCore.QRect()
        self.show();self.raise_()
        self.root.grab_keyboard(False,X.GrabModeAsync,X.GrabModeAsync,X.CurrentTime);self.x.flush()
    def refresh_native_previews(self):
        if self.phase!='row':return
        for item in self.items:
            try:
                path=self.native_path(self.x.create_resource_object('window',item['id']))
                if path and path.exists():
                    pix=QtGui.QPixmap(str(path))
                    if not pix.isNull():
                        item['pix']=pix
                        self.preview_cache[item['id']]=(time.monotonic(),pix)
            except Exception:pass
        self.last_render=None
        self.repaint_cards()
    def finish(self,cancel=False):
        if self.phase!='row':return
        self.x.ungrab_keyboard(X.CurrentTime);self.x.flush()
        if cancel:
            self.sequence_draft=None;self.hide();self.phase='hidden';self.rotation.next_at=time.monotonic()+self.rotation.delay;return
        if self.sequence_draft is not None:
            self.rotation.set_sequence(self.sequence_draft,time.monotonic())
            if self.sequence_draft:
                self.index=next((i for i,item in enumerate(self.items) if item['id']==self.sequence_draft[0]),self.index)
            self.sequence_draft=None
        if not self.config.get('animations_enabled',True):
            self.activate();return
        self.source=self.cardrect(self.index);self.phase='finish';self.started=time.monotonic()
    def activate(self):
        item=self.items[self.index]
        self.activate_window(item['id'])
        self.hide();self.phase='hidden';self.rotation.next_at=time.monotonic()+self.rotation.delay
    def activate_window(self,wid):
        try:
            w=self.x.create_resource_object('window',wid)
            ev=protocol.event.ClientMessage(window=w,client_type=self.atom('_NET_ACTIVE_WINDOW'),data=(32,[2,X.CurrentTime,0,0,0]))
            self.root.send_event(ev,event_mask=X.SubstructureRedirectMask|X.SubstructureNotifyMask);self.x.flush()
        except Exception:pass
    def alt_held(self):
        keys=self.x.query_keymap()
        return any(keys[k//8]&(1<<(k%8)) for k in self.alts)
    def automation_tick(self):
        now=time.monotonic()
        if now-self.last_config_check>=.5:
            self.loadconfig();self.last_config_check=now
            self.rotation.configure(self.config.get('auto_rotate',False),self.config.get('rotation_delay',5),now)
        if not self.rotation.enabled:return
        if self.phase!='hidden' or self.alt_held():
            self.rotation.next_at=now+self.rotation.delay;return
        if now<self.rotation.next_at:return
        windows=[item['id'] for item in self.collect(False)]
        active=self.prop(self.root,'_NET_ACTIVE_WINDOW')
        target=self.rotation.next_window(windows,int(active[0]) if active is not None else None,now)
        if target is not None:self.activate_window(target)
    def mousePressEvent(self,event):
        if self.phase!='row' or not self.alt_held():return
        if event.button()==QtCore.Qt.RightButton:
            self.sequence_draft=[];self.last_render=None;self.repaint_cards();return
        if event.button()!=QtCore.Qt.LeftButton:return
        panel=QtCore.QRectF(self.cx-self.rowwidth/2,self.cy-self.panelheight/2,self.rowwidth,self.panelheight)
        order=[self.index]+[i for i in reversed(range(len(self.items))) if i!=self.index]
        for i in order:
            rect=self.cardrect(i)
            if i!=self.index:rect=rect.intersected(panel)
            hit=rect.contains(event.localPos())
            if getattr(self,'config',{}).get('window_layout','flat')=='carousel':
                polygon=self.cardtransform(i,self.cardrect(i)).map(QtGui.QPolygonF(self.cardrect(i)))
                hit=polygon.containsPoint(event.localPos(),QtCore.Qt.OddEvenFill)
            if not hit:continue
            self.index=i
            if self.rotation.enabled:
                if self.sequence_draft is None:self.sequence_draft=[]
                wid=self.items[i]['id']
                if wid not in self.sequence_draft:self.sequence_draft.append(wid)
            self.last_render=None;self.repaint_cards();break
    def tick(self):
        self.automation_tick()
        if self.phase=='hidden' and time.monotonic()-self.last_prime>.5:
            self.prime_windows();self.last_prime=time.monotonic()
        try:
            while self.x.pending_events():
                e=self.x.next_event()
                if e.type==X.KeyPress:
                    if e.detail==self.tab:
                        if self.phase=='hidden':self.begin(bool(e.state&X.ShiftMask))
                        elif self.phase=='row':self.index=(self.index+(-1 if e.state&X.ShiftMask else 1))%len(self.items)
                    elif self.phase=='row' and e.detail==self.x.keysym_to_keycode(XK.string_to_keysym('Escape')):self.finish(True)
                elif e.type==X.KeyRelease and e.detail in self.alts:self.finish()
        except Exception as e:print('Input:',e,flush=True)
        if self.phase=='row':
            animated=self.config.get('animations_enabled',True)
            self.progress=min(1,(time.monotonic()-self.started)/self.duration('open_ms',240)) if animated else 1
            if self.config.get('window_layout','flat')=='carousel':
                self.scroll=(self.scroll+circular_delta(self.index,self.scroll,len(self.items))*(.18 if animated else 1))%len(self.items)
            else:self.scroll+=(self.index-self.scroll)*(.18 if animated else 1)
            for i in range(len(self.scales)):self.scales[i]+=((self.selection_scale if i==self.index else 1)-self.scales[i])*(.22 if animated else 1)
            if self.tilt_selected!=self.index:
                self.tilt_selected=self.index;self.tilt_started=time.monotonic();self.tilt_from=self.tilts[self.index]
            for i in range(len(self.tilts)):
                target=0.0
                if animated and i==self.index and self.config.get('selected_style','tilt')=='tilt':
                    strength=float(self.config.get('style_strength',6))
                    age=time.monotonic()-self.tilt_started
                    if age<1.0:
                        t=min(1,age/1.0);ease=t*t*(3-2*t)
                        target=self.tilt_from+(-strength-self.tilt_from)*ease
                    else:
                        target=-strength*math.cos((age-1.0)*2.6)
                    self.tilts[i]=target
                else:
                    self.tilts[i]+=(target-self.tilts[i])*(.10 if animated else 1)
            if os.environ.get('CARD_SWITCHER_TRACE'):
                Path('/tmp/card-switcher-tilt-trace.jsonl').open('a').write(json.dumps({'index':self.index,'age':time.monotonic()-self.tilt_started,'angle':self.tilts[self.index]})+'\n')
            # Release can occur before keyboard grab completes.
            keys=self.x.query_keymap()
            if not any(keys[k//8]&(1<<(k%8)) for k in self.alts):self.finish()
            self.repaint_cards()
        elif self.phase=='finish':
            self.progress=min(1,(time.monotonic()-self.started)/self.duration('finish_ms',360))
            self.update()
            if self.progress>=1:self.activate()
    def repaint_cards(self):
        signature=(self.index,self.progress,self.scroll,tuple(self.scales),self.config.get('window_layout','flat'))
        if not self.config.get('animations_enabled',True) and getattr(self,'last_render',None)==signature:return
        self.last_render=signature
        # Damage only the row and the transformed selected card, not every display.
        panel=QtCore.QRectF(self.cx-self.rowwidth/2,self.cy-self.panelheight/2,self.rowwidth,self.panelheight)
        selected=self.cardrect(self.index)
        radius=math.hypot(selected.width(),selected.height())*.6+32
        center=selected.center()
        bounds=panel.united(QtCore.QRectF(center.x()-radius,center.y()-radius,radius*2,radius*2))
        bounds=bounds.intersected(QtCore.QRectF(self.host.translated(-self.origin))).toAlignedRect()
        old=getattr(self,'last_damage',QtCore.QRect())
        self.last_damage=bounds
        self.update(bounds.united(old))
    def cardrect(self,i):
        scale=self.scales[i]
        if self.config.get('window_layout','flat')=='carousel' and self.phase=='row':
            angle,depth=carousel_pose(i,self.scroll,len(self.items))
            scale*=.66+.34*depth
            w=244*self.card_size*scale;h=186*self.card_size*scale
            radius=min(self.host.width()*.35,244*self.card_size*(1.45+min(len(self.items),8)*.12))
            x=self.cx+math.sin(math.radians(angle))*radius-w/2
            y=self.cy-h/2+(1-depth)*186*self.card_size*.2
            return QtCore.QRectF(x,y,w,h)
        w=244*self.card_size*scale;h=186*self.card_size*scale
        return QtCore.QRectF(self.cx+(i-self.scroll)*self.spacing-w/2,self.cy-h/2,w,h)
    def cardtransform(self,i,r):
        transform=QtGui.QTransform()
        if self.config.get('window_layout','flat')!='carousel' or self.phase!='row':return transform
        angle,_=carousel_pose(i,self.scroll,len(self.items));center=r.center()
        transform.translate(center.x(),center.y());transform.rotate(-angle*.82,QtCore.Qt.YAxis);transform.translate(-center.x(),-center.y())
        return transform
    def card(self,p,item,r,selected=False,opacity=1):
        p.save();p.setOpacity(opacity)
        i=next((i for i,v in enumerate(self.items) if v is item),None)
        if i is not None:p.setWorldTransform(self.cardtransform(i,r),True)
        if hasattr(self,'tilts') and self.config.get('selected_style','tilt')=='tilt':
            if i is not None:
                angle=self.tilts[i]*(1-self.progress if self.phase=='finish' else 1)
                center=r.center();p.translate(center);p.rotate(angle);p.translate(-center)
        path=QtGui.QPainterPath();path.addRoundedRect(r,16,16)
        p.fillPath(path,self.color('secondary','#202735'))
        preview=r.adjusted(8,8,-8,-38)
        if not item['pix'].isNull():
            pix=item['pix'];fit=QtCore.QSizeF(pix.size());fit.scale(preview.size(),QtCore.Qt.KeepAspectRatio)
            target=QtCore.QRectF(preview.center().x()-fit.width()/2,preview.center().y()-fit.height()/2,fit.width(),fit.height())
            p.save();p.setClipPath(path,QtCore.Qt.IntersectClip);p.drawPixmap(target,pix,QtCore.QRectF(pix.rect()));p.restore()
        else:
            p.setPen(QtGui.QColor('#899bb8'));p.drawText(preview,QtCore.Qt.AlignCenter,'Minimized · preview unavailable')
        p.setBrush(QtCore.Qt.NoBrush);p.setPen(QtGui.QPen(self.color('accent','#79b8ff') if selected else self.color('border','#384253'),3 if selected else 1));p.drawPath(path)
        p.setFont(QtGui.QFont('Sans',10));p.setPen(self.color('text','#edf3ff'))
        sequence=self.sequence_draft if self.sequence_draft is not None else (self.rotation.order if self.rotation.custom else [])
        if self.phase=='row' and self.rotation.enabled and item['id'] in sequence:
            badge=QtCore.QRectF(r.right()-38,r.top()+10,26,26)
            p.setBrush(self.color('accent','#79b8ff'));p.setPen(QtCore.Qt.NoPen);p.drawEllipse(badge)
            p.setPen(self.color('text','#edf3ff'));p.drawText(badge,QtCore.Qt.AlignCenter,str(sequence.index(item['id'])+1))
        title=QtGui.QFontMetrics(p.font()).elidedText(item['title'],QtCore.Qt.ElideRight,int(r.width()-24))
        p.drawText(r.adjusted(12,r.height()-32,-12,-8),QtCore.Qt.AlignVCenter,title);p.restore()
    def selected_card(self,p,fade):
        r=self.cardrect(self.index);center=r.center();p.save()
        if self.config.get('animations_enabled',True):
            style=self.config.get('selected_style','tilt');strength=float(self.config.get('style_strength',6));elapsed=time.monotonic()-self.started
            angle=0;dy=0;zoom=1
            if style=='tilt':angle=0
            elif style=='sway':angle=math.sin(elapsed*2.4)*strength
            elif style=='float':dy=math.sin(elapsed*2.2)*strength*1.5
            elif style=='pulse':zoom=1+math.sin(elapsed*2.8)*strength*.004
            p.translate(center.x(),center.y()+dy);p.rotate(angle);p.scale(zoom,zoom);p.translate(-center.x(),-center.y())
        self.card(p,self.items[self.index],r,True,fade);p.restore()
    def paintEvent(self,e):
        if self.phase=='hidden':return
        p=QtGui.QPainter(self);p.setRenderHint(QtGui.QPainter.Antialiasing);p.setRenderHint(QtGui.QPainter.SmoothPixmapTransform)
        if self.phase=='row':
            fade=1-(1-self.progress)**3
            panel=QtCore.QRectF(self.cx-self.rowwidth/2,self.cy-self.panelheight/2,self.rowwidth,self.panelheight)
            if self.config.get('show_background',False):
                p.save();p.setOpacity(fade);p.setBrush(self.color('primary','#0c111a'))
                if self.config.get('window_layout','flat')=='carousel':
                    radius=min(self.host.width()*.35,244*self.card_size*(1.45+min(len(self.items),8)*.12))
                    base=QtCore.QRectF(self.cx-radius-244*self.card_size*.4,self.cy+186*self.card_size*.43,radius*2+244*self.card_size*.8,34)
                    pen=QtGui.QPen(self.color('accent','#79b8ff'));pen.setWidthF(2);p.setPen(pen);p.drawRoundedRect(base,17,17)
                else:p.setPen(QtCore.Qt.NoPen);p.drawRoundedRect(panel,22,22)
                p.restore()
            p.save();p.setClipRect(panel.adjusted(10,8,-10,-8))
            order=range(len(self.items))
            if self.config.get('window_layout','flat')=='carousel':order=sorted(order,key=lambda i:carousel_pose(i,self.scroll,len(self.items))[1])
            for i in order:
                rect=self.cardrect(i)
                if i!=self.index and rect.intersects(panel):
                    depth=carousel_pose(i,self.scroll,len(self.items))[1] if self.config.get('window_layout','flat')=='carousel' else .6
                    self.card(p,self.items[i],rect,False,fade*(.55+.45*depth))
            p.restore()
            p.save();p.setClipRect(QtCore.QRectF(self.host.translated(-self.origin)))
            self.selected_card(p,fade);p.restore()
        else:
            t=1-(1-self.progress)**3;dest=QtCore.QRectF(self.items[self.index]['rect'].translated(-self.origin))
            r=QtCore.QRectF(*[a+(b-a)*t for a,b in zip((self.source.x(),self.source.y(),self.source.width(),self.source.height()),(dest.x(),dest.y(),dest.width(),dest.height()))])
            self.card(p,self.items[self.index],r,True,1-max(0,(self.progress-.8)/.2))
    def closeEvent(self,e):
        self.x.ungrab_keyboard(X.CurrentTime);self.x.close();e.accept()

if __name__=='__main__':
    app=QtWidgets.QApplication(sys.argv);app.setQuitOnLastWindowClosed(False)
    w=Switcher();w.setWindowTitle('Card Switcher')
    print('Card Switcher ready',flush=True)
    sys.exit(app.exec_())
