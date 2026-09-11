from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QVBoxLayout, QGroupBox, QFormLayout, QComboBox, QWidget

from src.settings.app_settings import AppSettings
from utils.camera_utils import get_available_cameras, get_preferred_camera, get_camera_resolutions, \
    get_preferred_resolution


class CameraHardwarePanel(QWidget):
    start_camera_emitter = pyqtSignal(dict)

    def __init__(self, control_panel: QVBoxLayout, settings: AppSettings):
        super().__init__()

        self.control_panel = control_panel
        self.settings = settings

        hw_group = QGroupBox("Camera Hardware")
        hw_layout = QFormLayout(hw_group)
        self.camera_selector = QComboBox()
        self.camera_selector.currentIndexChanged.connect(self.change_camera)
        hw_layout.addRow("Video Device:", self.camera_selector)

        self.resolution_selector = QComboBox()
        self.resolution_selector.setEnabled(False)
        self.resolution_selector.currentIndexChanged.connect(self.change_resolution)
        hw_layout.addRow("Video Resolution:", self.resolution_selector)
        control_panel.addWidget(hw_group)

        self.detect_cameras()

    def detect_cameras(self):
        self.camera_selector.blockSignals(True)
        self.camera_selector.clear()

        cameras = get_available_cameras()
        for camera in cameras:
            self.camera_selector.addItem(f"{camera['camera_name']} ({camera['dev']})", camera['dev'])

        preferred_camera = get_preferred_camera(self.settings.last_device)
        self.select_camera(preferred_camera['dev'])

        self.camera_selector.blockSignals(False)
        self.detect_camera_resolutions()

    def select_camera(self, device):
        index = self.camera_selector.findData(device)
        if index != -1:
            self.camera_selector.setCurrentIndex(index)

    def detect_camera_resolutions(self):
        if self.camera_selector.currentData() is None:
            return

        self.resolution_selector.blockSignals(True)
        self.resolution_selector.clear()
        self.resolution_selector.setEnabled(False)

        resolutions = get_camera_resolutions(self.camera_selector.currentData())
        if resolutions:
            for width, height in resolutions:
                self.resolution_selector.addItem(f"{width}x{height}", (width, height))

            self.select_resolution()
            self.resolution_selector.setEnabled(True)

        self.resolution_selector.blockSignals(False)

    def select_resolution(self):
        resolutions = [
            self.resolution_selector.itemData(i)
            for i in range(self.resolution_selector.count())
        ]

        preferred_resolution = get_preferred_resolution(self.settings.last_device, self.settings.camera_resolution)
        index = resolutions.index(preferred_resolution)
        if index != -1:
            self.resolution_selector.setCurrentIndex(index)

        self.start_camera_emitter.emit({
            "device_path": self.camera_selector.currentData(),
            "device_name": self.camera_selector.currentText(),
            "resolution": self.settings.camera_resolution
        })

    def change_camera(self):
        self.settings.set_last_device(self.camera_selector.currentData())
        self.select_camera(self.camera_selector.currentData())
        self.detect_camera_resolutions()
        self.start_camera_emitter.emit({
            "device_path": self.camera_selector.currentData(),
            "device_name": self.camera_selector.currentText(),
            "resolution": self.settings.camera_resolution
        })

    def change_resolution(self):
        self.settings.set_camera_resolution(tuple(self.resolution_selector.currentData()))
        self.select_resolution()
        self.start_camera_emitter.emit({
            "device_path": self.camera_selector.currentData(),
            "device_name": self.camera_selector.currentText(),
            "resolution": self.settings.camera_resolution
        })
