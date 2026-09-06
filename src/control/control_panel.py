from PyQt6.QtWidgets import QApplication, QVBoxLayout, QGroupBox, QFormLayout, QComboBox

from src.control.camera_hardware_panel import CameraHardwarePanel
from src.control.hardware_calibration_panel import HardwareCalibrationPanel
from src.settings.app_settings import AppSettings


class ControlPanel(QVBoxLayout):
    def __init__(self, settings: AppSettings):
        super().__init__()

        self.camera_hardware_panel = CameraHardwarePanel(self, settings)
        self.hardware_calibration_panel = HardwareCalibrationPanel(self, settings)
        self.addStretch()
