import os
import sys
from datetime import datetime

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QLabel, QPushButton,
    QHBoxLayout,
    QVBoxLayout, QGroupBox, QStatusBar, QFileDialog
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
        self.video_thread = None
        self.is_frozen = False

        self.control_panel = ControlPanel(self.settings)

        # Window size/state restore
        geometry = self.settings.geometry
        if geometry:
            self.restoreGeometry(geometry)

        window_state = self.settings.window_state
        if window_state:
            self.restoreState(window_state)

        # Window Widget
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QHBoxLayout(main_widget)

        # Camera Widget
        self.video_widget = VideoWidget()
        main_layout.addWidget(self.video_widget, stretch=3)

        # Control Panel
        main_layout.addLayout(self.control_panel, stretch=1)

        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

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
