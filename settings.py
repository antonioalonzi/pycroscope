from PyQt6.QtCore import QSettings


class AppSettings:
    def __init__(self, organization="MicroscopeLab", application="VisionWorkbench"):
        self._settings = QSettings(organization, application)
        self.last_device = self._settings.value("last_device", "")
        self.save_dir = self._settings.value("save_dir", "~/Pictures")
        self.geometry = self._settings.value("geometry")
        self.window_state = self._settings.value("window_state")

    def set_last_device(self, last_device):
        self.last_device = last_device
        self._settings.setValue("last_device", last_device)

    def set_save_dir(self, save_dir):
        self.save_dir = save_dir
        self._settings.setValue("save_dir", save_dir)

    def set_geometry(self, geometry):
        self.geometry = geometry
        self._settings.setValue("geometry", geometry)

    def set_window_state(self, window_state):
        self.window_state = window_state
        self._settings.setValue("window_state", window_state)

