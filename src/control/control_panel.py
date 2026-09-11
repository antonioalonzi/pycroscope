from PyQt6.QtWidgets import QApplication, QVBoxLayout, QGroupBox, QFormLayout, QComboBox

from control.measurement_panel import MeasurementPanel
from control.output_panel import OutputPanel
from src.control.camera_hardware_panel import CameraHardwarePanel
from src.control.hardware_calibration_panel import HardwareCalibrationPanel
from src.settings.app_settings import AppSettings


class ControlPanel(QVBoxLayout):
    def __init__(self, settings: AppSettings):
        super().__init__()

        self.camera_hardware_panel = CameraHardwarePanel(self, settings)
        self.hardware_calibration_panel = HardwareCalibrationPanel(self, settings)
        self.measurement_panel = MeasurementPanel(self, settings)
        # todo add a display panel to control the zoom (see last line of video_widget)
        self.output_panel = OutputPanel(self, settings)
        self.addStretch()
