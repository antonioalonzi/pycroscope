import glob
import os
import re
import subprocess
import sys
from datetime import datetime

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QLabel, QPushButton,
    QComboBox, QDoubleSpinBox, QFileDialog, QHBoxLayout,
    QVBoxLayout, QFormLayout, QGroupBox, QStatusBar, QButtonGroup, QRadioButton, QSizePolicy
)

from src.control.control_panel import ControlPanel
from src.video.video_thread import VideoThread
from src.settings.app_settings import AppSettings
from src.utils.utils import calculate_scale
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
        # self.detect_cameras()

    def init_ui(self):
        # window
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

        # Device Selection

        # Optical Calibration

        # Measurement Actions
        meas_group = QGroupBox("Measurement")
        meas_layout = QVBoxLayout(meas_group)

        self.snap_btn = QPushButton("Snap Frame")
        self.snap_btn.setFixedHeight(40)
        self.snap_btn.setStyleSheet("font-weight: bold; font-size: 14px;")
        self.snap_btn.clicked.connect(self.toggle_snap)
        meas_layout.addWidget(self.snap_btn)

        color_row = QHBoxLayout()
        color_label = QLabel("Measure Color:")
        color_label.setMinimumWidth(100)
        color_row.addWidget(color_label)
        self.measurement_color_buttons = []
        self.selected_color_button = None
        for color_name in ["Cyan", "Green", "Yellow", "Magenta", "Orange", "Red"]:
            button = QPushButton()
            button.setFixedSize(22, 22)
            button.setToolTip(color_name)
            button.setStyleSheet(
                f"background-color: {self.color_name_to_hex(color_name)}; "
                "border: 1px solid #444; border-radius: 2px;"
            )
            button.clicked.connect(lambda _, name=color_name: self.change_measurement_color(name))
            button.setEnabled(False)
            self.measurement_color_buttons.append(button)
            color_row.addWidget(button)
        self.selected_color_button = self.measurement_color_buttons[1]
        self.selected_color_button.setStyleSheet(
            f"background-color: {self.color_name_to_hex('Green')}; "
            "border: 2px solid #ffffff; border-radius: 2px;"
        )
        color_row.addStretch()
        meas_layout.addLayout(color_row)

        mode_layout = QHBoxLayout()
        self.meas_button_group = QButtonGroup(self)
        self.radio_dist = QRadioButton("Distance")
        self.radio_dist.setEnabled(False)
        self.radio_angle = QRadioButton("Angle")
        self.radio_angle.setEnabled(False)
        self.radio_text = QRadioButton("Text")
        self.radio_text.setEnabled(False)
        self.radio_dist.setChecked(True)
        self.meas_button_group.addButton(self.radio_dist)
        self.meas_button_group.addButton(self.radio_angle)
        self.meas_button_group.addButton(self.radio_text)
        mode_layout.addWidget(self.radio_dist)
        mode_layout.addWidget(self.radio_angle)
        mode_layout.addWidget(self.radio_text)
        meas_layout.addLayout(mode_layout)
        self.meas_button_group.buttonClicked.connect(
            lambda btn: self.change_measurement_mode(btn.text())
        )

        action_row = QHBoxLayout()
        self.delete_last_btn = QPushButton("Clear Last")
        self.delete_last_btn.clicked.connect(self.video_widget.clear_last_edit)
        self.delete_last_btn.setEnabled(False)
        self.delete_last_btn.setMinimumWidth(120)
        action_row.addWidget(self.delete_last_btn, 1)

        action_row.addSpacing(8)

        self.clear_btn = QPushButton("Clear All")
        self.clear_btn.clicked.connect(self.video_widget.clear_points)
        self.clear_btn.setEnabled(False)
        self.clear_btn.setMinimumWidth(120)
        action_row.addWidget(self.clear_btn, 1)

        meas_layout.addLayout(action_row)
        control_panel.addWidget(meas_group)

        # Output Storage
        cap_group = QGroupBox("Output Storage")
        cap_layout = QVBoxLayout(cap_group)
        self.folder_btn = QPushButton("Select Output Directory")
        self.folder_btn.clicked.connect(self.choose_folder)
        cap_layout.addWidget(self.folder_btn)

        self.dir_label = QLabel()
        self.dir_label.setWordWrap(True)
        self.dir_label.setStyleSheet("color: #AAA;")
        self.dir_label.setText(f"Output Storage: {os.path.basename(os.path.normpath(self.settings.save_dir))}")
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



    def start_camera(self):
        if self.video_thread is not None:
            self.video_thread.stop()

        self.is_frozen = False
        self.snap_btn.setText("Snap Frame")

        device = self.camera_selector.currentData()
        if device is None:
            return

        self.settings.set_last_device(device)

        self.resolution_selector.blockSignals(True)
        self.resolution_selector.clear()
        self.resolution_selector.setEnabled(False)

        resolutions = self.get_camera_resolutions(device)
        if resolutions:
            for width, height in resolutions:
                self.resolution_selector.addItem(f"{width}x{height}", (width, height))

            preferred_resolution = self.settings.camera_resolution
            if preferred_resolution is not None:
                preferred_resolution = tuple(preferred_resolution)
            if preferred_resolution not in resolutions:
                preferred_resolution = resolutions[-1]

            target_text = f"{preferred_resolution[0]}x{preferred_resolution[1]}"
            index = self.resolution_selector.findText(target_text)
            if index != -1:
                self.resolution_selector.setCurrentIndex(index)
            else:
                self.resolution_selector.setCurrentIndex(0)

            self.settings.set_camera_resolution(tuple(self.resolution_selector.currentData()))
            self.resolution_selector.setEnabled(True)
        else:
            self.settings.set_camera_resolution(None)

        self.resolution_selector.blockSignals(False)

        self.video_thread = VideoThread(device_path=device, resolution=self.settings.camera_resolution)
        self.video_thread.frame_signal.connect(self.video_widget.set_frame)
        self.video_thread.start()
        self.status_bar.showMessage(f"Connected to device: {device}", STATUS_BAR_MESSAGE_DURATION)

    def change_camera(self):
        self.start_camera()

    def change_resolution(self):
        selected = self.resolution_selector.currentData()
        if selected is None:
            return
        self.settings.set_camera_resolution(tuple(selected))
        self.start_camera()

    @staticmethod
    def color_name_to_hex(color_name):
        colors = {
            "Cyan": "#00B4FF",
            "Green": "#00FF80",
            "Yellow": "#FFD600",
            "Magenta": "#FF00CC",
            "Orange": "#FF8C00",
            "Red": "#FF3C3C",
        }
        return colors.get(color_name, "#00FF80")

    def change_measurement_mode(self, mode_name):
        mode = mode_name.lower()
        self.video_widget.set_measurement_mode(mode)
        self.status_bar.showMessage(f"Measurement mode: {mode_name}", STATUS_BAR_MESSAGE_DURATION)

    def change_measurement_color(self, color_name):
        self.video_widget.set_measurement_color(color_name)
        if self.selected_color_button is not None:
            self.selected_color_button.setStyleSheet(
                f"background-color: {self.color_name_to_hex(self.selected_color_button.toolTip())}; "
                "border: 1px solid #444; border-radius: 2px;"
            )
        for button in self.measurement_color_buttons:
            if button.toolTip() == color_name:
                self.selected_color_button = button
                button.setStyleSheet(
                    f"background-color: {self.color_name_to_hex(color_name)}; "
                    "border: 2px solid #ffffff; border-radius: 2px;"
                )
                break
        self.status_bar.showMessage(f"Measurement color: {color_name}", STATUS_BAR_MESSAGE_DURATION)

    def choose_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Save Directory", self.settings.save_dir)
        if folder:
            folder_name = os.path.basename(os.path.normpath(folder))
            self.dir_label.setText(f"Output Storage: {folder_name}")
            self.settings.set_save_dir(folder)

    def toggle_snap(self):
        if not self.is_frozen:
            if self.video_widget.current_frame is None:
                self.status_bar.showMessage("Error: No frame available to snap.", STATUS_BAR_MESSAGE_DURATION)
                return

            if self.video_thread is not None:
                self.video_thread.frame_signal.disconnect(self.video_widget.set_frame)

            self.is_frozen = True
            self.snap_btn.setText("Resume Live View")
            self.status_bar.showMessage("Frame frozen", STATUS_BAR_MESSAGE_DURATION)
        else:
            if self.video_thread is not None:
                self.video_thread.frame_signal.connect(self.video_widget.set_frame)

            self.is_frozen = False
            self.snap_btn.setText("Snap Frame")
            self.status_bar.showMessage("Resumed live feed", STATUS_BAR_MESSAGE_DURATION)

        self.video_widget.set_measurement_enabled(self.is_frozen)
        self.clear_btn.setEnabled(self.is_frozen)
        self.delete_last_btn.setEnabled(self.is_frozen)
        self.radio_dist.setEnabled(self.is_frozen)
        self.radio_angle.setEnabled(self.is_frozen)
        self.radio_text.setEnabled(self.is_frozen)
        for button in self.measurement_color_buttons:
            button.setEnabled(self.is_frozen)

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
