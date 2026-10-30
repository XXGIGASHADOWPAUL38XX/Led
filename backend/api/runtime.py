"""Authoritative processing graph, parameter validation, and live output state."""
from copy import deepcopy
from enum import Enum
import inspect

import networkx as nx
import numpy as np

from ai.template_generator.agent import NodeCatalog, preview_nodes
from backend.components.elements.element import Element
from backend.components.elements.signal import drain_signals
from backend.components.elements.parameters import DataElement, ArrayElement, SequenceElement, Parameter, NodeReferenceElement, ReferenceElement
from backend.overrides.CNode import CNode
from backend.components.elements.node_selector.node_selector import NodeSelector
from backend.updatable.updatable import audio_updatable_objects, visual_updatable_objects
from .protocol import encode


class Runtime:
    def __init__(self):
        self.catalog = NodeCatalog()
        self.nodes = {}
        self.graph = {"nodes": [], "connections": []}
        self.revision = 0
        self.failed = set()
        self.players = {}
        self.updates = []
        self.updates_by_node = {}
        self.dirty_settings = set()
        self.port_signatures = {}

    def get_nodes(self):
        return list(self.nodes.values())

    def element(self, node_id, name):
        node = self.nodes[node_id]
        element = vars(node)[node.terminal_element_name(name)]
        if not isinstance(element, Element):
            raise ValueError(f"{node_id}.{name} is not an element")
        return element

    def _resolve(self, value, live):
        if type(value) is dict and set(value) == {"nodeId"}:
            return live[value["nodeId"]]
        if type(value) is dict and set(value) == {"nodeId", "element"}:
            node = live[value["nodeId"]]
            return vars(node)[node.terminal_element_name(value["element"])]
        if type(value) is list:
            return [self._resolve(item, live) for item in value]
        if type(value) is dict:
            return {key: self._resolve(item, live) for key, item in value.items()}
        return value

    @staticmethod
    def _references(value):
        if type(value) is dict:
            if set(value) in ({"nodeId", "element"}, {"nodeId"}):
                yield value["nodeId"]
            else:
                for child in value.values():
                    yield from Runtime._references(child)
        elif type(value) is list:
            for child in value:
                yield from Runtime._references(child)

    def _build(self, graph, reuse=True):
        specs = {item["id"]: item for item in graph["nodes"]}
        if len(specs) != len(graph["nodes"]) or any(not key or type(key) is not str for key in specs):
            raise ValueError("Node IDs must be unique nonempty strings")
        dependencies = nx.DiGraph()
        dependencies.add_nodes_from(specs)
        for item in specs.values():
            if item["type"] not in self.catalog.classes:
                raise ValueError(f"Unknown node type: {item['type']}")
            for source in self._references(item.get("parameters", {})):
                if source not in specs:
                    raise ValueError(f"Unknown source node: {source}")
                dependencies.add_edge(source, item["id"])
        targets, ids = set(), set()
        for edge in graph["connections"]:
            source, target = edge["source"], edge["target"]
            if edge["id"] in ids or (target["nodeId"], target["element"]) in targets:
                raise ValueError("Connections require unique IDs and one source per input")
            ids.add(edge["id"])
            targets.add((target["nodeId"], target["element"]))
            if source["nodeId"] not in specs or target["nodeId"] not in specs:
                raise ValueError("Connection references an unknown node")
            dependencies.add_edge(source["nodeId"], target["nodeId"])
        if not nx.is_directed_acyclic_graph(dependencies):
            raise ValueError("Graph connections and constructor references must be acyclic")
        live, updates_by_node = {}, {}
        old_specs = {item["id"]: item for item in self.graph["nodes"]}
        created = []
        try:
            with preview_nodes():
                for node_id in nx.topological_sort(dependencies):
                    spec = specs[node_id]
                    old = old_specs.get(node_id)
                    incoming = [edge for edge in graph["connections"] if edge["target"]["nodeId"] == node_id]
                    old_incoming = [edge for edge in self.graph["connections"] if edge["target"]["nodeId"] == node_id]
                    unchanged = reuse and old is not None and node_id in self.nodes and old["type"] == spec["type"] and encode(old.get("parameters", {})) == encode(spec.get("parameters", {}))
                    if unchanged and incoming == old_incoming and all(live[source] is self.nodes.get(source) for source in dependencies.predecessors(node_id)):
                        live[node_id] = self.nodes[node_id]
                        updates_by_node[node_id] = self.updates_by_node[node_id]
                        continue
                    audio_start, visual_start = len(audio_updatable_objects), len(visual_updatable_objects)
                    cls = self.catalog.classes[spec["type"]]
                    parameters = inspect.signature(cls).parameters
                    values = dict(self.catalog.defaults[spec["type"]])
                    values.update(self._resolve(spec.get("parameters", {}), live))
                    for edge in graph["connections"]:
                        if edge["target"]["nodeId"] == node_id and edge["target"]["element"] in parameters:
                            source = edge["source"]
                            upstream = live[source["nodeId"]]
                            values[edge["target"]["element"]] = vars(upstream)[upstream.terminal_element_name(source["element"])]
                    if values.keys() - parameters.keys() or values.keys() & {"parent", "alias", "node_selector"}:
                        raise ValueError(f"Unknown or reserved constructor parameter on {node_id}")
                    for key, value in list(values.items()):
                        default = parameters[key].default
                        if isinstance(default, Enum) and type(value) is str:
                            values[key] = type(default)[value]
                        elif isinstance(default, np.ndarray) and type(value) is list:
                            values[key] = np.asarray(value, dtype=default.dtype)
                    if "alias" in parameters:
                        values["alias"] = node_id
                    node = cls(**values)
                    created.append(node)
                    node.rename(node_id)
                    node.alias = node_id
                    node.parent = self
                    live[node_id] = node
                    for key, element in self._parameters(node):
                        self._check_value(element, element.value)
                    node.validate_parameters({})
                    updates_by_node[node_id] = list(dict.fromkeys(audio_updatable_objects[audio_start:] + visual_updatable_objects[visual_start:]))
                for edge in graph["connections"]:
                    source, target = edge["source"], edge["target"]
                    src, dst = live[source["nodeId"]], live[target["nodeId"]]
                    if src.pending_terminals[source["element"]]["io"] != "out" or dst.pending_terminals[target["element"]]["io"] != "in":
                        raise ValueError("Connect outputs to inputs only")
                    output = vars(src)[src.terminal_element_name(source["element"])]
                    input_element = vars(dst)[dst.terminal_element_name(target["element"])]
                    self._check_connection(output.value, input_element.value)
                    if input_element._value_source is not output:
                        input_element.value = output
        except Exception:
            for node in reversed(created):
                self._stop_node(node)
            raise
        return live, updates_by_node

    @staticmethod
    def _parameters(node):
        for name in inspect.signature(type(node)).parameters:
            if name in {"parent", "alias", "node_selector"}:
                continue
            element = vars(node).get(name)
            if isinstance(element, Element):
                yield name, element

    @staticmethod
    def _check_value(element, value):
        if isinstance(value, np.ndarray) and value.dtype.kind in "fiu" and not np.isfinite(value).all():
            raise ValueError("Arrays must contain finite values")
        valid, error = element.check_value(value)
        if not valid:
            raise ValueError(error)

    @staticmethod
    def _check_connection(output, target):
        if isinstance(target, np.ndarray):
            if not isinstance(output, np.ndarray) or output.ndim != target.ndim or any(want and want != got for want, got in zip(target.shape, output.shape)):
                raise ValueError("Incompatible array shapes")
            if not np.can_cast(output.dtype, target.dtype, casting="same_kind"):
                raise ValueError("Incompatible array dtypes")
        elif target is not None and type(output) is not type(target):
            raise ValueError("Incompatible element types")

    def load(self, graph, *, replace=False):
        graph = deepcopy(graph)
        live, updates_by_node = self._build(graph, reuse=not replace)
        previous = self.nodes
        for node_id, node in previous.items():
            if live.get(node_id) is not node:
                self._stop_node(node)
        self.nodes, self.updates_by_node, self.graph = live, updates_by_node, graph
        self.updates = list(dict.fromkeys(node for updates in updates_by_node.values() for node in updates))
        self.failed.clear()
        self.dirty_settings.clear()
        self.revision += 1
        for node_id, node in live.items():
            if previous.get(node_id) is node:
                continue
            for name, element in self._parameters(node):
                if (isinstance(element, DataElement) and not isinstance(element, ArrayElement)) or isinstance(element, (ReferenceElement, NodeSelector)):
                    continue
                element.valueChanged.connect(lambda _value, owner=node, field=name: self._setting_changed(owner, field))
        self.players = {key: node for key, node in live.items() if node.nodeName == "SCPlaylistPlayer"}
        self.port_signatures = {key: self._port_signature(node) for key, node in live.items()}
        # Explicit playback starts playlist loading; unrelated edits preserve it.
        for node in live.values():
            if node.nodeName == "ESP32" and previous.get(node.name()) is not node:
                node.worker.start()
        return self.snapshot()

    def load_template(self, template, *, replace=False):
        """Load Jev's saved constructor values and references without a desktop loader."""
        from backend.overrides.CNode import CNode

        def resolve(value):
            if type(value) is dict:
                if "__element_ref__" in value:
                    ref = value["__element_ref__"]
                    return {"nodeId": ref["node_name"], "element": ref["element_name"]}
                if CNode._SERDE_TAG in value:
                    return CNode.deserialize_state_value(value)
                return {key: resolve(child) for key, child in value.items()}
            if type(value) in (list, tuple):
                return [resolve(child) for child in value]
            return value

        nodes = []
        for item in template["nodes"]:
            state = item["state"]
            parameters = resolve({**state.get("ctor_kwargs", {}), **state.get("init_refs", {})})
            if "arguments" in state:
                parameters["arguments"] = resolve(state["arguments"])
            nodes.append({"id": item["name"], "type": item["class"],
                          "position": state.get("pos", [0, 0]), "parameters": parameters})
        connections = [{"id": f"connection-{index}",
                        "source": {"nodeId": source, "element": output},
                        "target": {"nodeId": target, "element": input_name}}
                       for index, (source, output, target, input_name) in enumerate(template["connects"])]
        return self.load({"nodes": nodes, "connections": connections}, replace=replace)

    def set_element(self, node_id, name, value):
        node = self.nodes[node_id]
        parameters = dict(self._parameters(node))
        if name not in parameters:
            raise ValueError("Only constructor parameters are editable")
        element = parameters[name]
        if isinstance(element, ReferenceElement):
            raise ValueError("This object is managed by the backend")
        if element._value_source is not None and not isinstance(element, NodeSelector):
            raise ValueError("Disconnect this input before editing it")
        old = element._value_source if isinstance(element, NodeSelector) else element.value
        value = self._resolve(value, self.nodes)
        if isinstance(value, Element):
            source_ports = value.node.pending_terminals
            output_names = [key for key, options in source_ports.items() if options["io"] == "out" and value.node.terminal_element_name(key) == value.name]
            if not output_names or value.node is node:
                raise ValueError("References must point to another node's output")
            if isinstance(element, NodeSelector) and element.selection_elements.value and value.name not in element.selection_elements.value:
                raise ValueError("This selector does not accept that output")
        if isinstance(old, Enum):
            value = type(old)[value]
        elif isinstance(old, np.ndarray):
            value = np.asarray(value, dtype=old.dtype)
            if value.shape != old.shape:
                raise ValueError("Keep authored array dimensions")
        elif type(old) is tuple:
            value = tuple(value)
        elif type(old) is bool and type(value) is not bool:
            raise ValueError("Expected a boolean")
        elif type(old) is str and type(value) is not str:
            raise ValueError("Expected text")
        self._check_value(element, value)
        node.validate_parameters({name: value})
        try:
            if isinstance(element, NodeSelector):
                element.set_default_element(value)
            else:
                element.value = value
            node.parameters_changed(name)
            for edge in self.graph["connections"]:
                src, dst = edge["source"], edge["target"]
                self._check_connection(self.element(src["nodeId"], src["element"]).value, self.element(dst["nodeId"], dst["element"]).value)
            for candidate in self.nodes.values():
                candidate.validate_parameters({})
        except Exception:
            self.dirty_settings.discard((node_id, name))
            if isinstance(element, NodeSelector):
                element.set_default_element(old)
            else:
                element.value = old
            node.parameters_changed(name)
            self.dirty_settings.discard((node_id, name))
            raise
        spec = next(item for item in self.graph["nodes"] if item["id"] == node_id)
        spec.setdefault("parameters", {})[name] = {"nodeId": value.node.name(), "element": value.name} if isinstance(value, Element) else value
        self.dirty_settings.discard((node_id, name))
        self.failed.clear()
        self.revision += 1
        return {"nodeId": node_id, "element": name, "value": spec["parameters"][name]}

    def _setting_changed(self, node, name):
        if self.nodes.get(node.name()) is node:
            self.dirty_settings.add((node.name(), name))

    def setting_updates(self):
        """Coalesce changes made by Python itself, not only API commands."""
        dirty, self.dirty_settings = self.dirty_settings, set()
        changes = []
        specs = {item["id"]: item for item in self.graph["nodes"]}
        for node_id, name in sorted(dirty):
            element = self.element(node_id, name)
            if element._value_source is not None:
                continue
            value = element.value
            specs[node_id].setdefault("parameters", {})[name] = value
            changes.append({"nodeId": node_id, "element": name, "value": value, "node": self.describe(self.nodes[node_id])})
        if changes:
            self.revision += 1
        return changes

    def describe(self, node):
        result = []
        for name, element in self._parameters(node):
            value = element.value
            item = {"name": name, "label": name.replace("_", " ").capitalize(), "kind": "text", "value": value, "disabled": element._value_source is not None}
            if isinstance(element, NodeReferenceElement):
                item.update(kind="node-reference", value=self._describe_value(value), defaultType=type(value).__name__)
            elif isinstance(element, ReferenceElement):
                item.update(kind="managed", value=None, disabled=True)
            elif isinstance(element, SequenceElement):
                item.update(kind="sequence", value=self._describe_value(value))
            elif isinstance(element, Parameter):
                item.update(kind=element.kind, min=element.minimum, max=element.maximum, integer=element.integer, optional=element.optional)
                if element.choices:
                    item.update(options=[{"value": choice, "label": name} for name, choice in element.choices.items()])
                if element.kind == "enum":
                    item["value"] = value.name
            elif isinstance(element, DataElement) and not isinstance(element, ArrayElement):
                item.update(kind="data", value=None, shape=list(np.shape(value)))
            elif isinstance(element, NodeSelector):
                source = element._value_source
                item.update(kind="reference", value=self._describe_value(source), disabled=False, selectionElements=element.selection_elements.value)
            elif isinstance(value, Enum):
                item.update(kind="select", value=value.name, options=[{"value": key, "label": key} for key in type(value).__members__])
            elif isinstance(value, np.ndarray):
                item.update(kind="array", shape=list(value.shape), dtype=value.dtype.str)
                if isinstance(element, ArrayElement):
                    item.update(min=element.min_value, max=element.max_value)
            elif type(value) in (list, tuple, dict) or value is None:
                continue
            result.append(item)
        return {"id": node.name(), "type": node.nodeName, "elements": result,
                "ports": [{"name": key, "direction": options["io"], "shape": list(np.shape(vars(node)[node.terminal_element_name(key)].value))}
                          for key, options in node.pending_terminals.items() if isinstance(vars(node).get(node.terminal_element_name(key)), Element)]}

    def _describe_value(self, value):
        if isinstance(value, Element):
            source = value._value_source
            if source is not None:
                return self._describe_value(source)
            if isinstance(value, NodeSelector):
                return None
            return {"nodeId": value.node.name(), "element": value.name}
        if isinstance(value, CNode):
            return {"nodeId": value.name()} if self.nodes.get(value.name()) is value else None
        if type(value) in (list, tuple):
            return [self._describe_value(item) for item in value]
        return value

    @staticmethod
    def _port_signature(node):
        return [(name, options["io"], np.shape(vars(node)[node.terminal_element_name(name)].value))
                for name, options in node.pending_terminals.items()
                if node.terminal_element_name(name) in vars(node)]

    def schema_updates(self):
        """Publish resized arrays and dynamic outputs without streaming metadata every tick."""
        changes = []
        for key, node in self.nodes.items():
            signature = self._port_signature(node)
            if signature != self.port_signatures[key]:
                self.port_signatures[key] = signature
                changes.append({"nodeId": key, "node": self.describe(node)})
        if changes:
            self.revision += 1
        return changes

    def configure(self, node_id, parameters):
        """Rebuild constructor-dependent state atomically for structural edits."""
        node = self.nodes[node_id]
        fields = dict(self._parameters(node))
        if type(parameters) is not dict or parameters.keys() - fields.keys():
            raise ValueError("Unknown node parameters")
        for name in parameters:
            if isinstance(fields[name], ReferenceElement) and not isinstance(fields[name], NodeReferenceElement):
                raise ValueError("This object is managed by the backend")
        graph = deepcopy(self.graph)
        spec = next(item for item in graph["nodes"] if item["id"] == node_id)
        spec.setdefault("parameters", {}).update(parameters)
        return self.load(graph)

    def snapshot(self):
        return {"graph": self.graph, "nodes": [self.describe(node) for node in self.nodes.values()],
                "catalog": [{"type": key, "description": value} for key, value in self.catalog.descriptions.items()]}

    def frame(self, subscriptions):
        return [{"nodeId": node_id, "element": name, "value": self.element(node_id, name).value}
                for node_id, name in subscriptions if node_id in self.nodes and name in self.nodes[node_id].pending_terminals]

    def tick(self):
        drain_signals()
        errors = []
        for node in self.updates:
            if node in self.failed:
                continue
            try:
                node.c_update()
            except Exception as error:
                self.failed.add(node)
                errors.append({"nodeId": node.name(), "message": str(error)})
        return errors

    @staticmethod
    def _stop_node(node):
        if node.nodeName in {"SCPlaylistPlayer", "StreamPlayer", "StreamMic"}:
            node.stop()
        node.close()

    def close(self):
        for node in self.nodes.values():
            self._stop_node(node)
        self.nodes = {}
        self.updates = []
        self.updates_by_node = {}
        self.players.clear()
