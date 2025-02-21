from typing import List, Dict, Callable, Any
from pyri.webui_browser.plugins.panel import PyriWebUIBrowserPanelBase
from pyri.webui_browser import PyriWebUIBrowser
import importlib_resources
import js
import traceback
from RobotRaconteur.Client import *
import base64
from pyri.webui_browser import util
from pyri.webui_browser.util import to_js2

class PyriCameraListPanel(PyriWebUIBrowserPanelBase):

    def __init__(self, core, device_manager):
        self.vue = None
        self.core = core
        self.device_manager = device_manager

    def init_vue(self,vue):
        self.vue = vue

    def camera_open(self, local_device_name):
        p = PyriCameraViewerPanel(local_device_name,self.core,self.device_manager)

    def camera_info(self, local_device_name):
        pass

    def camera_settings(self, local_device_name):
        pass

    def refresh_cameras_table(self,*args):
        try:
            cameras = util.get_devices_with_type(self.core,"com.robotraconteur.imaging.Camera")
                        
            getattr(self.vue,"$data").cameras = to_js2([{"local_device_name": d} for d in cameras])
        except:
            traceback.print_exc()

async def add_vision_panel(panel_type: str, core: PyriWebUIBrowser, parent_element: Any):

    print("#### add_vision_panel called")

    #assert panel_type == ""

    vision_panel_config = {
        "type": "stack",
        "componentName": "Vision",
        "componentState": {},
        "title": "Vision",
        "id": "vision",
        "isClosable": False
    }

    core.layout.register_component("vision",False)

    core.layout.add_panel(vision_panel_config)

    core.layout.add_panel_menu_item("vision", "Vision")

    camera_list_panel_html = importlib_resources.read_text(__package__,"cameras_panel.html")

    camera_list_panel_config = {
        "type": "component",
        "componentName": "camera_list",
        "componentState": {},
        "title": "Camera List",
        "id": "camera_list",
        "isClosable": False
    }

    def register_camera_list_panel(container, state):
        container.getElement().html(camera_list_panel_html)

    core.layout.register_component("camera_list",register_camera_list_panel)

    core.layout.layout.root.getItemsById("vision")[0].addChild(to_js2(camera_list_panel_config))

    camera_list_panel_obj = PyriCameraListPanel(core, core.device_manager)

    cameras_panel = js.Vue.new(to_js2({
        "el": "#cameras_table",
        "components": {
            "BootstrapTable": js.window.BootstrapTable
        },
        "data":
        {
            "cameras": [],
            "cameras_columns": [
                {
                    "field": "local_device_name",
                    "title": "Camera Device Name"
                },
                {
                    "field": "actions",
                    "title": "Actions",
                    "searchable": False,
                    "formatter": lambda a,b,c,d: """
                                                <a class="camera_list_open" title="Open Preview" @click="camera_open(c.local_device_name)"><i class="fas fa-2x fa-folder-open"></i></a>&nbsp;
                                                <a class="camera_list_info" title="Camera Info" @click="camera_info(c.local_device_name)"><i class="fas fa-2x fa-info-circle"></i></a>&nbsp;
                                                """
                                                #<a class="camera_lest_settings" title="Camera Settings" @click="camera_settings(c.local_device_name)"><i class="fas fa-2x fa-cog"></i></a>
                                                 ,
                    "events": {
                        "click .camera_list_open": lambda e, value, row, d: camera_list_panel_obj.camera_open(row.local_device_name),
                        "click .camera_list_info": lambda e, value, row, d: camera_list_panel_obj.camera_info(row.local_device_name)
                    }
                },                               
            ],
            "camera_list_options":
                {
                    "search": True,
                    "showColumns": False,
                    "showToggle": True,
                    "search": True,
                    "showSearchClearButton": True,
                    "showRefresh": False,
                    "cardView": True,
                    "toolbar": "#camera_list_toolbar"
                } 
        },
        "methods":
        {
            "camera_open": camera_list_panel_obj.camera_open,
            "camera_info": camera_list_panel_obj.camera_info,
            "camera_settings": camera_list_panel_obj.camera_settings,
            "refresh_cameras_table": camera_list_panel_obj.refresh_cameras_table            
        }
    }))

    camera_list_panel_obj.init_vue(cameras_panel)

    camera_viewer_panel_html = importlib_resources.read_text(__package__,"camera_viewer_panel.html")

    def register_camera_viewer_panel(container, state):
        container.getElement().html(camera_viewer_panel_html)

    core.layout.register_component(f"camera_viewer",register_camera_viewer_panel)

    return None


