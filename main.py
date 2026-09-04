import glob
import os
import sys
from datetime import datetime

from PyQt6.QtCore import QSettings
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QLabel, QPushButton,
    QComboBox, QDoubleSpinBox, QFileDialog, QHBoxLayout,
    QVBoxLayout, QFormLayout, QGroupBox, QStatusBar, QInputDialog,
    QButtonGroup, QRadioButton
)

from camera import VideoThread
from utils import calculate_scale
from widgets import VideoWidget


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Microscope Vision Workbench")
        self.resize(1024, 720)

        self.settings = QSettings("MicroscopeLab", "VisionWorkbench")
        self.video_thread = None
        self.is_frozen = False

        self.init_ui()
        self.load_settings()
        self.detect_cameras()

    def init_ui(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QHBoxLayout(main_widget)

        self.video_widget = VideoWidget()
        main_layout.addWidget(self.video_widget, stretch=3)

        control_panel = QVBoxLayout()
        main_layout.addLayout(control_panel, stretch=1)

        # Device Selection
        hw_group = QGroupBox("Camera Hardware")
        hw_layout = QFormLayout(hw_group)
        self.camera_selector = QComboBox()
        self.camera_selector.currentIndexChanged.connect(self.change_camera)
        hw_layout.addRow("Video Device:", self.camera_selector)
        control_panel.addWidget(hw_group)

        # Optical Calibration
        calib_group = QGroupBox("Hardware Calibration")
        calib_layout = QFormLayout(calib_group)

        self.pitch_spin = QDoubleSpinBox()
        self.pitch_spin.setRange(0.01, 100.0)
        self.pitch_spin.setValue(3.75)
        self.pitch_spin.setSuffix(" um")
        self.pitch_spin.valueChanged.connect(self.update_scale)
        calib_layout.addRow("Sensor Pixel Pitch:", self.pitch_spin)

        self.obj_spin = QDoubleSpinBox()
        self.obj_spin.setRange(0.1, 200.0)
        self.obj_spin.setValue(10.0)
        self.obj_spin.setSuffix(" x")
        self.obj_spin.valueChanged.connect(self.update_scale)
        calib_layout.addRow("Objective Mag:", self.obj_spin)

        self.cmount_spin = QDoubleSpinBox()
        self.cmount_spin.setRange(0.01, 10.0)
        self.cmount_spin.setValue(0.5)
        self.cmount_spin.setSuffix(" x")
        self.cmount_spin.valueChanged.connect(self.update_scale)
        calib_layout.addRow("C-Mount Adapter:", self.cmount_spin)

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
        cap_layout.addWidget(self.dir_label)

        # Save Image with Measurement Overlays
        self.save_meas_btn = QPushButton("Save")
        self.save_meas_btn.clicked.connect(self.save_image)
        cap_layout.addWidget(self.save_meas_btn)

        control_panel.addWidget(cap_group)
        control_panel.addStretch()

        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.update_scale()

    def detect_cameras(self):
        self.camera_selector.blockSignals(True)
        self.camera_selector.clear()

        devices = sorted(glob.glob("/dev/video*"))
        if devices:
            for dev in devices:
                self.camera_selector.addItem(dev, dev)
        else:
            self.camera_selector.addItem("Default (0)", 0)

        saved_device = self.settings.value("last_device", "")
        index = self.camera_selector.findData(saved_device)
        if index != -1:
            self.camera_selector.setCurrentIndex(index)

        self.camera_selector.blockSignals(False)
        self.start_camera()

    def start_camera(self):
        if self.video_thread is not None:
            self.video_thread.stop()

        self.is_frozen = False
        self.snap_btn.setText("Snap Frame")
        self.snap_btn.setStyleSheet("font-weight: bold; font-size: 14px;")

        device = self.camera_selector.currentData()
        if device is not None:
            self.settings.setValue("last_device", device)
            self.video_thread = VideoThread(device_path=device)
            self.video_thread.frame_signal.connect(self.video_widget.set_frame)
            self.video_thread.start()
            self.status_bar.showMessage(f"Connected to device: {device}")

    def change_camera(self):
        self.start_camera()

    def change_measurement_mode(self, mode_name):
        mode = mode_name.lower()
        self.video_widget.set_measurement_mode(mode)
        self.status_bar.showMessage(f"Measurement mode: {mode_name}", 2000)

    def add_text_annotation(self):
        if not self.is_frozen:
            self.status_bar.showMessage("Snap the frame before adding text.", 3000)
            return

        text, ok = QInputDialog.getText(self, "Add Label", "Text:")
        if ok and text.strip():
            self.video_widget.begin_text_annotation(text.strip())
            self.status_bar.showMessage("Click on the frame to place the label.", 2500)

    def update_scale(self):
        scale = calculate_scale(
            self.pitch_spin.value(),
            self.obj_spin.value(),
            self.cmount_spin.value()
        )
        self.video_widget.scale_um_per_px = scale
        self.scale_label.setText(f"{scale:.4f} um/px")
        self.video_widget.update_display()

    def choose_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Save Directory", self.save_dir)
        if folder:
            self.save_dir = folder
            folder_name = os.path.basename(os.path.normpath(self.save_dir))
            self.dir_label.setText(f"Output Storage: {folder_name}")
            self.settings.setValue("save_dir", self.save_dir)

    def load_settings(self):
        default_dir = os.path.expanduser("~/Pictures")
        self.save_dir = self.settings.value("save_dir", default_dir)
        folder_name = os.path.basename(os.path.normpath(self.save_dir))
        self.dir_label.setText(f"Output Storage: {folder_name}")

        geometry = self.settings.value("geometry")
        if geometry:
            self.restoreGeometry(geometry)

    def toggle_snap(self):
        if not self.is_frozen:
            if self.video_widget.current_frame is None:
                self.status_bar.showMessage("Error: No frame available to snap.", 3000)
                return

            if self.video_thread is not None:
                self.video_thread.frame_signal.disconnect(self.video_widget.set_frame)

            self.video_widget.set_measurement_enabled(True)
            self.is_frozen = True
            self.clear_btn.setEnabled(True)
            self.delete_last_btn.setEnabled(True)
            self.radio_dist.setEnabled(True)
            self.radio_angle.setEnabled(True)
            self.radio_text.setEnabled(True)
            self.snap_btn.setText("Resume Live View")
            self.snap_btn.setStyleSheet("font-weight: bold; font-size: 14px; background-color: #d9534f; color: white;")
            self.status_bar.showMessage("Frame frozen", 3000)
        else:
            if self.video_thread is not None:
                self.video_thread.frame_signal.connect(self.video_widget.set_frame)

            self.video_widget.set_measurement_enabled(False)
            self.is_frozen = False
            self.clear_btn.setEnabled(False)
            self.delete_last_btn.setEnabled(False)
            self.radio_dist.setEnabled(False)
            self.radio_angle.setEnabled(False)
            self.radio_text.setEnabled(False)
            self.snap_btn.setText("Snap Frame")
            self.snap_btn.setStyleSheet("font-weight: bold; font-size: 14px;")
            self.status_bar.showMessage("Resumed live feed", 3000)

    def save_image(self):
        pixmap = self.video_widget.grab()
        if pixmap.isNull():
            self.status_bar.showMessage("Error: Failed to capture widget pixmap.", 3000)
            return

        os.makedirs(self.save_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filepath = os.path.join(self.save_dir, f"microscope_meas_{timestamp}.png")

        pixmap.save(filepath, "PNG")
        self.status_bar.showMessage(f"Saved annotated image: {filepath}", 5000)

    def closeEvent(self, event):
        self.settings.setValue("geometry", self.saveGeometry())

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