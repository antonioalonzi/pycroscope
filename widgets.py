import math

import cv2
from PyQt6.QtCore import Qt, pyqtSignal, QPointF
from PyQt6.QtWidgets import QLabel, QInputDialog

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
        self.text_annotations = []
        self.pending_points = []
        self.pending_text = None
        self.points = []
        self.scale_um_per_px = 1.0
        self.measurement_enabled = False
        self.measurement_mode = "distance"

    def set_measurement_enabled(self, enabled):
        self.measurement_enabled = enabled
        if enabled:
            self.setCursor(Qt.CursorShape.CrossCursor)
        else:
            self.unsetCursor()
            self.clear_points()

    def set_measurement_mode(self, mode):
        if mode not in {"distance", "angle", "text"}:
            return
        self.measurement_mode = mode
        self.pending_points = []
        self.pending_text = None
        self._sync_points()
        self.update_display()
        if self.measurement_enabled:
            self.setCursor(Qt.CursorShape.CrossCursor)

    def begin_text_annotation(self, text):
        if not self.measurement_enabled or not text:
            return
        self.pending_text = text
        self.update_display()

    def set_frame(self, frame):
        self.current_frame = frame
        self.update_display()

    def _sync_points(self):
        self.points = []
        for measurement in self.measurements:
            self.points.extend(measurement["points"])
        self.points.extend(self.pending_points)

    def add_measurement_point(self, point):
        if self.pending_text is not None:
            self.text_annotations.append({"text": self.pending_text, "x": point[0], "y": point[1]})
            self.pending_text = None
            self.update_display()
            return

        if self.measurement_mode == "distance":
            if len(self.pending_points) >= 1:
                self.measurements.append({"type": "distance", "points": [self.pending_points[0], point]})
                self.pending_points = []
            else:
                self.pending_points = [point]
        else:
            if len(self.pending_points) >= 3:
                self.pending_points = []
            self.pending_points.append(point)
            if len(self.pending_points) == 3:
                self.measurements.append({"type": "angle", "points": list(self.pending_points)})
                self.pending_points = []

        self._sync_points()
        self.update_display()

    def clear_last_edit(self):
        if self.pending_text is not None:
            self.pending_text = None
        elif self.pending_points:
            self.pending_points.pop()
        elif self.measurements:
            self.measurements.pop()
        elif self.text_annotations:
            self.text_annotations.pop()
        self._sync_points()
        self.update_display()

    def delete_last_measurement(self):
        if self.pending_text is not None:
            self.pending_text = None
        elif self.pending_points:
            self.pending_points.pop()
        elif self.measurements:
            self.measurements.pop()
        elif self.text_annotations:
            self.text_annotations.pop()
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

                    if self.measurement_mode == "text":
                        label_text, ok = QInputDialog.getText(self, "Add Label", "Text:")
                        if ok and label_text.strip():
                            self.text_annotations.append({"text": label_text.strip(), "x": img_x, "y": img_y})
                            self.update_display()
                        return

                    self.add_measurement_point((img_x, img_y))

    def clear_points(self):
        self.measurements.clear()
        self.text_annotations.clear()
        self.pending_points = []
        self.pending_text = None
        self._sync_points()
        self.update_display()

    def _draw_distance(self, frame, p1, p2, label):
        cv2.circle(frame, p1, 3, (0, 180, 255), -1)
        cv2.circle(frame, p2, 3, (0, 180, 255), -1)
        cv2.line(frame, p1, p2, (0, 255, 128), 1)

        mid_x = int((p1[0] + p2[0]) / 2)
        mid_y = int((p1[1] + p2[1]) / 2) - 10
        cv2.putText(frame, label, (mid_x, mid_y),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 128), 1)

    def _draw_angle(self, frame, p1, p2, p3, label):
        cv2.circle(frame, p1, 3, (0, 180, 255), -1)
        cv2.circle(frame, p2, 3, (0, 180, 255), -1)
        cv2.circle(frame, p3, 3, (0, 180, 255), -1)
        cv2.line(frame, p2, p1, (0, 255, 128), 1)
        cv2.line(frame, p2, p3, (0, 255, 128), 1)

        label_x = int((p1[0] + p2[0] + p3[0]) / 3)
        label_y = int((p1[1] + p2[1] + p3[1]) / 3) - 12
        cv2.putText(frame, label, (label_x, label_y),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 128), 1)

    def update_display(self):
        if self.current_frame is None:
            return

        frame = self.current_frame.copy()

        if self.pending_text is not None:
            cv2.putText(frame, f"Text: {self.pending_text}", (12, 26),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1, cv2.LINE_AA)

        for point in self.pending_points:
            p = (int(point[0]), int(point[1]))
            cv2.circle(frame, p, 3, (0, 180, 255), -1)

        for measurement in self.measurements:
            points = [(int(pt[0]), int(pt[1])) for pt in measurement["points"]]
            if measurement["type"] == "distance":
                p1, p2 = points
                _, label_text = calculate_distance(measurement["points"][0], measurement["points"][1], self.scale_um_per_px)
                self._draw_distance(frame, p1, p2, label_text)

            elif measurement["type"] == "angle":
                p1, p2, p3 = points
                v1 = (p1[0] - p2[0], p1[1] - p2[1])
                v2 = (p3[0] - p2[0], p3[1] - p2[1])
                dot = v1[0] * v2[0] + v1[1] * v2[1]
                mag1 = math.hypot(*v1)
                mag2 = math.hypot(*v2)
                angle = 0.0
                if mag1 > 0 and mag2 > 0:
                    cos_theta = max(-1.0, min(1.0, dot / (mag1 * mag2)))
                    angle = math.degrees(math.acos(cos_theta))
                label_text = f"{angle:.1f}°"
                self._draw_angle(frame, p1, p2, p3, label_text)

        for annotation in self.text_annotations:
            cv2.putText(frame, annotation["text"], (int(annotation["x"]), int(annotation["y"])),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1, cv2.LINE_AA)

        pixmap = cv_to_qpixmap(frame)
        self.setPixmap(pixmap.scaled(self.size(), Qt.AspectRatioMode.KeepAspectRatio,
                                     Qt.TransformationMode.SmoothTransformation))
