from __future__ import annotations

from collections.abc import Iterable

from PyQt5 import QtCore, QtGui, QtWidgets

from config import NODE_LAYOUT_X_GAP
from frontend.overrides.CNode import CNode


class GroupNode(CNode):
    """Arrange related nodes inside a titled visual group.

    Configure `nodes`, title, padding, color, and `hide_node`; optional
    `terminals` are defined by subclasses. `draw()` opens child charts and
    `start()` starts `auto_start_nodes`. Grouping itself does not process
    signals; concrete subclasses expose outputs from their child pipelines."""

    nodeName = "GroupNode"
    is_group_node = True

    def __init__(
        self,
        nodes: Iterable[CNode | str] | None = None,
        auto_start_nodes: Iterable[CNode] | None = None,
        terminals: dict | None = None,
        title: str = "Group",
        padding: float = 0.05,
        color: tuple[int, int, int] = (120, 120, 120),
        hide_node: bool = True,
        render: bool = True,
        alias: str | None = None,
    ) -> None:
        super().__init__(self.nodeName, terminals=terminals or {}, render=render, alias=alias)
        self.hide_node = hide_node
        if self.hide_node:
            self.graphicsItem().hide()
        self.title = title
        self.padding = float(padding)
        self.color = color
        self._rect_item = None
        self._title_item = None
        self._update_timer = None
        self.nodes = list(nodes or [])
        self.auto_start_nodes = list(auto_start_nodes or [])
        QtCore.QTimer.singleShot(0, self.attach_to_scene)

    def attach_to_scene(self):
        scene = self.graphicsItem().scene()
        if scene is None:
            QtCore.QTimer.singleShot(0, self.attach_to_scene)
            return
        view_box = self.graphicsItem().getViewBox()
        if view_box is None:
            QtCore.QTimer.singleShot(0, self.attach_to_scene)
            return

        if self.hide_node:
            self.graphicsItem().hide()
        self._attach_internal_nodes(view_box)

        if self._rect_item is None:
            pen = QtGui.QPen(QtGui.QColor(*self.color))
            pen.setWidth(2)
            pen.setStyle(QtCore.Qt.PenStyle.DotLine)
            self._rect_item = QtWidgets.QGraphicsRectItem()
            self._rect_item.setPen(pen)
            self._rect_item.setBrush(QtGui.QBrush(QtCore.Qt.BrushStyle.NoBrush))
            self._rect_item.setZValue(-100)
            scene.addItem(self._rect_item)

        if self._title_item is None:
            self._title_item = QtWidgets.QGraphicsTextItem(self.title)
            self._title_item.setDefaultTextColor(QtGui.QColor(*self.color))
            self._title_item.setZValue(-99)
            scene.addItem(self._title_item)

        if self._update_timer is None:
            self._update_timer = QtCore.QTimer()
            self._update_timer.timeout.connect(self.update_bounds)
            self._update_timer.start(250)

        self.update_bounds()

    def _attach_internal_nodes(self, view_box):
        for node in self._resolved_nodes():
            item = node.graphicsItem()
            if item.scene() is None:
                view_box.addItem(item)
            item.show()
        self._layout_internal_nodes()

    def _layout_internal_nodes(self):
        x = self.graphicsItem().pos().x()
        y = self.graphicsItem().pos().y() + self.graphicsItem().boundingRect().height() + 80.0
        x_gap = float(NODE_LAYOUT_X_GAP)
        for node in self._resolved_nodes():
            item = node.graphicsItem()
            item.setPos(x, y)
            x += max(float(item.boundingRect().width()), 180.0) + x_gap

    def update_bounds(self):
        if self._rect_item is None:
            return

        self._layout_internal_nodes()
        rect = self._group_rect()
        if rect is None:
            self._rect_item.hide()
            if self._title_item is not None:
                self._title_item.hide()
            return

        self._rect_item.setRect(rect)
        self._rect_item.show()
        if self._title_item is not None:
            self._title_item.setPlainText(self.title)
            self._title_item.setPos(rect.left(), rect.top() - max(20.0, rect.height() * 0.03))
            self._title_item.show()

    def _group_rect(self):
        rect = None
        for node in self._resolved_nodes():
            item = node.graphicsItem()
            node_rect = item.mapRectToScene(item.boundingRect())
            rect = node_rect if rect is None else rect.united(node_rect)

        if rect is None:
            return None

        x_padding = rect.width() * self.padding
        y_padding = rect.height() * self.padding
        return rect.adjusted(-x_padding, -y_padding, x_padding, y_padding)

    def _resolved_nodes(self):
        return [node for node in self.nodes if isinstance(node, CNode)]

    def draw(self):
        windows = []
        for node in self._resolved_nodes():
            if callable(getattr(node, "draw", None)):
                windows.append(node.draw())
        return windows[-1] if windows else None

    def start(self):
        for node in self.auto_start_nodes:
            node.start()
