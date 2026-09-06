import glob
import re
import subprocess

from PyQt6.QtWidgets import QVBoxLayout, QGroupBox, QFormLayout, QComboBox

from src.settings.app_settings import AppSettings


class CameraHardwarePanel(QVBoxLayout):
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
        # self.start_camera()

    def detect_cameras(self):
        self.camera_selector.blockSignals(True)
        self.camera_selector.clear()

        devices = sorted(glob.glob("/dev/video*"))
        if devices:
            for dev in devices:
                self.camera_selector.addItem(dev, dev)

        self.select_camera(self.settings.last_device)

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

        resolutions = self.get_camera_resolutions(self.camera_selector.currentData())
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

        if self.settings.camera_resolution in resolutions:
            self.resolution_selector.setCurrentIndex(resolutions.index(self.settings.camera_resolution))
        else:
            self.resolution_selector.setCurrentIndex(0)

    def change_camera(self):
        self.settings.set_last_device(self.camera_selector.currentData())
        self.select_camera(self.camera_selector.currentData())
        self.detect_camera_resolutions()
        # self.start_camera()

    def change_resolution(self):
        self.settings.set_camera_resolution(tuple(self.resolution_selector.currentData()))
        # self.start_camera()

    @staticmethod
    def get_camera_resolutions(device):
        if not isinstance(device, str):
            return []

        try:
            result = subprocess.run(
                ["v4l2-ctl", "--device", device, "--list-formats-ext"],
                capture_output=True,
                text=True,
                check=False,
            )
        except FileNotFoundError:
            return []

        if result.returncode != 0:
            return []

        resolutions = set()
        for line in result.stdout.splitlines():
            match = re.search(r"(\d+)x(\d+)", line)
            if match:
                width = int(match.group(1))
                height = int(match.group(2))
                resolutions.add((width, height))

        return sorted(resolutions, key=lambda res: (res[0] * res[1], res[0], res[1]))
