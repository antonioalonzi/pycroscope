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
        self.init_ui()

    def init_ui(self):
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

        control_panel = QVBoxLayout()
        main_layout.addLayout(control_panel, stretch=1)

        # Output Storage
        cap_group = QGroupBox("Output Storage")
        cap_layout = QVBoxLayout(cap_group)
        self.folder_btn = QPushButton("Select Output Directory")
        self.folder_btn.clicked.connect(self.choose_folder)
        cap_layout.addWidget(self.folder_btn)

        self.dir_label = QLabel()
        self.dir_label.setWordWrap(True)
        self.dir_label.setStyleSheet("color: #AAA;")
        self.dir_label.setText(f"Output Directory: {os.path.basename(os.path.normpath(self.settings.save_dir))}")
        cap_layout.addWidget(self.dir_label)

        # Save Image with Measurement Overlays
        self.save_meas_btn = QPushButton("Save")
        self.save_meas_btn.setStyleSheet("font-weight: bold; font-size: 14px;")
        self.save_meas_btn.clicked.connect(self.save_image)
        cap_layout.addWidget(self.save_meas_btn)

        control_panel.addWidget(cap_group)
        control_panel.addStretch()

        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

    def choose_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Save Directory", self.settings.save_dir)
        if folder:
            folder_name = os.path.basename(os.path.normpath(folder))
            self.dir_label.setText(f"Output Storage: {folder_name}")
            self.settings.set_save_dir(folder)

    def start_camera(self):
        if self.video_thread is not None:
            self.video_thread.stop()

        self.is_frozen = False
        self.snap_btn.setText("Snap Frame")

        device = self.camera_selector.currentData()
        if device is None:
            return

        self.video_thread = VideoThread(device_path=device, resolution=self.settings.camera_resolution)
        self.video_thread.frame_signal.connect(self.video_widget.set_frame)
        self.video_thread.start()
        self.status_bar.showMessage(f"Connected to device: {device}", STATUS_BAR_MESSAGE_DURATION)



    def save_image(self):
        pixmap = self.video_widget.grab()
        if pixmap.isNull():
            self.status_bar.showMessage("Error: Failed to capture widget pixmap.", STATUS_BAR_MESSAGE_DURATION)
            return

        os.makedirs(self.settings.save_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filepath = os.path.join(self.settings.save_dir, f"microscope_{timestamp}.png")

        pixmap.save(filepath, "PNG")
        self.status_bar.showMessage(f"Saved image: {filepath}", STATUS_BAR_MESSAGE_DURATION)

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
