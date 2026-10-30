"""Generate saved Led graph variations with Jev."""
import inspect
import json
import logging
import os
from contextlib import contextmanager
from copy import deepcopy
from random import choices
from unittest.mock import patch
from time import sleep
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import networkx as nx
import numpy as np
from dotenv import load_dotenv
from .adapter import adapt, apply_parameters, compatible, prepare_parameters, serialize, summary

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

GENERATION_RULES = (
    "Build automated festival ambiance lighting from the user's prompt. "
    "Always start with SCPlaylistPlayer using its constructor's default playlist_url. "
    "Build the playback and analysis pipeline from that playlist. "
    "Always end with BarGraphChart displaying exactly 180 lights: every bar height "
    "is fixed at 1. Express lighting intensity, rhythm, fades, and spatial effects "
    "through brushes alpha (RGBA channels 0-255), never through bar heights. "
    "Create an audio-reactive RGBA output of shape (180, 4) before adding the chart. "
    "Connect that output to the chart's brushes and leave its data input disconnected."
)

logger = logging.getLogger("led.jev")
logger.setLevel(logging.INFO)
logger.propagate = False
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("[Jev] %(levelname)s: %(message)s"))
    logger.addHandler(handler)


def jev(state, questions):
    """Keep requests small; split rejected batches without dropping choices."""
    items = list(questions.items())
    answers = {}
    for start in range(0, len(items), 8):
        logger.info("Batch %d/%d", start // 8 + 1, (len(items) + 7) // 8)
        answers.update(_jev_batch(state, items[start:start + 8]))
    return answers


def _jev_batch(state, items):
    try:
        return _jev_request(state, dict(items))
    except HTTPError as error:
        detail = error.read().decode()
        if error.code == 400 and '"max_tokens_exceeded"' in detail and len(items) > 1:
            middle = len(items) // 2
            return {**_jev_batch(state, items[:middle]), **_jev_batch(state, items[middle:])}
        raise RuntimeError(f"Jev HTTP {error.code}: {detail}") from error


def _jev_request(state, questions):
    for attempt in range(4):
        try:
            return _jev_request_once(state, questions)
        except HTTPError as error:
            if error.code not in (429, 500, 502, 503, 504) or attempt == 3:
                raise
            reason = str(error)
        except (URLError, ConnectionError, TimeoutError) as error:
            if attempt == 3:
                raise
            reason = str(error)
        delay = 2 ** attempt
        logger.warning("Batch failed: %s; retry %d/3 in %ds", reason, attempt + 1, delay)
        sleep(delay)


def _jev_request_once(state, questions):
    request = Request(
        "https://opencode.ai/zen/v1/systemone",
        data=json.dumps({"model": "jev-1.13-free", "state": state, "questions": questions}).encode(),
        headers={
            "Authorization": f"Bearer {os.environ['OPENCODE_API_KEY']}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "JevTests/1.0",
        },
    )
    logger.info("API batch: %d questions, %d bytes", len(questions), len(request.data))
    with urlopen(request, timeout=30) as response:
        return normalize_answers(json.load(response)["answers"], questions)


def normalize_answers(answers, questions):
    """Decode choices and sample returned probabilities before validation."""
    result = {}
    for name, question in questions.items():
        value = answers[name]["probabilities"]
        value = choices(list(value), weights=list(value.values()))[0]
        if str(value) not in question["criteria"]:
            raise ValueError(f"Invalid Jev choice for {name}: {value!r}")
        result[name] = {**answers[name], "choice": str(value)}
    return result


@contextmanager
def preview_nodes():
    """Disable workers and preserve update registries while inspecting nodes."""
    from backend.updatable.updatable import audio_updatable_objects, visual_updatable_objects
    audio, visual = list(audio_updatable_objects), list(visual_updatable_objects)
    try:
        with patch("threading.Thread.start"):
            yield
    finally:
        audio_updatable_objects[:] = audio
        visual_updatable_objects[:] = visual


class NodeCatalog:
    """Inspect registered node constructors and their Elements at runtime."""
    def __init__(self):
        from backend.registry.registry import nodes
        from backend.nodes.simple.constant_array import ConstantArrayNode
        from backend.components.elements.parameters import Parameter

        self.classes = {cls.nodeName: cls for cls in nodes}
        self.defaults, self.descriptions = {}, {}
        self.prototypes = []
        with preview_nodes():
            support = ConstantArrayNode(alias="ConstantArray.support")
            self.prototypes.append(support)
            for name, cls in self.classes.items():
                kwargs = {}
                if name == "Gathering":
                    kwargs.update(input_datas=[support.data], input_booleans=[support.length])
                if name == "AmplitudeLevelFunction":
                    kwargs["number_points"] = 300
                node = cls(**kwargs)
                self.prototypes.append(node)
                if name == "ESP32":
                    node.close()
                fields = []
                for parameter in inspect.signature(cls).parameters:
                    if parameter in ("alias", "parent", "terminals", "node_selector"):
                        continue
                    element = vars(node)[parameter]
                    # Build every adapter now, so catalog fields use actual Element constraints.
                    adapt(element)
                    if type(element) is Parameter:
                        details = element.kind
                        if element.kind == "number":
                            details += f" [{element.minimum}, {element.maximum}], integer={element.integer}, optional={element.optional}"
                    else:
                        details = type(element).__name__
                    fields.append(f"{parameter}: {details}")
                # Recreate constructor defaults, rather than copying references
                # to private child nodes owned by the inspection prototype.
                self.defaults[name] = {key: serialize(value) for key, value in kwargs.items()
                                       if key not in ("input_datas", "input_booleans")}
                self.descriptions[name] = f"{inspect.getdoc(cls) or name} Parameters: {', '.join(fields)}"
            self.defaults["SCPlaylistPlayer"]["playlist_url"] = inspect.signature(
                self.classes["SCPlaylistPlayer"]).parameters["playlist_url"].default

    def begin(self, source_state):
        self.state = deepcopy(source_state)
        self.state.update(nodes=[], connects=[])
        self.selected = []
        self.steps = 0

    def context(self, prompt, pending=False):
        return json.dumps({"instructions": GENERATION_RULES, "prompt": prompt, "catalog": self.descriptions,
                           "current_graph": self.pending if pending else self.state})

    def outputs(self):
        return [(node, terminal, vars(node).get(node.terminal_element_name(terminal)))
                for node in self.selected for terminal, options in node.pending_terminals.items()
                if options["io"] == "out"]

    def questions(self):
        criteria = {name: f"Add a {name} node" for name in self.classes
                    if name != "Gathering" or any("data" in node.pending_terminals
                    and node.pending_terminals["data"]["io"] == "out" for node in self.selected)}
        if not self.state["nodes"]:
            criteria = {"SCPlaylistPlayer": "Start with the default SoundCloud playlist"}
        elif self.state["nodes"][-1]["class"] == "BarGraphChart":
            criteria = {"finish": "Validate and load the completed festival lighting graph"}
        else:
            criteria.pop("SCPlaylistPlayer")
            if not any(element is not None and np.shape(element.value) == (180, 4)
                       for _, _, element in self.outputs()):
                criteria.pop("BarGraphChart")
        if self.steps >= int(os.environ.get("JEV_MAX_STEPS", "128")):
            raise ValueError("Generation reached JEV_MAX_STEPS without finishing")
        return {"next_node": {
            "type": "choice",
            "instructions": "Choose the next node to add, or finish when complete. Build sources before consumers so inputs can connect to existing outputs. Do not duplicate a role already fulfilled by the current graph.",
            "criteria": criteria,
        }}

    def get_nodes(self):
        return self.selected

    def prepare_add(self, node_type):
        self.steps += 1
        state = deepcopy(self.state)
        index = sum(node["class"] == node_type for node in state["nodes"])
        name = f"{node_type}.{index}"
        kwargs = dict(self.defaults[node_type])
        if node_type == "Gathering":
            sources = [node for node in self.selected if "data" in node.pending_terminals
                       and node.pending_terminals["data"]["io"] == "out"]
            if not sources:
                raise ValueError("Gathering requires an existing data source")
            kwargs.update(input_datas=[serialize(sources[0].data)],
                          input_booleans=[serialize(sources[0].data)])
        if node_type == "BarGraphChart":
            kwargs.update(number_points=180, data=serialize(np.ones(180)),
                          brushes=serialize(np.zeros((180, 4))))
        state["nodes"].append({"class": node_type, "name": name,
                               "pos": [len(state["nodes"]) * 300, 0],
                               "state": {"ctor_kwargs": kwargs}})
        self.selected = self.validate(state)
        self.pending = state
        sources = [element for node in self.selected for element in node.elements
                   if any(cls.__name__ == "Element" for cls in type(element).__mro__)]
        questions, resolve = prepare_parameters([self.selected[-1]], sources)
        omitted = {}
        target = self.selected[-1]
        locked = {"playlist_url"} if node_type == "SCPlaylistPlayer" else set()
        if node_type == "BarGraphChart":
            locked = set(vars(target))
        for terminal, options in target.pending_terminals.items():
            if options["io"] != "in":
                continue
            element_name = target.terminal_element_name(terminal)
            classes = {cls.__name__ for cls in type(vars(target)[element_name]).__mro__}
            if classes & {"DataElement", "NodeSelector"} and "ArrayElement" not in classes:
                locked.add(element_name)
        prefixes = tuple(f"Choose {target.name()}.{parameter}." for parameter in locked)
        for key in list(questions):
            if questions[key]["instructions"].startswith(prefixes):
                omitted[key] = {"choice": "original"}
                del questions[key]
        return questions, lambda answers: apply_parameters(state, resolve({**omitted, **answers}), self.selected)

    def prepare_wiring(self, state):
        self.selected = self.validate(state)
        return self.prepare_connections(state, self.selected[-1])

    def accept(self, state):
        self.selected = self.validate(state)
        self.state = state
        logger.info("Graph now has %d nodes, %d connections", len(state["nodes"]), len(state["connects"]))

    def complete(self):
        nodes = self.validate(self.state)
        first, last = nodes[0], nodes[-1]
        default_url = self.defaults["SCPlaylistPlayer"]["playlist_url"]
        if first.nodeName != "SCPlaylistPlayer" or first.playlist_url.value != default_url:
            raise ValueError("Festival lighting must start with the default SoundCloud playlist")
        if last.nodeName != "BarGraphChart" or last.number_points.value != 180:
            raise ValueError("Festival lighting must end with a 180-bar chart")
        if not np.array_equal(last.data.value, np.ones(180)):
            raise ValueError("Festival bar heights must stay fixed at 1")
        incoming = [edge[3] for edge in self.state["connects"] if edge[2] == last.name()]
        if "data" in incoming or "brushes" not in incoming:
            raise ValueError("Connect lighting to chart brushes only, leaving bar heights fixed")
        return self.state

    def validate(self, state):
        """Construct a side-effect-free preview before replacing the live graph."""
        from backend.overrides.CNode import CNode
        saved = {node["name"]: node for node in state["nodes"]}
        if not saved or len(saved) != len(state["nodes"]):
            raise ValueError("Graph must contain uniquely named nodes")
        dependencies = nx.DiGraph()
        dependencies.add_nodes_from(saved)

        def references(value):
            if type(value) is dict:
                if "__element_ref__" in value:
                    yield value["__element_ref__"]
                else:
                    for child in value.values():
                        yield from references(child)
            elif type(value) in (list, tuple):
                for child in value:
                    yield from references(child)

        for name, node in saved.items():
            if node["class"] not in self.classes:
                raise ValueError(f"Unknown node class: {node['class']}")
            for ref in references(node["state"]):
                if ref["node_name"] not in saved:
                    raise ValueError(f"Unknown reference: {ref['node_name']}")
                dependencies.add_edge(ref["node_name"], name)
        if not nx.is_directed_acyclic_graph(dependencies):
            raise ValueError("Constructor references must be acyclic")
        live = {}

        def resolve(value):
            if type(value) is dict:
                if "__element_ref__" in value:
                    ref = value["__element_ref__"]
                    source = live[ref["node_name"]]
                    element = source.terminal_element_name(ref["element_name"])
                    return vars(source)[element]
                if "__cnode_serde__" in value:
                    return CNode.deserialize_state_value(value)
                return {key: resolve(child) for key, child in value.items()}
            if type(value) in (list, tuple):
                return type(value)(resolve(child) for child in value)
            return value

        with preview_nodes():
            for name in nx.topological_sort(dependencies):
                node = saved[name]
                cls = self.classes[node["class"]]
                values = resolve(node["state"].get("ctor_kwargs", {}))
                values.update(resolve(node["state"].get("init_refs", {})))
                if "arguments" in node["state"]:
                    values["arguments"] = resolve(node["state"]["arguments"])
                parameters = inspect.signature(cls).parameters
                if values.keys() - parameters.keys():
                    raise ValueError(f"Unknown parameters for {name}")
                if "alias" in parameters:
                    values["alias"] = name
                instance = cls(**values)
                if node["class"] == "ESP32":
                    instance.close()
                instance.rename(name)
                instance.alias = name
                instance.parent = self
                live[name] = instance
            connected = set()
            for source, output, target, input_name in state["connects"]:
                src, dst = live[source], live[target]
                if src.pending_terminals[output]["io"] != "out" or dst.pending_terminals[input_name]["io"] != "in":
                    raise ValueError("Connections must run from output to input")
                key = (target, input_name)
                if key in connected:
                    raise ValueError(f"Multiple sources for {target}.{input_name}")
                connected.add(key)
                src_element = vars(src)[src.terminal_element_name(output)]
                dst_element = vars(dst)[dst.terminal_element_name(input_name)]
                if not compatible(src_element, dst_element):
                    raise ValueError(f"Incompatible connection: {source}.{output} -> {target}.{input_name}")
                dst_element.value = src_element
        return [live[name] for name in saved]

    def prepare_connections(self, state, node):
        questions = {}
        connections = {}
        outputs = self.outputs()
        parameters = inspect.signature(type(node)).parameters
        for terminal, options in node.pending_terminals.items():
            if options.get("io") != "in" or (node.nodeName == "BarGraphChart" and terminal == "data"):
                continue
            target = vars(node).get(node.terminal_element_name(terminal))
            if target is None:
                continue
            candidates = {"none": None}
            criteria = {"none": "Leave disconnected and use the configured parameter value"}
            for source_node, source_terminal, element in outputs:
                if element is None or source_node is node or not compatible(element, target):
                    continue
                key = f"source_{len(candidates)}"
                candidates[key] = (source_node.name(), source_terminal)
                criteria[key] = f"{source_node.name()}.{source_terminal}: {summary(element.value)}"
            if len(candidates) == 1:
                continue
            if node.nodeName == "BarGraphChart":
                del candidates["none"]
                del criteria["none"]
            key = f"connection_{len(connections)}"
            connections[key] = (node.name(), terminal, terminal in parameters, candidates)
            questions[key] = {
                "type": "choice",
                "instructions": f"Connect the input {node.name()}.{terminal} to fulfill its role in the NEW graph. {inspect.getdoc(type(node)) or ''} Choose none only if this input should use its default.",
                "criteria": criteria,
            }

        def resolve(answers):
            result = deepcopy(state)
            saved = {node["name"]: node["state"] for node in result["nodes"]}
            for key, (name, terminal, constructor_parameter, candidates) in connections.items():
                source = candidates[answers[key]["choice"]]
                result["connects"] = [edge for edge in result["connects"]
                                      if tuple(edge[2:]) != (name, terminal)]
                saved[name].setdefault("init_refs", {}).pop(terminal, None)
                if source is None:
                    continue
                source_name, source_terminal = source
                result["connects"].append((source_name, source_terminal, name, terminal))
                if constructor_parameter:
                    saved[name].setdefault("ctor_kwargs", {}).pop(terminal, None)
                    saved[name].setdefault("init_refs", {})[terminal] = {
                        "__element_ref__": {"node_name": source_name, "element_name": source_terminal}}
            if node.nodeName == "OperatorPipeline":
                node_state = saved[node.name()]
                kwargs = node_state.setdefault("ctor_kwargs", {})
                for argument in node_state.get("arguments", kwargs.get("arguments", [])):
                    if type(argument) is not dict or "__element_ref__" not in argument:
                        continue
                    ref = argument["__element_ref__"]
                    terminal = f"{ref['node_name']}:{ref['element_name']}".lower()
                    edge = (ref["node_name"], ref["element_name"], node.name(), terminal)
                    if edge not in map(tuple, result["connects"]):
                        result["connects"].append(edge)
                    if kwargs.get("length", 0) == 0:
                        source = next(item for item in self.selected if item.name() == ref["node_name"])
                        element = vars(source)[source.terminal_element_name(ref["element_name"])]
                        kwargs["length"] = int(np.size(element.value))
            return result

        return questions, resolve
