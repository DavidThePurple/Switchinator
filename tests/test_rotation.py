import importlib.util
from pathlib import Path
from types import SimpleNamespace
import unittest
from PyQt5 import QtCore,QtGui

path=Path(__file__).resolve().parents[1]/'extension/card-switcher@everlasting.media/switcher.py'
spec=importlib.util.spec_from_file_location('switcher',path)
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)

class RotationTests(unittest.TestCase):
    def test_carousel_wraps_and_projects_side_cards(self):
        self.assertEqual(module.circular_delta(0,4,5),1)
        self.assertEqual(module.circular_delta(4,0,5),-1)
        center_angle,center_depth=module.carousel_pose(2,2,5)
        side_angle,side_depth=module.carousel_pose(4,2,5)
        self.assertEqual(center_angle,0);self.assertEqual(center_depth,1)
        self.assertGreater(side_angle,0);self.assertLess(side_depth,1)
        widget=SimpleNamespace(config={'window_layout':'carousel'},phase='row',scroll=2,items=[1,2,3,4,5])
        rect=QtCore.QRectF(100,100,244,186)
        transform=module.Switcher.cardtransform(widget,4,rect)
        mapped=transform.map(QtGui.QPolygonF(rect)).boundingRect()
        self.assertLess(mapped.width(),rect.width())

    def engine(self):
        engine=module.AutoRotation();engine.configure(True,5,0);return engine
    def test_default_order_delay_and_wrap(self):
        e=self.engine()
        self.assertIsNone(e.next_window([1,2,3],1,4.9))
        self.assertEqual(e.next_window([1,2,3],1,5),2)
        self.assertIsNone(e.next_window([2,1,3],2,6))
        self.assertEqual(e.next_window([2,1,3],2,10),3)
        self.assertEqual(e.next_window([3,2,1],3,15),1)
    def test_custom_order_skips_closed_windows(self):
        e=self.engine();e.set_sequence([3,1,3,2],0)
        self.assertEqual(e.order,[3,1,2])
        self.assertEqual(e.next_window([1,2,3,4],3,5),1)
        self.assertEqual(e.next_window([2,3,4],3,10),2)
        self.assertIsNone(e.next_window([4],2,15))
        self.assertEqual(e.next_at,20)
        self.assertEqual(e.order,[])
    def test_pause_and_disable(self):
        e=self.engine()
        self.assertIsNone(e.next_window([1,2],1,5,paused=True))
        self.assertIsNone(e.next_window([1,2],1,9))
        self.assertEqual(e.next_window([1,2],1,10),2)
        e.configure(False,5,11)
        self.assertIsNone(e.next_window([1,2],2,100))
    def test_new_windows_and_return_to_default(self):
        e=self.engine();e.set_sequence([2],0)
        self.assertIsNone(e.next_window([1,2,3],2,5))
        e.set_sequence([],6)
        self.assertEqual(e.next_window([1,2,3],1,11),2)
    def test_delay_change_and_empty_list_do_not_spin(self):
        e=self.engine();e.configure(True,10,3)
        self.assertIsNone(e.next_window([1,2],1,12))
        self.assertEqual(e.next_window([1,2],1,13),2)
        self.assertIsNone(e.next_window([],1,23))
        self.assertEqual(e.next_at,33)
    def test_clicks_record_order_and_reset(self):
        e=self.engine()
        w=SimpleNamespace(phase='row',alt_held=lambda:True,cx=200,cy=100,rowwidth=400,panelheight=200,index=0,
                          items=[{'id':10},{'id':20}],rotation=e,sequence_draft=None,
                          cardrect=lambda i:QtCore.QRectF(i*100,0,90,90),repaint_cards=lambda:None)
        def click(x,button=QtCore.Qt.LeftButton):
            module.Switcher.mousePressEvent(w,SimpleNamespace(button=lambda:button,localPos=lambda:QtCore.QPointF(x,40)))
        click(140);click(40);click(140)
        self.assertEqual(w.sequence_draft,[20,10])
        click(40,QtCore.Qt.RightButton)
        self.assertEqual(w.sequence_draft,[])
    def test_scheduler_never_requests_previews(self):
        e=self.engine();e.next_at=0;calls=[]
        w=SimpleNamespace(rotation=e,phase='hidden',last_config_check=module.time.monotonic(),alt_held=lambda:False,
            collect=lambda previews:calls.append(previews) or [{'id':1},{'id':2}],root=None,
            prop=lambda root,key:[1],activate_window=lambda wid:calls.append(wid))
        module.Switcher.automation_tick(w)
        self.assertEqual(calls,[False,2])

    def test_release_commits_order_and_selects_first(self):
        e=self.engine();calls=[]
        w=SimpleNamespace(phase='row',x=SimpleNamespace(ungrab_keyboard=lambda stamp:None,flush=lambda:None),
            rotation=e,sequence_draft=[20,10],items=[{'id':10},{'id':20}],index=0,
            config={'animations_enabled':False},activate=lambda:calls.append(w.items[w.index]['id']))
        module.Switcher.finish(w)
        self.assertEqual(e.order,[20,10]);self.assertEqual(calls,[20]);self.assertIsNone(w.sequence_draft)
    def test_escape_preserves_previous_order(self):
        e=self.engine();e.set_sequence([10,20],0)
        w=SimpleNamespace(phase='row',x=SimpleNamespace(ungrab_keyboard=lambda stamp:None,flush=lambda:None),
            rotation=e,sequence_draft=[30],hide=lambda:None)
        module.Switcher.finish(w,True)
        self.assertEqual(e.order,[10,20]);self.assertIsNone(w.sequence_draft);self.assertEqual(w.phase,'hidden')
    def test_activation_requests_target_without_live_focus(self):
        calls=[]
        x=SimpleNamespace(create_resource_object=lambda kind,wid:wid,flush=lambda:None)
        root=SimpleNamespace(send_event=lambda event,event_mask:calls.append((event,event_mask)))
        w=SimpleNamespace(x=x,root=root,atom=lambda name:123)
        module.Switcher.activate_window(w,42)
        self.assertEqual(len(calls),1)
        self.assertEqual(calls[0][0].window,42)
        self.assertEqual(calls[0][0].client_type,123)

if __name__=='__main__':unittest.main()
