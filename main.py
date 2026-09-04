import sys
import os
import glob
import math
from datetime import datetime
import cv2
import numpy as np

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QLabel, QPushButton,
    QComboBox, QDoubleSpinBox, QFileDialog, QHBoxLayout,
    QVBoxLayout, QFormLayout, QGroupBox, QStatusBar
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QPointF, QSettings
from PyQt6.QtGui import QImage, QPixmap, QPen, QColor, QPainter, QFont


class VideoThread(QThread):
    """Background thread for continuous OpenCV frame acquisition."""
    frame_signal = pyqtSignal(np.ndarray)

    def __init__(self, device_path=0):
        super().__init__()
        self.device_path = device_path
        self.running = True

    def run(self):
        # Open device using V4L2 backend on Linux
        if isinstance(self.device_path, str):
            cap = cv2.VideoCapture(self.device_path, cv2.CAP_V4L2)
        else:
            cap = cv2.VideoCapture(self.device_path)

        while self.running:
            ret, frame = cap.read()
            if ret:
                self.frame_signal.emit(frame)
            else:
                self.msleep(30)
        cap.release()

    def stop(self):
        self.running = False
        self.wait()


class VideoWidget(QLabel):
    """Custom QLabel to handle live video rendering and interactive point selection."""
    point_clicked = pyqtSignal(QPointF)

    def __init__(self):
        super().__init__()
        self.setMinimumSize(640, 480)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setStyleSheet("background-color: #1e1e1e; border: 1px solid #333;")

        self.current_frame = None
        self.points = []
        self.scale_um_per_px = 1.0  # Default scale

    def set_frame(self, frame):
        self.current_frame = frame
        self.update_display()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.pixmap():
            # Translate widget click coordinates to underlying image pixels
            pm_size = self.pixmap().size()
            lbl_size = self.size()

            # Account for Qt.KeepAspectRatio scaling offsets
            scaled_w = pm_size.width()
            scaled_h = pm_size.height()
            x_offset = (lbl_size.width() - scaled_w) / 2
            y_offset = (lbl_size.height() - scaled_h) / 2

            click_x = event.position().x() - x_offset
            click_y = event.position().y() - y_offset

            if 0 <= click_x <= scaled_w and 0 <= click_y <= scaled_h:
                if self.current_frame is not None:
                    orig_h, orig_w = self.current_frame.shape[:2]
                    img_x = (click_x / scaled_w) * orig_w
                    img_y = (click_y / scaled_h) * orig_h

                    if len(self.points) >= 2:
                        self.points.clear()

                    self.points.append((img_x, img_y))
                    self.update_display()

    def clear_points(self):
        self.points.clear()
        self.update_display()

    def update_display(self):
        if self.current_frame is None:
            return

        frame = self.current_frame.copy()

        # Draw live measurement overlay
        if len(self.points) == 1:
            p1 = (int(self.points[0][0]), int(self.points[0][1]))
            cv2.circle(frame, p1, 5, (0, 0, 255), -1)

        elif len(self.points) == 2:
            p1 = (int(self.points[0][0]), int(self.points[0][1]))
            p2 = (int(self.points[1][0]), int(self.points[1][1]))

            # Draw measurement line & anchors
            cv2.circle(frame, p1, 5, (0, 0, 255), -1)
            cv2.circle(frame, p2, 5, (0, 0, 255), -1)
            cv2.line(frame, p1, p2, (0, 255, 0), 2)

            # Calculate pixel and calibrated physical distance
            pixel_dist = math.hypot(p2[0] - p1[0], p2[1] - p1[1])
            real_dist_um = pixel_dist * self.scale_um_per_px

            # Format label (μm or mm depending on magnitude)
            if real_dist_um >= 1000:
                text = f"{real_dist_um / 1000.0:.2f} mm"
            else:
                text = f"{real_dist_um:.2f} um"

            mid_x = int((p1[0] + p2[0]) / 2)
            mid_y = int((p1[1] + p2[1]) / 2) - 10

            cv2.putText(frame, text, (mid_x, mid_y),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

        # Convert OpenCV BGR image to Qt QPixmap
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_frame.shape
        bytes_per_line = ch * w
        qt_img = QImage(rgb_frame.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
        pixmap = QPixmap.fromImage(qt_img)

        # Render maintaining window aspect ratio
        self.setPixmap(pixmap.scaled(self.size(), Qt.AspectRatioMode.KeepAspectRatio,
                                     Qt.TransformationMode.SmoothTransformation))


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Microscope Vision Workbench")
        self.resize(1024, 720)

        self.settings = QSettings("MicroscopeLab", "VisionWorkbench")
        self.video_thread = None

        self.init_ui()
        self.load_settings()
        self.detect_cameras()

    def init_ui(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QHBoxLayout(main_widget)

        # Left: Live Video Display Area
        self.video_widget = VideoWidget()
        main_layout.addWidget(self.video_widget, stretch=3)

        # Right: Control Panel
        control_panel = QVBoxLayout()
        main_layout.addLayout(control_panel, stretch=1)

        # Hardware Setup Group
        hw_group = QGroupBox("Camera Hardware")
        hw_layout = QFormLayout(hw_group)

        self.camera_selector = QComboBox()
        self.camera_selector.currentIndexChanged.connect(self.change_camera)
        hw_layout.addRow("Video Device:", self.camera_selector)

        control_panel.addWidget(hw_group)

        # Optical Calibration Group
        calib_group = QGroupBox("Hardware Calibration")
        calib_layout = QFormLayout(calib_group)

        self.pitch_spin = QDoubleSpinBox()
        self.pitch_spin.setRange(0.01, 100.0)
        self.pitch_spin.setValue(3.75)  # Default pitch in μm
        self.pitch_spin.setSuffix(" um")
        self.pitch_spin.valueChanged.connect(self.update_scale)
        calib_layout.addRow("Sensor Pixel Pitch:", self.pitch_spin)

        self.obj_spin = QDoubleSpinBox()
        self.obj_spin.setRange(0.1, 200.0)
        self.obj_spin.setValue(10.0)  # Default 10x objective
        self.obj_spin.setSuffix(" x")
        self.obj_spin.valueChanged.connect(self.update_scale)
        calib_layout.addRow("Objective Mag:", self.obj_spin)

        self.cmount_spin = QDoubleSpinBox()
        self.cmount_spin.setRange(0.01, 10.0)
        self.cmount_spin.setValue(0.5)  # Default 0.5x C-mount adapter
        self.cmount_spin.setSuffix(" x")
        self.cmount_spin.valueChanged.connect(self.update_scale)
        calib_layout.addRow("C-Mount Adapter:", self.cmount_spin)

        self.scale_label = QLabel()
        self.scale_label.setStyleSheet("font-weight: bold; color: #008000;")
        calib_layout.addRow("Calculated Scale:", self.scale_label)

        control_panel.addWidget(calib_group)

        # Measurement Controls
        meas_group = QGroupBox("Measurement")
        meas_layout = QVBoxLayout(meas_group)

        self.clear_btn = QPushButton("Clear Measurement Points")
        self.clear_btn.clicked.connect(self.video_widget.clear_points)
        meas_layout.addWidget(self.clear_btn)

        control_panel.addWidget(meas_group)

        # Capture Options
        cap_group = QGroupBox("Output Storage")
        cap_layout = QVBoxLayout(cap_group)

        self.folder_btn = QPushButton("Select Output Directory")
        self.folder_btn.clicked.connect(self.choose_folder)
        cap_layout.addWidget(self.folder_btn)

        self.dir_label = QLabel()
        self.dir_label.setWordWrap(True)
        self.dir_label.setStyleSheet("font-size: 10px; color: #555;")
        cap_layout.addWidget(self.dir_label)

        self.snap_btn = QPushButton("Snap Snapshot")
        self.snap_btn.setFixedHeight(40)
        self.snap_btn.setStyleSheet("font-weight: bold; font-size: 14px;")
        self.snap_btn.clicked.connect(self.save_snapshot)
        cap_layout.addWidget(self.snap_btn)

        control_panel.addWidget(cap_group)
        control_panel.addStretch()

        # Status Bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

        # Initialize calculated scale
        self.update_scale()

    def detect_cameras(self):
        """Scans Linux /dev/video* devices."""
        self.camera_selector.blockSignals(True)
        self.camera_selector.clear()

        devices = sorted(glob.glob("/dev/video*"))
        if devices:
            for dev in devices:
                self.camera_selector.addItem(dev, dev)
        else:
            self.camera_selector.addItem("Default (0)", 0)

        # Restore last used device if present
        saved_device = self.settings.value("last_device", "")
        index = self.camera_selector.findData(saved_device)
        if index != -1:
            self.camera_selector.setCurrentIndex(index)

        self.camera_selector.blockSignals(False)
        self.start_camera()

    def start_camera(self):
        if self.video_thread is not None:
            self.video_thread.stop()

        device = self.camera_selector.currentData()
        if device is not None:
            self.settings.setValue("last_device", device)
            self.video_thread = VideoThread(device_path=device)
            self.video_thread.frame_signal.connect(self.video_widget.set_frame)
            self.video_thread.start()
            self.status_bar.showMessage(f"Connected to device: {device}")

    def change_camera(self):
        self.start_camera()

    def update_scale(self):
        pitch = self.pitch_spin.value()
        objective = self.obj_spin.value()
        cmount = self.cmount_spin.value()

        # Scale (μm per pixel) = Pitch / (Objective * C-Mount)
        total_mag = objective * cmount
        if total_mag > 0:
            scale = pitch / total_mag
        else:
            scale = 1.0

        self.video_widget.scale_um_per_px = scale
        self.scale_label.setText(f"{scale:.4f} um/px")
        self.video_widget.update_display()

    def choose_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Save Directory", self.save_dir)
        if folder:
            self.save_dir = folder
            self.dir_label.setText(self.save_dir)
            self.settings.setValue("save_dir", self.save_dir)

    def load_settings(self):
        default_dir = os.path.expanduser("~/Pictures")
        self.save_dir = self.settings.value("save_dir", default_dir)
        self.dir_label.setText(self.save_dir)

    def save_snapshot(self):
        if self.video_widget.current_frame is None:
            self.status_bar.showMessage("Error: No frame available to capture.", 3000)
            return

        os.makedirs(self.save_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"microscope_{timestamp}.png"
        filepath = os.path.join(self.save_dir, filename)

        # Write frame to disk
        cv2.imwrite(filepath, self.video_widget.current_frame)
        self.status_bar.showMessage(f"Saved: {filepath}", 5000)

    def closeEvent(self, event):
        if self.video_thread is not None:
            self.video_thread.stop()
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())