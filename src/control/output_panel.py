import os

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QVBoxLayout, QGroupBox, QLabel, QPushButton, QFileDialog, QWidget

from src.settings.app_settings import AppSettings


class OutputPanel(QWidget):
    save_signal = pyqtSignal(str)

    def __init__(self, control_panel: QVBoxLayout, settings: AppSettings):
        super().__init__()

        self.control_panel = control_panel
        self.settings = settings

        cap_group = QGroupBox("Output")
        cap_layout = QVBoxLayout(cap_group)
        self.folder_btn = QPushButton("Select Output Directory")
        self.folder_btn.clicked.connect(self.choose_folder)
        cap_layout.addWidget(self.folder_btn)

        self.dir_label = QLabel()
        self.dir_label.setWordWrap(True)
        self.dir_label.setStyleSheet("color: #AAA;")
        self.dir_label.setText(f"Output Directory: {os.path.basename(os.path.normpath(self.settings.save_dir))}")
        cap_layout.addWidget(self.dir_label)

        self.save_meas_btn = QPushButton("Save")
        self.save_meas_btn.setStyleSheet("font-weight: bold; font-size: 14px;")
        self.save_meas_btn.clicked.connect(self.save_image)
        cap_layout.addWidget(self.save_meas_btn)

        control_panel.addWidget(cap_group)

    def choose_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Save Directory", self.settings.save_dir)
        if folder:
            folder_name = os.path.basename(os.path.normpath(folder))
            self.dir_label.setText(f"Output Directory: {folder_name}")
            self.settings.set_save_dir(folder)

    def save_image(self):
        self.save_signal.emit(self.settings.save_dir)
