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

from camera import VideoThread
from settings import AppSettings
from utils import calculate_scale
from widgets import VideoWidget


STATUS_BAR_MESSAGE_DURATION = 3000


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Microscope Vision Workbench")

        self.settings = AppSettings()
        self.video_thread = None
        self.is_frozen = False

        self.init_ui()
        self.detect_cameras()

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
        control_panel = QVBoxLayout()
        main_layout.addLayout(control_panel, stretch=1)

        # Device Selection
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

        # Optical Calibration
        calib_group = QGroupBox("Hardware Calibration")
        calib_layout = QFormLayout(calib_group)

        self.pitch_spin = QDoubleSpinBox()
        self.pitch_spin.setRange(0.01, 100.0)
        self.pitch_spin.setValue(self.settings.pitch_spin)
        self.pitch_spin.setSuffix(" µm")
        self.pitch_spin.valueChanged.connect(self.update_scale)
        self.add_calibration_row(
            calib_layout,
            "Sensor Pixel Pitch:",
            self.pitch_spin,
            (
                "Sensor pixel pitch is the distance between adjacent light-sensing pixels on your camera sensor, measured in micrometers (µm).\n"
                "The target pixel pitch depends on whether you are using industrial vision sensors, consumer webcams, or scientific cameras:\n"
                " - 3.45µm: Widely used across Sony Pregius global shutter CMOS sensors (e.g., IMX250, IMX252, IMX264, IMX273). The most dominant pixel size in machine vision and USB 3.0 inspection cameras.\n"
                " - 3.75µm: Extremely common in entry-level, astronomy, and microscope cameras built around Sony Starvis/Exmor sensors (like the IMX225 or Aptina AR0130).\n"
                " - 2.4µm to 2.74µm: Found in smaller 1/2.8\" or 1/3\" consumer webcams, board cameras, and high-resolution industrial sensors (e.g., Sony Pregius S Gen 4, which dropped down to 2.74µm.\n"
                " - 1.12µm to 1.4µm: Typical for mobile devices, high-MP consumer webcams, and inexpensive USB microscope dongles.\n"
                " - 5.5µm to 6.5µm: Common in scientific-grade CMOS (sCMOS) and large-format machine vision sensors where high sensitivity and wide dynamic range are required."
            )
        )

        self.obj_spin = QDoubleSpinBox()
        self.obj_spin.setRange(0.1, 200.0)
        self.obj_spin.setValue(self.settings.obj_spin)
        self.obj_spin.setSuffix(" x")
        self.obj_spin.valueChanged.connect(self.update_scale)
        self.add_calibration_row(
            calib_layout,
            "Objective Mag:",
            self.obj_spin,
            (
                "Objective magnification is the microscope objective's optical magnification factor.\n"
                "It tells the app how much the objective enlarges the image before it reaches the camera sensor."
            )
        )

        self.cmount_spin = QDoubleSpinBox()
        self.cmount_spin.setRange(0.01, 10.0)
        self.cmount_spin.setValue(self.settings.cmount_spin)
        self.cmount_spin.setSuffix(" x")
        self.cmount_spin.valueChanged.connect(self.update_scale)
        self.add_calibration_row(
            calib_layout,
            "C-Mount Adapter:",
            self.cmount_spin,
            (
                "C-mount adapter magnification is the multiplier from the adapter or tube between the objective and camera sensor.\n"
                "It compensates for the optical path so the app can calculate the correct real-world scale."
            )
        )

        self.scale_label = QLabel()
        self.scale_label.setStyleSheet("font-weight: bold; color: #008000;")
        calib_layout.addRow("Calculated Scale:", self.scale_label)
        control_panel.addWidget(calib_group)

        # Measurement Actions
        meas_group = QGroupBox("Measurement")
        meas_layout = QVBoxLayout(meas_group)

        self.snap_btn = QPushButton("Snap Frame")
        self.snap_btn.setFixedHeight(40)
        self.snap_btn.setStyleSheet("font-weight: bold; font-size: 14px;")
        self.snap_btn.clicked.connect(self.toggle_snap)
        meas_layout.addWidget(self.snap_btn)

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
        self.clear_btn = QPushButton("Clear All")
        self.clear_btn.clicked.connect(self.video_widget.clear_points)
        self.clear_btn.setEnabled(False)
        self.clear_btn.setMinimumWidth(120)
        action_row.addWidget(self.clear_btn, 1)
        action_row.addSpacing(8)

        self.delete_last_btn = QPushButton("Clear Last")
        self.delete_last_btn.clicked.connect(self.video_widget.clear_last_edit)
        self.delete_last_btn.setEnabled(False)
        self.delete_last_btn.setMinimumWidth(120)
        action_row.addWidget(self.delete_last_btn, 1)
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
        self.update_scale()

    def add_calibration_row(self, form_layout, label_text, spin_box, tooltip):
        field_widget = QWidget()
        field_layout = QHBoxLayout(field_widget)
        field_layout.setContentsMargins(0, 0, 0, 0)
        field_layout.setSpacing(6)

        spin_box.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        field_layout.addWidget(spin_box)

        info_label = QLabel("ⓘ")
        info_label.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        info_label.setToolTip(tooltip)
        info_label.setStyleSheet("color: #6aa6ff; font-weight: bold; margin: 4px; font-size: 14px;")

        info_label.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        field_layout.addWidget(info_label)

        form_layout.addRow(label_text, field_widget)

    def get_camera_resolutions(self, device):
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

    def detect_cameras(self):
        self.camera_selector.blockSignals(True)
        self.camera_selector.clear()

        devices = sorted(glob.glob("/dev/video*"))
        if devices:
            for dev in devices:
                self.camera_selector.addItem(dev, dev)
        else:
            self.camera_selector.addItem("Default (0)", 0)

        index = self.camera_selector.findData(self.settings.last_device)
        if index != -1:
            self.camera_selector.setCurrentIndex(index)

        self.camera_selector.blockSignals(False)
        self.start_camera()

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

    def change_measurement_mode(self, mode_name):
        mode = mode_name.lower()
        self.video_widget.set_measurement_mode(mode)
        self.status_bar.showMessage(f"Measurement mode: {mode_name}", STATUS_BAR_MESSAGE_DURATION)

    def update_scale(self):
        self.settings.set_pitch_spin(self.pitch_spin.value())
        self.settings.set_obj_spin(self.obj_spin.value())
        self.settings.set_cmount_spin(self.cmount_spin.value())
        scale = calculate_scale(
            self.settings.pitch_spin,
            self.settings.obj_spin,
            self.settings.cmount_spin
        )
        self.video_widget.scale_um_per_px = scale
        self.scale_label.setText(f"{scale:.4f} µm/px")
        self.video_widget.update_display()

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
