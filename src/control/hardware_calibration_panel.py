from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QVBoxLayout, QGroupBox, QFormLayout, QDoubleSpinBox, QLabel, QWidget, \
    QHBoxLayout, QSizePolicy

from src.settings.app_settings import AppSettings
from src.utils.utils import calculate_scale


class HardwareCalibrationPanel(QVBoxLayout):
    def __init__(self, control_panel: QVBoxLayout, settings: AppSettings):
        super().__init__()

        self.control_panel = control_panel
        self.settings = settings

        calib_group = QGroupBox("Hardware Calibration")
        calib_layout = QFormLayout(calib_group)

        self.pitch_spin = QDoubleSpinBox()
        self.pitch_spin.setRange(0.01, 100.0)
        self.pitch_spin.setValue(settings.pitch_spin)
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
        self.obj_spin.setValue(settings.obj_spin)
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
        self.cmount_spin.setValue(settings.cmount_spin)
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

        self.update_scale()

    @staticmethod
    def add_calibration_row(form_layout, label_text, spin_box, tooltip):
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

    def update_scale(self):
        self.settings.set_pitch_spin(self.pitch_spin.value())
        self.settings.set_obj_spin(self.obj_spin.value())
        self.settings.set_cmount_spin(self.cmount_spin.value())
        scale = calculate_scale(
            self.settings.pitch_spin,
            self.settings.obj_spin,
            self.settings.cmount_spin
        )
        # self.video_widget.scale_um_per_px = scale
        self.scale_label.setText(f"{scale:.4f} µm/px")
        # self.video_widget.update_display()
