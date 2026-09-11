import sys

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QHBoxLayout,
    QStatusBar
)

from src.control.control_panel import ControlPanel
from src.settings.app_settings import AppSettings
from src.video.video_thread import VideoThread
from src.video.video_widget import VideoWidget
from utils.camera_utils import get_preferred_camera, get_preferred_resolution

STATUS_BAR_MESSAGE_DURATION = 3000


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Pycroscope")

        self.settings = AppSettings()
        self.restore_window_size_and_state()

        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

        self.control_panel = ControlPanel(self.settings)
        self.video_widget = VideoWidget()
        self.video_thread = None
        preferred_camera = get_preferred_camera(self.settings.last_device)
        preferred_resolution = get_preferred_resolution(preferred_camera['dev'], self.settings.camera_resolution)
        self._start_camera(preferred_camera['dev'], preferred_resolution, preferred_camera['camera_name'])

        main_widget = QWidget()
        self.setCentralWidget(main_widget)

        main_layout = QHBoxLayout(main_widget)
        main_layout.addWidget(self.video_widget, stretch=3)
        main_layout.addLayout(self.control_panel, stretch=1)

        self.control_panel.camera_hardware_panel.start_camera_emitter.connect(self.start_camera)
        self.control_panel.measurement_panel.measurement_signal.connect(self.video_widget.set_measurement)


    def restore_window_size_and_state(self):
        geometry = self.settings.geometry
        if geometry:
            self.restoreGeometry(geometry)

        window_state = self.settings.window_state
        if window_state:
            self.restoreState(window_state)


    def start_camera(self, config: dict):
        self._start_camera(config["device_path"], config["resolution"], config["device_name"])
        self.status_bar.showMessage(f"Starting {config["device_name"]} ({config["device_path"]}) at {config["resolution"][0]}x{config["resolution"][1]}...", STATUS_BAR_MESSAGE_DURATION)


    def _start_camera(self, device_path: str, resolution: tuple, device_name: str = ''):
        if self.video_thread is not None:
            self.video_thread.stop()

        self.status_bar.showMessage(f"Starting {device_name} ({device_path}) at {resolution[0]}x{resolution[1]}...", STATUS_BAR_MESSAGE_DURATION)

        self.video_thread = VideoThread(device_path, resolution)
        self.video_thread.frame_signal.connect(self.video_widget.set_frame)
        self.control_panel.measurement_panel.freeze_signal.connect(self.video_thread.toggle_freeze)
        self.video_thread.start()


    def closeEvent(self, event):
        self.settings.set_geometry(self.saveGeometry())
        self.settings.set_window_state( self.saveState())

        if self.video_thread is not None:
            self.video_thread.stop()
        event.accept()


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
