from typing import List, Dict, Callable, Any, Tuple
from pyri.webui_browser.plugins.variable_dialog import PyriWebUIBrowserVariableDialogInfo, PyriWebUIBrowserVariableDialogPluginFactory, PyriWebUIBrowserVariableDialogBase
from pyri.webui_browser import PyriWebUIBrowser
from .new_calibrate_intrinsic_dialog import show_new_camera_calibration_intrinsic_dialog

_variable_dialog_infos = {
    ("com.robotraconteur.imaging.camerainfo.CameraCalibration",("camera_calibration_intrinsic")): \
        PyriWebUIBrowserVariableDialogInfo(
            "vision_camera_calibration_intrinsic",
            "Camera Calibration Intrinsic",
            "com.robotraconteur.imaging.camerainfo.CameraCalibration",
            ["camera_calibration_intrinsic"],
            "Camera Intrinsic Calibration Parameters",
        ),
    ("com.robotraconteur.geometry.NamedPoseWithCovariance",("camera_calibration_extrinsic")): \
        PyriWebUIBrowserVariableDialogInfo(
            "vision_camera_calibration_extrinsic",
            "Camera Calibration Extrinsic",
            "com.robotraconteur.geometry.NamedPoseWithCovariance",
            ["camera_calibration_extrinsic"],
            "Camera Extrinsic Calibration Parameters"
        )
}

class PyriVisionWebUIBrowserVariableDialogPluginFactory(PyriWebUIBrowserVariableDialogPluginFactory):
    def __init__(self):
        super().__init__()

    def get_plugin_name(self) -> str:
        return "pyri-vision-browser"

    def get_variable_dialog_infos(self) -> Dict[Tuple[str,Tuple[str]],PyriWebUIBrowserVariableDialogInfo]:
        return _variable_dialog_infos

    def show_variable_new_dialog(self, new_name: str, variable_type: str, variable_tags: str, core: "PyriWebUIBrowser") -> None:
        if variable_type == "com.robotraconteur.imaging.camerainfo.CameraCalibration" and "camera_calibration_intrinsic" in variable_tags:
            show_new_camera_calibration_intrinsic_dialog(new_name, variable_type, variable_tags, core)
            return
        assert False, "Invalid new variable dialog type requested"

    def show_variable_edit_dialog(self, variable_name: str, variable_type: str, variable_tags: List[str], core: "PyriWebUIBrowser") -> None:
        raise NotImplementedError()

def get_webui_browser_variable_dialog_factory():
    return PyriVisionWebUIBrowserVariableDialogPluginFactory()
    