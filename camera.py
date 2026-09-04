import cv2
import numpy as np
from PyQt6.QtCore import QThread, pyqtSignal

class VideoThread(QThread):
    """Background thread for non-blocking V4L2 frame acquisition."""
    frame_signal = pyqtSignal(np.ndarray)

    def __init__(self, device_path=0):
        super().__init__()
        self.device_path = device_path
        self.running = True

    def run(self):
        backend = cv2.CAP_V4L2 if isinstance(self.device_path, str) else cv2.CAP_ANY
        cap = cv2.VideoCapture(self.device_path, backend)

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
