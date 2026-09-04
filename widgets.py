import cv2
from PyQt6.QtCore import Qt, pyqtSignal, QPointF
from PyQt6.QtWidgets import QLabel

from utils import calculate_distance, cv_to_qpixmap


class VideoWidget(QLabel):
    """Custom view for live rendering and interactive measurement vector overlays."""
    point_clicked = pyqtSignal(QPointF)

    def __init__(self):
        super().__init__()
        self.setMinimumSize(640, 480)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setStyleSheet("background-color: #1e1e1e; border: 1px solid #333;")

        self.current_frame = None
        self.measurements = []
        self.pending_point = None
        self.points = []
        self.scale_um_per_px = 1.0
        self.measurement_enabled = False

    def set_measurement_enabled(self, enabled):
        self.measurement_enabled = enabled
        if not enabled:
            self.clear_points()

    def set_frame(self, frame):
        self.current_frame = frame
        self.update_display()

    def _sync_points(self):
        points = []
        for start, end in self.measurements:
            points.extend([start, end])
        if self.pending_point is not None:
            points.append(self.pending_point)
        self.points = points

    def add_measurement_point(self, point):
        if self.pending_point is not None:
            self.measurements.append((self.pending_point, point))
            self.pending_point = None
        else:
            self.pending_point = point
        self._sync_points()
        self.update_display()

    def delete_last_measurement(self):
        if self.pending_point is not None:
            self.pending_point = None
        elif self.measurements:
            self.measurements.pop()
        self._sync_points()
        self.update_display()

    def delete_measurement(self, index=None):
        if index is None:
            index = len(self.measurements) - 1

        if 0 <= index < len(self.measurements):
            self.measurements.pop(index)
            self._sync_points()
            self.update_display()

    def mousePressEvent(self, event):
        if not self.measurement_enabled:
            return

        if event.button() == Qt.MouseButton.LeftButton and self.pixmap():
            pm_size = self.pixmap().size()
            lbl_size = self.size()

            scaled_w, scaled_h = pm_size.width(), pm_size.height()
            x_offset = (lbl_size.width() - scaled_w) / 2
            y_offset = (lbl_size.height() - scaled_h) / 2

            click_x = event.position().x() - x_offset
            click_y = event.position().y() - y_offset

            if 0 <= click_x <= scaled_w and 0 <= click_y <= scaled_h:
                if self.current_frame is not None:
                    orig_h, orig_w = self.current_frame.shape[:2]
                    img_x = (click_x / scaled_w) * orig_w
                    img_y = (click_y / scaled_h) * orig_h
                    self.add_measurement_point((img_x, img_y))

    def clear_points(self):
        self.measurements.clear()
        self.pending_point = None
        self._sync_points()
        self.update_display()

    def update_display(self):
        if self.current_frame is None:
            return

        frame = self.current_frame.copy()

        if self.pending_point is not None:
            p1 = (int(self.pending_point[0]), int(self.pending_point[1]))
            cv2.circle(frame, p1, 5, (0, 0, 255), -1)

        for start, end in self.measurements:
            p1 = (int(start[0]), int(start[1]))
            p2 = (int(end[0]), int(end[1]))

            cv2.circle(frame, p1, 5, (0, 0, 255), -1)
            cv2.circle(frame, p2, 5, (0, 0, 255), -1)
            cv2.line(frame, p1, p2, (0, 255, 0), 2)

            _, label_text = calculate_distance(start, end, self.scale_um_per_px)

            mid_x = int((p1[0] + p2[0]) / 2)
            mid_y = int((p1[1] + p2[1]) / 2) - 10
            cv2.putText(frame, label_text, (mid_x, mid_y),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

        pixmap = cv_to_qpixmap(frame)
        self.setPixmap(pixmap.scaled(self.size(), Qt.AspectRatioMode.KeepAspectRatio,
                                     Qt.TransformationMode.SmoothTransformation))
