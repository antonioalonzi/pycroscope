import sys

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QHBoxLayout,
    QStatusBar
)

from src.control.control_panel import ControlPanel
from src.settings.app_settings import AppSettings
from src.video.video_thread import VideoThread
from src.video.video_widget import VideoWidget

STATUS_BAR_MESSAGE_DURATION = 3000


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Pycroscope")

        self.settings = AppSettings()
        self.restore_window_size_and_state()

        self.control_panel = ControlPanel(self.settings)
        self.video_widget = VideoWidget()
        self.video_thread = VideoThread(self.settings.last_device, self.settings.camera_resolution)
        self.video_thread.frame_signal.connect(self.video_widget.set_frame)
        self.video_thread.start()

        main_widget = QWidget()
        self.setCentralWidget(main_widget)

        main_layout = QHBoxLayout(main_widget)
        main_layout.addWidget(self.video_widget, stretch=3)
        main_layout.addLayout(self.control_panel, stretch=1)

        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.control_panel.camera_hardware_panel.status_bar_emitter.connect(self.handle_command)


    def restore_window_size_and_state(self):
        geometry = self.settings.geometry
        if geometry:
            self.restoreGeometry(geometry)

        window_state = self.settings.window_state
        if window_state:
            self.restoreState(window_state)


    def handle_command(self, message: str):
        self.status_bar.showMessage(message, STATUS_BAR_MESSAGE_DURATION)


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
