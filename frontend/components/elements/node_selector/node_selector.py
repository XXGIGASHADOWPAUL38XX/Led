from typing import Callable, Sequence, List

from PyQt5 import QtCore, QtWidgets

from frontend.components.elements.element import Element
from frontend.components.elements.element_value import ElementValue
from frontend.overrides.CComboBox import CComboBox
from frontend.overrides.CNode import CNode

class NodeSelector(Element):
    def __init__(
        self,
        node: CNode,
        name: str,
        value: object = None,
        selection_nodes: Sequence[CNode] | Callable[[], Sequence[CNode]] = [],
        selection_elements: Sequence[str] | Callable[[], Sequence[str]] = [],
        **kwargs: object,
    ) -> None:
        initial_element = value
        while isinstance(initial_element, ElementValue):
            initial_element = initial_element.value
        if not isinstance(initial_element, Element):
            initial_element = None

        super().__init__(node, name, value, **kwargs)
        self.selection_nodes = ElementValue(selection_nodes)
        self.selection_elements = ElementValue(selection_elements)

        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_TranslucentBackground, True)

        self.controls_container = QtWidgets.QWidget()
        self.controls_layout = QtWidgets.QHBoxLayout(self.controls_container)
        self.controls_layout.setContentsMargins(0, 0, 0, 0)
        self.controls_layout.setSpacing(4)

        self.selection_nodes_combobox = CComboBox()
        self.selection_nodes_combobox.setFixedSize(100, 20)
        self.selection_nodes_combobox.setContentsMargins(0, 0, 0, 0)
        self.selection_nodes_combobox.setMinimumContentsLength(10)
        self.selection_nodes_combobox.view().setTextElideMode(QtCore.Qt.TextElideMode.ElideRight)
        self.selection_nodes_combobox.addItems(["null"])
        self.selection_nodes_combobox.popupAboutToShow.connect(self.refresh_selection_nodes)
        self.selection_nodes_combobox.currentIndexChanged.connect(self.set_node_value)
        self.controls_layout.addWidget(self.selection_nodes_combobox)

        self.selected_node: CNode | None = None
        self.selected_elements: List[Element | None] = []

        self.selection_elements_combobox = CComboBox()
        self.selection_elements_combobox.setFixedSize(100, 20)
        self.selection_elements_combobox.setContentsMargins(0, 0, 0, 0)
        self.selection_elements_combobox.setSizeAdjustPolicy(QtWidgets.QComboBox.SizeAdjustPolicy.AdjustToContents)
        self.selection_elements_combobox.setMinimumContentsLength(10)
        self.selection_elements_combobox.view().setTextElideMode(QtCore.Qt.TextElideMode.ElideRight)
        self.selection_elements_combobox.addItems(["null"] + self.selection_elements.value)
        self.selection_elements_combobox.currentIndexChanged.connect(self.set_element_value)
        self.controls_layout.addWidget(self.selection_elements_combobox)

        self.selected_element = None

        self.container_vchange_layout.addWidget(self.controls_container)
        if initial_element is not None:
            self.set_default_element(initial_element)

    def _is_pointer_over_selector(self, scene_pos=None):
        if scene_pos is None:
            return False
        proxy = getattr(self.node, "_elements_proxy", None)
        if proxy is None or proxy.widget() is None:
            return False
        local_pos = proxy.mapFromScene(scene_pos)
        widget = proxy.widget().childAt(int(local_pos.x()), int(local_pos.y()))
        return widget is self or (widget is not None and self.isAncestorOf(widget))

    def _set_drop_hover(self, hovered):
        super()._set_drop_hover(hovered)

    def _set_element_from_terminal(self, terminal):
        owner = getattr(terminal.node(), "obj", terminal.node())
        element_name = owner.terminal_element_name(terminal.name())
        element = getattr(owner, element_name, None)
        if isinstance(element, Element):
            self.set_default_element(element)

    def extract_selection_node_names(self):
        return list(map(lambda x: x.name(), self.selection_nodes.value))

    def extract_selection_element_names(self):
        return list(map(
            lambda x: x.name,
            self.selected_elements
        ))

    def refresh_selection_nodes(self):
        selected_text = self.selection_nodes_combobox.currentText()
        node_names = ["null"] + self.extract_selection_node_names()
        if self.selected_node is not None and self.selected_node.name() not in node_names:
            node_names.append(self.selected_node.name())
        self.selection_nodes_combobox.blockSignals(True)
        self.selection_nodes_combobox.clear()
        self.selection_nodes_combobox.addItems(node_names)
        if selected_text in node_names:
            self.selection_nodes_combobox.setCurrentText(selected_text)
        self.selection_nodes_combobox.blockSignals(False)

    def set_node_value(self, item):
        if item == 0:
            self.selected_node = None
            self.selected_elements = []
            self.selection_elements_combobox.clear()
            self.selection_elements_combobox.addItems(["null"])
            self.set_element_value(0)
            return
        else:
            self.selection_nodes_combobox.currentIndexChanged.disconnect(self.set_node_value)
            selection_nodes = self.selection_nodes.value
            self.selected_node = (
                selection_nodes[item - 1]
                if item - 1 < len(selection_nodes)
                else self.selected_node
            )
            self.selected_elements = [element for element in self.selected_node.elements if isinstance(element, Element) and (not self.selection_elements.value or element.name in self.selection_elements.value)]
            self.selection_elements_combobox.clear()

        element_names = ["null"] + self.extract_selection_element_names()
        self.selection_elements_combobox.addItems(element_names)
        self.selection_nodes_combobox.currentIndexChanged.connect(self.set_node_value)
        self.set_element_value(0)

    def set_element_value(self, element_total):
        element = self.selected_elements[element_total - 1] if element_total > 0 else None
        self._set_selected_element(element)

    def _set_selected_element(self, element):
        self.selected_element = element
        terminal_name = self.name.lower()
        if self.link_terminal and terminal_name in self.node.terminals:
            target = self.node[terminal_name]
            if element is None or not target.connectedTo(element.node[element.name.lower()]):
                target.disconnectAll()
                if element is not None:
                    self.connect_terminal(element)
        self.value = element

    def set_default_element(self, element):
        if element is None:
            self.selection_nodes_combobox.setCurrentIndex(0)
            self._set_selected_element(None)
            return
        self.selected_node = element.node
        self.selected_elements = [element for element in self.selected_node.elements if isinstance(element, Element) and (not self.selection_elements.value or element.name in self.selection_elements.value)]
        self.selected_element = element

        self.refresh_selection_nodes()
        self.selection_nodes_combobox.blockSignals(True)
        self.selection_nodes_combobox.setCurrentText(self.selected_node.name())
        self.selection_nodes_combobox.blockSignals(False)

        element_names = ["null"] + self.extract_selection_element_names()
        self.selection_elements_combobox.blockSignals(True)
        self.selection_elements_combobox.clear()
        self.selection_elements_combobox.addItems(element_names)
        self.selection_elements_combobox.setCurrentText(element.name)
        self.selection_elements_combobox.blockSignals(False)
        self._set_selected_element(element)

    def eventFilter(self, watched, event):
        super().eventFilter(watched, event)
        if event.type == QtCore.QEvent.Type.GraphicsSceneMouseRelease and self._dragged_terminal is not None:
            if self._is_pointer_over_selector(event.scenePos()):
                self._set_element_from_terminal(self._dragged_terminal)
            self._dragged_terminal = None
            self._set_drop_hover(False)
        return False


    def after_ui_init(self, placeholder_element):
        self.set_default_element(placeholder_element.selected_element)
