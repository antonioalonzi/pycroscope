from PyQt6.QtCore import QSettings


class AppSettings:
    def __init__(self, organization="aa", application="Pycroscope"):
        self._settings = QSettings(organization, application)
        self.last_device = self._settings.value("last_device", "")
        self.save_dir = self._settings.value("save_dir", "~/Pictures")
        self.pitch_spin = self._settings.value("pitch_spin", 3.75, type=float)
        self.obj_spin = self._settings.value("obj_spin", 10.0, type=float)
        self.cmount_spin = self._settings.value("cmount_spin", 0.5, type=float)
        self.geometry = self._settings.value("geometry")
        self.window_state = self._settings.value("window_state")

    def set_last_device(self, last_device):
        self.last_device = last_device
        self._settings.setValue("last_device", last_device)

    def set_save_dir(self, save_dir):
        self.save_dir = save_dir
        self._settings.setValue("save_dir", save_dir)

    def set_pitch_spin(self, pitch_spin):
        self.pitch_spin = pitch_spin
        self._settings.setValue("pitch_spin", pitch_spin)

    def set_obj_spin(self, obj_spin):
        self.obj_spin = obj_spin
        self._settings.setValue("obj_spin", obj_spin)

    def set_cmount_spin(self, cmount_spin):
        self.cmount_spin = cmount_spin
        self._settings.setValue("cmount_spin", cmount_spin)

    def set_geometry(self, geometry):
        self.geometry = geometry
        self._settings.setValue("geometry", geometry)

    def set_window_state(self, window_state):
        self.window_state = window_state
        self._settings.setValue("window_state", window_state)

