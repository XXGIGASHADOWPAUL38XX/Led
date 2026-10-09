import inspect
import weakref

import networkx as nx
from PyQt5 import QtCore
from pyqtgraph.debug import printExc
from pyqtgraph.flowchart import Flowchart
from pyqtgraph.flowchart.Node import Node
from pyqtgraph.flowchart.Terminal import TerminalGraphicsItem

from backend.updatable.updatable import pause_updates, audio_updatable_objects, visual_updatable_objects
from config import NODE_LAYOUT_X_GAP, NODE_LAYOUT_Y_GAP
from frontend.components.elements.element import Element
from frontend.components.ui.create_node_form import CreateNodeForm
from frontend.overrides.CNode import CNode
from frontend.overrides.node_style import GRAPH_STYLESHEET
from frontend.ui_features.add_node import AddNodeFeature


class CFlowchart(Flowchart):
    PAUSE_EVENTS = (
        QtCore.QEvent.Type.MouseButtonPress,
        QtCore.QEvent.Type.MouseButtonRelease,
        QtCore.QEvent.Type.KeyPress,
        QtCore.QEvent.Type.Wheel,
    )

    def __init__(self, nodes=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._drag_elements = weakref.WeakSet()
        self._dragged_terminal = None
        QtCore.QCoreApplication.instance().installEventFilter(self)
        self.widget().setStyleSheet(GRAPH_STYLESHEET)
        self.add_node_feature = AddNodeFeature(self)
        # getattr(self.widget(), "chartWidget", self.widget()).setBackground("#171819")
        self.widget().installEventFilter(self)
        self.inputNode.graphicsItem().hide()
        self.outputNode.graphicsItem().hide()

        self.add_nodes(nodes or [])
        self.visible_nodes = self.get_visible_nodes()
        QtCore.QTimer.singleShot(0, lambda: self.place_nodes())

    def eventFilter(self, obj, event):
        if event.type() == QtCore.QEvent.Type.GraphicsSceneMousePress and event.button() == QtCore.Qt.MouseButton.LeftButton:
            element = next(iter(self._drag_elements), None)
            scene = element.node.graphicsItem().scene() if element is not None else None
            for item in scene.items(event.scenePos()) if scene is not None else []:
                if isinstance(item, TerminalGraphicsItem):
                    self._dragged_terminal = item.term
                    break
        elif event.type() == QtCore.QEvent.Type.GraphicsSceneMouseMove and self._dragged_terminal is not None:
            incoming = Element._element_from_terminal(self._dragged_terminal)
            for element in self._drag_elements:
                element._set_drop_hover(incoming is not None and element.check_connect_by_drag(incoming))
        elif event.type() == QtCore.QEvent.Type.GraphicsSceneMouseRelease and self._dragged_terminal is not None:
            for element in self._drag_elements:
                if element._is_pointer_over_selector(event.scenePos()):
                    element._set_element_from_terminal(self._dragged_terminal)
                    break
            for element in self._drag_elements:
                element._set_drop_hover(False)
            self._dragged_terminal = None
        if event.type() in self.PAUSE_EVENTS:
            pause_updates()
        return False

    def createNode(self, nodeType, name=None, pos=None, ctor_kwargs=None):
        needs_setup_form = name is None
        name = name or self._next_node_name(nodeType)

        node_cls = self.library.getNodeType(nodeType)
        node = node_cls(**self._node_init_kwargs(node_cls, name, ctor_kwargs))

        if needs_setup_form and not self.display_create_node_form(node):
            return None

        if hasattr(node, "rename") and node.name() != name:
            node.rename(name)
        if hasattr(node, "alias"):
            node.alias = name
        self.addNode(node, name, pos)
        if hasattr(node, "init_all"):
            node.init_all()
            self._drag_elements.update(element for element in node.elements if isinstance(element, Element))
        draw = getattr(node, "draw", None)
        if callable(draw):
            QtCore.QTimer.singleShot(0, draw)
        return node

    def _next_node_name(self, node_type):
        index = 0
        while f"{node_type}.{index}" in self._nodes:
            index += 1
        return f"{node_type}.{index}"

    @staticmethod
    def _node_init_kwargs(node_cls, name, ctor_kwargs=None):
        init_kwargs = {"render": False, **(ctor_kwargs or {})}
        signature_parameters = inspect.signature(node_cls.__init__).parameters
        if "alias" in signature_parameters:
            init_kwargs.setdefault("alias", name)
        return {key: value for key, value in init_kwargs.items() if key in signature_parameters}

    def restoreState(self, state, clear=False):
        audio_updatable_objects.clear()
        visual_updatable_objects.clear()
        self.blockSignals(True)
        try:
            if clear:
                self.clear()
            Node.restoreState(self, state)
            nodes = state["nodes"]
            nodes.sort(key=lambda a: a["pos"][0])
            pending_nodes = list(nodes)
            while pending_nodes:
                progressed = False
                next_pending = []

                for node_state in pending_nodes:
                    name = node_state["name"]
                    if name in self._nodes:
                        self._nodes[name].restoreState(node_state["state"])
                        progressed = True
                        continue

                    try:
                        node = self._restore_node(node_state)
                        if node is None:
                            next_pending.append(node_state)
                            continue

                        progressed = True
                    except Exception:
                        printExc("Error creating node %s: (continuing anyway)" % name)
                        progressed = True

                if not progressed:
                    break
                pending_nodes = next_pending

            self.inputNode.restoreState(state.get("inputNode", {}))
            self.outputNode.restoreState(state.get("outputNode", {}))

            self._connect_saved_terminals(state["connects"])
        finally:
            self.blockSignals(False)

        self.outputChanged()
        self.sigChartLoaded.emit()
        self.sigStateChanged.emit()

    def _restore_node(self, node_state):
        ctor_kwargs = self._ctor_kwargs_from_state(node_state.get("state", {}))
        if ctor_kwargs is None:
            return None

        node = self.createNode(node_state["class"], node_state["name"], node_state["pos"], ctor_kwargs)
        node.restoreState(node_state["state"])
        return node

    def _ctor_kwargs_from_state(self, state):
        ctor_kwargs = {
            key: CNode.deserialize_state_value(value)
            for key, value in state.get("ctor_kwargs", {}).items()
        }

        if not self._resolve_init_refs(ctor_kwargs, state.get("init_refs", {})):
            return None

        if (arguments := state.get("arguments")) is not None:
            if (arguments := self._resolve_arguments(arguments)) is None:
                return None
            ctor_kwargs["arguments"] = arguments

        return ctor_kwargs

    def _resolve_init_refs(self, ctor_kwargs, init_refs):
        for parameter_name, payload in init_refs.items():
            if (element := self._resolve_element_ref(payload.get("__element_ref__", {}))) is None:
                return False
            ctor_kwargs[parameter_name] = element
        return True

    def _resolve_arguments(self, arguments):
        resolved = []
        for arg in arguments:
            if isinstance(arg, dict) and "__element_ref__" in arg:
                element = self._resolve_element_ref(arg["__element_ref__"])
                if element is None:
                    return None
                resolved.append(element)
            else:
                resolved.append(CNode.deserialize_state_value(arg))
        return resolved

    def _resolve_element_ref(self, ref):
        src_node = self._nodes.get(ref.get("node_name"))
        element_name = ref.get("element_name")
        if src_node is None or not hasattr(src_node, element_name):
            return None
        return getattr(src_node, element_name)

    def _connect_saved_terminals(self, connects):
        for n1, t1, n2, t2 in connects:
            try:
                node1 = self._nodes.get(n1)
                node2 = self._nodes.get(n2)
                if node1 is not None and node2 is not None and t1 in node1.terminals and t2 in node2.terminals:
                    self.connectTerminals(node1[t1], node2[t2])
            except Exception:
                printExc("Error connecting terminals %s.%s - %s.%s:" % (n1, t1, n2, t2))

    def add_nodes(self, nodes):
        for node in nodes:
            self.add_node(node)

    def add_node(self, node, name=None, pos=None):
        if name is None and hasattr(node, "name"):
            name = node.name()
        self.addNode(node, name, pos)
        self._drag_elements.update(element for element in node.elements if isinstance(element, Element))
        return node

    def get_visible_nodes(self):
        return [
            node
            for node in self._nodes.values()
            if not getattr(node, "is_embedded", False)
            and (item := node.graphicsItem()) is not None
            and item.isVisible()
        ]

    def place_nodes(self):
        if not self.visible_nodes:
            return

        node_by_name = {node.name(): node for node in self.visible_nodes}
        layers = self._layout_layers(node_by_name)
        positions = self._layout_positions(node_by_name, layers)
        for node_name, (x, y) in positions.items():
            node_by_name[node_name].graphicsItem().setPos(float(x), float(y))

    def _layout_layers(self, node_by_name):
        graph = nx.DiGraph()
        graph.add_nodes_from(node_by_name.keys())

        for src_node in self.visible_nodes:
            src_name = src_node.name()
            for term in src_node.terminals.values():
                if not term.isOutput():
                    continue
                for connected_term in term.connections().keys():
                    dst_node = connected_term.node()
                    if dst_node in self.visible_nodes:
                        graph.add_edge(src_name, dst_node.name())

        if nx.is_directed_acyclic_graph(graph):
            return [list(nodes) for nodes in nx.topological_generations(graph)]

        condensed = nx.condensation(graph)
        mapping = condensed.graph["mapping"]
        return [
            [
                node_name
                for node_name, component in mapping.items()
                if component in components
            ]
            for components in nx.topological_generations(condensed)
        ]

    def _layout_positions(self, node_by_name, layers):
        x_gap = float(NODE_LAYOUT_X_GAP)
        y_gap = float(NODE_LAYOUT_Y_GAP)
        positions = {}
        x = 0.0
        for layer_nodes in layers:
            sizes = {name: self._layout_node_size(node_by_name[name]) for name in layer_nodes}
            layer_width = max(width for width, _ in sizes.values())
            layer_height = sum(height for _, height in sizes.values())
            layer_height += y_gap * max(0, len(layer_nodes) - 1)
            y = -layer_height / 2.0
            for node_name in sorted(layer_nodes):
                _, node_height = sizes[node_name]
                positions[node_name] = (x, y + node_height / 2.0)
                y += node_height + y_gap
            x += layer_width + x_gap

        return positions

    def _layout_node_size(self, node):
        item = node.graphicsItem()
        rect = item.boundingRect()
        width = max(float(rect.width()), 180.0)
        height = max(float(rect.height()), 100.0)

        group_nodes = getattr(node, "nodes", None)
        if group_nodes:
            visible_children = [child for child in group_nodes if getattr(child, "render", False)]
            if visible_children:
                child_sizes = [self._layout_node_size(child) for child in visible_children]
                child_widths, child_heights = zip(*child_sizes)
                width = max(width, sum(child_widths) + 360.0 * max(0, len(child_widths) - 1))
                height = max(height, max(child_heights))

        return width, height

    def display_create_node_form(self, node):
        node_name = node.name()
        node_args = list(inspect.signature(node.__init__).parameters.values())
        create_node_form = CreateNodeForm(self, node, node_name, node_args)
        return create_node_form.exec_() == CreateNodeForm.Accepted