class PyriCameraViewerPanel(PyriWebUIBrowserPanelBase):

    def __init__(self, camera_local_name, core, device_manager):
        self.vue = None
        self.core = core
        self.device_manager = device_manager
        self.camera_local_name = camera_local_name

        camera_viewer_panel_config = {
            "type": "component",
            "componentName": f"camera_viewer",
            "componentState": {
                "camera_local_name": camera_local_name
            },
            "title": camera_local_name,
            "id": f"camera_viewer_{camera_local_name}",
            "isClosable": True
        }
       
        core.layout.layout.root.getItemsById("vision")[0].addChild(to_js2(camera_viewer_panel_config))
        viewer_panel_el = core.layout.layout.root.getItemsById(f"camera_viewer_{camera_local_name}")[0].element
        self.viewer_img = viewer_panel_el.find("#camera_viewer_img")[0]
        viewer_panel_toolbar = viewer_panel_el.find("#camera_viewer_panel_toolbar")[0]
        print(f"viewer_img: {self.viewer_img}")

        self.viewer_connected = False

        self.vue = js.Vue.new(to_js2({
            "el": viewer_panel_toolbar,
            "data":
            {
                "capturing_sequence": False,
                "captured_sequence_global_name": "",
                "captured_sequence_count": 0,
                "save_system_state_checked": True
            },
            "methods":
            {
                "save_to_globals": self.save_to_globals,
                "save_sequence_to_globals": self.save_sequence_to_globals,
                "sequence_capture_next": self.sequence_capture_next,
                "sequence_capture_done": self.sequence_capture_done,
                "sequence_capture_cancel": self.sequence_capture_cancel
            }
        }))

        self.core.create_task(self._run_viewer())

    async def _run_viewer(self):

        viewer_obj = None
        img = None
        try:
            while True: 
                try:
                    if viewer_obj is None:
                        if not self.viewer_connected:
                            try:
                                self.device_manager.connect_device("vision_camera_viewer")
                                self.viewer_connected = True
                            except:
                                pass                            
                        viewer_service = self.device_manager.get_device_subscription("vision_camera_viewer").GetDefaultClient()
                        viewer_obj = await viewer_service.async_get_camera_viewer(self.camera_local_name,None)
                    img = await viewer_obj.async_capture_frame_preview(None)
                except:
                    traceback.print_exc()
                    viewer_obj = None
                else:                   
                    encoded = str(base64.b64encode(img.data))[2:-1]
                    self.viewer_img.src = "data:image/jpeg;base64," + encoded

                img = None
                
                await RRN.AsyncSleep(0.001,None)
        except:
            traceback.print_exc()
    
    async def do_save_to_globals(self, global_name, save_state):
        try:
            viewer_service = self.device_manager.get_device_subscription("vision_camera_viewer").GetDefaultClient()
            viewer_obj = await viewer_service.async_get_camera_viewer(self.camera_local_name,None)
            await viewer_obj.async_save_to_globals(global_name, save_state, None)

            js.alert(f"Image \"{global_name}\" saved")
        except:
            js.alert(f"Save image failed:\n\n{traceback.format_exc()}")
            traceback.print_exc()

    def save_to_globals(self, *args):
        global_name = js.prompt("global name")
        if global_name is None or global_name == "":
            return
        save_state = getattr(self.vue,"$data").save_system_state_checked
        self.core.create_task(self.do_save_to_globals(global_name, save_state))

    async def do_save_sequence_to_globals(self, global_name, save_state):
        try:
            viewer_service = self.device_manager.get_device_subscription("vision_camera_viewer").GetDefaultClient()
            viewer_obj = await viewer_service.async_get_camera_viewer(self.camera_local_name,None)
            self._sequence_gen = await viewer_obj.async_save_sequence_to_globals(global_name, save_state, None)

        except:
            self._sequence_gen = None
            js.alert(f"Save image sequence failed:\n\n{traceback.format_exc()}")
            traceback.print_exc()

    def save_sequence_to_globals(self, *args):
        global_name = js.prompt("global name")
        if global_name is None or global_name == "":
            return
        getattr(self.vue,"$data").capturing_sequence=True
        getattr(self.vue,"$data").captured_sequence_count=0
        getattr(self.vue,"$data").captured_sequence_global_name=global_name

        save_state = getattr(self.vue,"$data").save_system_state_checked
        self.core.create_task(self.do_save_sequence_to_globals(global_name, save_state))

    async def do_sequence_capture_next(self):
        try:            
            # TODO: AsyncNext should only have one argument
            await self._sequence_gen.AsyncNext(None,None)
        except:
            self._sequence_gen = None
            js.alert(f"Save image sequence failed:\n\n{traceback.format_exc()}")
            traceback.print_exc()

    def sequence_capture_next(self, *args):
        getattr(self.vue,"$data").captured_sequence_count+=1
        self.core.create_task(self.do_sequence_capture_next())

    async def do_sequence_capture_done(self):
        try:            
            await self._sequence_gen.AsyncClose(None)
            self._sequence_gen = None
        except:
            self._sequence_gen = None
            js.alert(f"Save image sequence failed:\n\n{traceback.format_exc()}")
            traceback.print_exc()

    def sequence_capture_done(self, *args):
        getattr(self.vue,"$data").capturing_sequence=False
        getattr(self.vue,"$data").captured_sequence_count=0
        getattr(self.vue,"$data").captured_sequence_global_name=""
        self.core.create_task(self.do_sequence_capture_done())

    async def do_sequence_capture_cancel(self):
        try:            
            await self._sequence_gen.AsyncAbort(None)
            self._sequence_gen = None
        except:
            self._sequence_gen = None
            js.alert(f"Save image sequence failed:\n\n{traceback.format_exc()}")
            traceback.print_exc()

    def sequence_capture_cancel(self, *args):
        getattr(self.vue,"$data").capturing_sequence=False
        getattr(self.vue,"$data").captured_sequence_count=0
        getattr(self.vue,"$data").captured_sequence_global_name=""
        self.core.create_task(self.do_sequence_capture_abort())



    