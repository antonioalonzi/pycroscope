from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QVBoxLayout, QGroupBox, QLabel, QHBoxLayout, QPushButton, QButtonGroup, QRadioButton, \
    QWidget

from src.settings.app_settings import AppSettings
from utils.utils import bgr_to_rgb_hex
from video.video_widget import MEASUREMENT_COLORS_BGR


class MeasurementPanel(QWidget):
    freeze_signal = pyqtSignal(bool)
    measurement_signal = pyqtSignal(dict)

    def __init__(self, control_panel: QVBoxLayout, settings: AppSettings):
        super().__init__()

        self.control_panel = control_panel
        self.settings = settings

        self.is_frozen = False

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
        for color_name, bgr_tuple in MEASUREMENT_COLORS_BGR.items():
            button = QPushButton()
            button.setFixedSize(22, 22)
            button.setStyleSheet(
                f"background-color: {bgr_to_rgb_hex(bgr_tuple)}; "
                "border: 1px solid #444; border-radius: 2px;"
            )
            button.clicked.connect(lambda _, name=color_name: self.change_measurement_color(name))
            button.setEnabled(False)
            self.measurement_color_buttons.append(button)
            color_row.addWidget(button)
        # todo highlight the selected color... needs to be done in a shared method as the same logic will be in change_measurement_color
        # self.selected_color_button = self.measurement_color_buttons[0]
        # self.selected_color_button.setStyleSheet(
        #     f"background-color: #444; "
        #     "border: 2px solid #ffffff; border-radius: 2px;"
        # )
        color_row.addStretch()
        meas_layout.addLayout(color_row)

        mode_layout = QHBoxLayout()
        self.meas_button_group = QButtonGroup(self)
        self.radio_dist = QRadioButton("Distance")
        self.radio_dist.setEnabled(False)
        self.radio_dist.setChecked(True)
        self.meas_button_group.addButton(self.radio_dist)
        mode_layout.addWidget(self.radio_dist)
        self.radio_angle = QRadioButton("Angle")
        self.radio_angle.setEnabled(False)
        self.meas_button_group.addButton(self.radio_angle)
        mode_layout.addWidget(self.radio_angle)
        self.radio_text = QRadioButton("Text")
        self.radio_text.setEnabled(False)
        self.meas_button_group.addButton(self.radio_text)
        mode_layout.addWidget(self.radio_text)
        meas_layout.addLayout(mode_layout)
        self.meas_button_group.buttonClicked.connect(
            lambda btn: self.change_measurement_mode(btn.text())
        )

        action_row = QHBoxLayout()
        self.delete_last_btn = QPushButton("Clear Last")
        self.delete_last_btn.clicked.connect(self.delete_last_measurement)
        self.delete_last_btn.setEnabled(False)
        self.delete_last_btn.setMinimumWidth(120)
        action_row.addWidget(self.delete_last_btn, 1)

        action_row.addSpacing(8)

        self.clear_btn = QPushButton("Clear All")
        self.clear_btn.clicked.connect(self.delete_all_measurement)
        self.clear_btn.setEnabled(False)
        self.clear_btn.setMinimumWidth(120)
        action_row.addWidget(self.clear_btn, 1)

        meas_layout.addLayout(action_row)
        control_panel.addWidget(meas_group)

    def toggle_snap(self):
        self.is_frozen = not self.is_frozen
        self.freeze_signal.emit(self.is_frozen)
        self.measurement_signal.emit({"command": "enabled", "value": self.is_frozen})

        if self.is_frozen:
            self.snap_btn.setText("Resume Live View")
        else:
            self.snap_btn.setText("Snap Frame")

        self.clear_btn.setEnabled(self.is_frozen)
        self.delete_last_btn.setEnabled(self.is_frozen)
        self.radio_dist.setEnabled(self.is_frozen)
        self.radio_angle.setEnabled(self.is_frozen)
        self.radio_text.setEnabled(self.is_frozen)
        for button in self.measurement_color_buttons:
            button.setEnabled(self.is_frozen)

    def change_measurement_mode(self, mode_name):
        self.measurement_signal.emit({"command": "mode", "value": mode_name.lower()})

    def change_measurement_color(self, color_name):
        self.measurement_signal.emit({"command": "color", "value": color_name})
        # self.video_widget.set_measurement_color(color_name)
        # if self.selected_color_button is not None:
        #     self.selected_color_button.setStyleSheet(
        #         f"background-color: {self.color_name_to_hex(self.selected_color_button.toolTip())}; "
        #         "border: 1px solid #444; border-radius: 2px;"
        #     )
        # for button in self.measurement_color_buttons:
        #     if button.toolTip() == color_name:
        #         self.selected_color_button = button
        #         button.setStyleSheet(
        #             f"background-color: {self.color_name_to_hex(color_name)}; "
        #             "border: 2px solid #ffffff; border-radius: 2px;"
        #         )
        #         break
        # dispatch status_bar.showMessage(f"Measurement color: {color_name}", STATUS_BAR_MESSAGE_DURATION)

    def delete_last_measurement(self):
        self.measurement_signal.emit({"command": "delete", "value": "last_measurement"})

    def delete_all_measurement(self):
        self.measurement_signal.emit({"command": "delete", "value": "all_measurements"})
