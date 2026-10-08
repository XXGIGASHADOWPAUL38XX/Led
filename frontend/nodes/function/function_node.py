import numpy as np
from PyQt5 import QtCore, QtGui, QtWidgets

from config import FREQ_BINS
from frontend.components.elements.analysable_element import AnalysableElement
from frontend.components.elements.element import Element
from frontend.components.elements.element_value import ElementValue
from frontend.overrides.CNode import CNode


def normalized_points(points) -> np.ndarray:
    points = np.asarray(points if points is not None else (), dtype=float).reshape(-1, 2)
    points = np.vstack((points, [[0.0, 0.0], [1.0, 1.0]]))
    points = np.clip(points, 0.0, 1.0)
    points = points[np.argsort(points[:, 0])]
    _, indices = np.unique(points[:, 0], return_index=True)
    return points[np.sort(indices)]


class FunctionCanvas(QtWidgets.QWidget):
    radius = 6

    def __init__(self, points) -> None:
        super().__init__()
        self.points = normalized_points(points)
        self.selected = None
        self.setMinimumSize(400, 230)

    def paintEvent(self, _event) -> None:
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        rect = self._rect()
        screen_points = self._to_screen(self.points)

        painter.fillRect(self.rect(), QtGui.QColor("#202124"))
        painter.setPen(QtGui.QPen(QtGui.QColor("#555"), 1))
        painter.drawRect(rect)
        painter.setPen(QtGui.QPen(QtGui.QColor("#6db7ff"), 2))
        painter.drawPolyline(QtGui.QPolygonF([QtCore.QPointF(x, y) for x, y in screen_points]))

        painter.setPen(QtGui.QPen(QtGui.QColor("#111"), 1))
        for index, (x, y) in enumerate(screen_points):
            painter.setBrush(QtGui.QColor("#ffcc66" if index == self.selected else "#ffffff"))
            painter.drawEllipse(QtCore.QPointF(x, y), self.radius, self.radius)

    def mousePressEvent(self, event) -> None:
        self.selected = self._nearest(event.pos())
        if event.button() == QtCore.Qt.MouseButton.RightButton:
            self.remove_selected()
        elif self.selected is None:
            self.points = normalized_points(np.vstack((self.points, self._from_screen(event.pos()))))
            self.selected = self._nearest(event.pos())
        self.update()

    def mouseMoveEvent(self, event) -> None:
        if self.selected is None or not event.buttons() & QtCore.Qt.MouseButton.LeftButton:
            return
        point = self._from_screen(event.pos())
        if self.selected in (0, len(self.points) - 1):
            point[0] = float(self.selected == len(self.points) - 1)
        self.points[self.selected] = point
        self.points = normalized_points(self.points)
        self.selected = self._nearest(event.pos())
        self.update()

    def remove_selected(self) -> None:
        if self.selected is not None and len(self.points) > 2:
            self.points = np.delete(self.points, self.selected, axis=0)
            self.selected = None
            self.update()

    def _nearest(self, pos) -> int | None:
        distances = np.abs(self._to_screen(self.points) - np.array([pos.x(), pos.y()])).sum(axis=1)
        index = int(np.argmin(distances))
        return index if distances[index] <= self.radius * 3 else None

    def _rect(self) -> QtCore.QRectF:
        return QtCore.QRectF(18, 12, self.width() - 36, self.height() - 24)

    def _to_screen(self, points: np.ndarray) -> np.ndarray:
        rect = self._rect()
        return np.column_stack((
            rect.left() + points[:, 0] * rect.width(),
            rect.bottom() - points[:, 1] * rect.height(),
        ))

    def _from_screen(self, pos) -> np.ndarray:
        rect = self._rect()
        return np.clip([
            (pos.x() - rect.left()) / rect.width(),
            (rect.bottom() - pos.y()) / rect.height(),
        ], 0.0, 1.0)


class FunctionEditor(QtWidgets.QDialog):
    def __init__(self, points, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Function")
        self.setFixedSize(420, 300)
        self.canvas = FunctionCanvas(points)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.addWidget(self.canvas)

        buttons = QtWidgets.QHBoxLayout()
        for label, slot in (("Remove point", self.canvas.remove_selected), ("Done", self.accept)):
            button = QtWidgets.QPushButton(label)
            button.clicked.connect(slot)
            buttons.addWidget(button)
        layout.addLayout(buttons)


class FunctionNode(CNode):
    """Generate an editable piecewise-linear spatial curve.

    Inputs `input_data` and `number_points` determine the output `data` shape;
    input_data values are not transformed. Configure normalized (x, y)
    `points`. With an array input, the curve spans its first axis and repeats
    across trailing dimensions; otherwise it is a number_points vector.
    Regenerates on input changes or accepted curve edits."""

    nodeName = "Function"

    def __init__(
        self,
        input_data: np.ndarray | None = None,
        number_points: int = FREQ_BINS,
        points: list[tuple[float, float]] | np.ndarray | None = None,
        render: bool = True,
        alias: str | None = None,
    ) -> None:
        super().__init__(
            self.nodeName,
            {"input_data": {"io": "in"}, "number_points": {"io": "in"}, "data": {"io": "out"}},
            render,
            alias=alias,
        )
        self.input_data = Element(self, "input_data", ElementValue(input_data))
        self.number_points = Element(self, "number_points", ElementValue(number_points))
        self.points = Element(self, "points", ElementValue(normalized_points(points)), link_terminal=False)
        self.data = AnalysableElement(self, "data", ElementValue(np.zeros(self._data_shape())))

        self.edit_button = QtWidgets.QPushButton("Edit")
        self.edit_button.clicked.connect(self.open_editor)
        self.points.container_vchange_layout.addWidget(self.edit_button)

        self.number_points.valueChanged.connect(self._refresh_data)
        self.input_data.valueChanged.connect(self._refresh_data)
        self._refresh_data()

    def open_editor(self) -> None:
        dialog = FunctionEditor(self.points.value, self.edit_button)
        if dialog.exec_() == QtWidgets.QDialog.DialogCode.Accepted:
            self.points.value = dialog.canvas.points
            self._refresh_data()

    def _refresh_data(self, *_args) -> None:
        shape = self._data_shape()
        size = shape[0] if shape else 0
        points = normalized_points(self.points.value)
        data = np.interp(np.linspace(0.0, 1.0, size), points[:, 0], points[:, 1])
        self.data.value = np.broadcast_to(data.reshape(-1, *([1] * (len(shape) - 1))), shape).copy()

    def _data_shape(self) -> tuple[int, ...]:
        input_data = self.input_data.value
        if isinstance(input_data, np.ndarray):
            return input_data.shape
        return (max(0, int(self.number_points.value)),)
