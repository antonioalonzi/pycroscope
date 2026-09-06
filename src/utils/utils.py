import math

import cv2
from PyQt6.QtGui import QImage, QPixmap


def calculate_scale(pitch_um: float, objective_mag: float, cmount_mag: float) -> float:
    """Calculates spatial scale in um per pixel."""
    total_mag = objective_mag * cmount_mag
    return pitch_um / total_mag if total_mag > 0 else 1.0


def calculate_distance(p1: tuple, p2: tuple, scale_um_px: float) -> tuple[float, str]:
    """Returns (pixel_distance, formatted_physical_string)."""
    pixel_dist = math.hypot(p2[0] - p1[0], p2[1] - p1[1])
    real_dist_um = pixel_dist * scale_um_px

    if real_dist_um >= 1000:
        formatted = f"{real_dist_um / 1000.0:.2f} mm"
    else:
        formatted = f"{real_dist_um:.2f} µm"

    return pixel_dist, formatted


def cv_to_qpixmap(frame) -> QPixmap:
    """Converts an OpenCV BGR frame to Qt QPixmap."""
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    h, w, ch = rgb_frame.shape
    qt_img = QImage(rgb_frame.data, w, h, ch * w, QImage.Format.Format_RGB888)
    return QPixmap.fromImage(qt_img)
