"""Build native Led graphs incrementally using weighted Jev choices."""
import asyncio
import inspect
import json
import logging
import os
from copy import deepcopy
from random import choices
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import numpy as np
import networkx as nx
from dotenv import load_dotenv
from .adapter import prepare_parameters, serialize, summary

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
EDIT_RULES = (
    "Edit the current lighting graph according to the user's prompt. "
    "Keep existing nodes, values, connections and positions unless a change is needed. "
    "Choose small targeted edits; add, configure, reconnect or remove nodes, then finish. "
    "Preserve the existing playback pipeline and express lighting intensity through brushes alpha. "
    "Keep existing BarGraphChart heights fixed. Do not rebuild the graph from scratch."
)

logger = logging.getLogger("led.jev")
INVALID_GRAPH = (ValueError, TypeError, KeyError, IndexError, OverflowError)
logger.setLevel(logging.INFO)
logger.propagate = False
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("[Jev] %(levelname)s: %(message)s"))
    logger.addHandler(handler)


async def jev(state, questions, deterministic=False):
    """Cancellable batches; only the in-flight HTTP call runs in a worker."""
    items, answers = list(questions.items()), {}
    for start in range(0, len(items), 8):
        logger.info("Batch %d/%d", start // 8 + 1, (len(items) + 7) // 8)
        answers.update(await _jev_batch(state, items[start:start + 8], deterministic))
    return answers


async def _jev_batch(state, items, deterministic):
    for attempt in range(4):
        try:
            return await asyncio.to_thread(_jev_request_once, state, dict(items), deterministic)
        except HTTPError as error:
            detail = error.read().decode()
            if error.code == 400 and '"max_tokens_exceeded"' in detail and len(items) > 1:
                middle = len(items) // 2
                return {**await _jev_batch(state, items[:middle], deterministic), **await _jev_batch(state, items[middle:], deterministic)}
            if error.code not in (429, 500, 502, 503, 504) or attempt == 3:
                raise RuntimeError(f"Jev HTTP {error.code}: {detail}") from error
            reason = str(error)
        except (URLError, ConnectionError, TimeoutError) as error:
            if attempt == 3:
                raise
            reason = str(error)
        delay = 2 ** attempt
        logger.warning("Batch failed: %s; retry %d/3 in %ds", reason, attempt + 1, delay)
        await asyncio.sleep(delay)


def _jev_request_once(state, questions, deterministic):
    request = Request(
        "https://opencode.ai/inference/systemone/v1/systemone",
        data=json.dumps({"model": "jev-1.13-free", "state": state, "questions": questions}).encode(),
        headers={
            "Authorization": f"Bearer {os.environ['OPENCODE_API_KEY']}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "Led/1.0",
        },
    )
    logger.info("API batch: %d questions, %d bytes", len(questions), len(request.data))
    with urlopen(request, timeout=30) as response:
        return normalize_answers(json.load(response)["answers"], questions, deterministic)


def normalize_answers(answers, questions, deterministic=False):
    """Decode choices and sample returned probabilities before validation."""
    result = {}
    for name, question in questions.items():
        value = answers[name]["probabilities"]
        weights = np.asarray(list(value.values()), dtype=float)
        if not value or value.keys() - question["criteria"].keys() or not np.isfinite(weights).all() or np.any(weights < 0) or weights.sum() <= 0:
            raise ValueError(f"Invalid Jev probabilities for {name}")
        value = max(value, key=lambda option: value[option]) if deterministic else choices(list(value), weights=list(value.values()))[0]
        if str(value) not in question["criteria"]:
            raise ValueError(f"Invalid Jev choice for {name}: {value!r}")
        result[name] = {**answers[name], "choice": str(value)}
    return result




class Generator:
    """Build a private graph; only the caller can commit the validated result."""

    def __init__(self, catalog):
        from backend.api.runtime import Runtime
        self.runtime = Runtime(catalog, preview=True)
        self.error = ""
        self.observations = {}
        self.accepted = {}

    def outputs(self):
        return [self.runtime.element(node.name(), name) for node in self.runtime.nodes.values()
                for name, port in node.pending_terminals.items() if port["io"] == "out"]

    async def ask(self, questions, deterministic=False):
        if all(len(question["criteria"]) == 1 for question in questions.values()):
            return {key: {"choice": next(iter(question["criteria"]))} for key, question in questions.items()}
        state = json.dumps({"instructions": EDIT_RULES if self.mode == "edit" else GENERATION_RULES, "prompt": self.prompt,
            "catalog": self.runtime.catalog.descriptions, "current_graph": self.current,
            "draft_graph": self.runtime.graph, "validation_error": self.error, "audition": self.observations,
            "outputs": {f"{source.node.name()}.{source.name}": summary(source.value) for source in self.outputs()}}, default=summary)
        return await jev(state, questions, deterministic)

    async def review(self, change):
        proposed = await self.audition.measure(self.runtime.graph, self.runtime.catalog)
        self.observations = {"change": change, "previous_accepted": self.accepted, "proposed": proposed,
                             "proposed_parameters": {item["id"]: item["parameters"] for item in self.runtime.graph["nodes"] if item["id"] in change}}
        answer = await self.ask({"review": {"type": "choice",
            "instructions": "Evaluate this change against the user's prompt at the CURRENT stage using the silent song audition. Judge the node's role and signal behavior, not whether an unfinished graph already produces finished lights. Constant sources, colors and curves may be correct. Compare with previous accepted observations. Revise if the change contradicts the request, breaks useful behavior, or cannot perform its intended role. For finish, require the whole request to be fulfilled.",
            "criteria": {"revise": "Reject this change and revise parameters/connections or choose another node/action",
                         "accept": "This change supports the request at the current stage"}}}, deterministic=True)
        if answer["review"]["choice"] != "accept":
            raise ValueError(f"Jev rejected {change} after the silent song audition; use the observations to revise it")
        self.accepted = proposed

    async def choose(self, name, instructions, options):
        question = {name: {"type": "choice", "instructions": instructions,
                           "criteria": {key: summary(value) for key, value in options.items()}}}
        return options[(await self.ask(question))[name]["choice"]]

    @staticmethod
    def spec(graph, node_id):
        return next(node for node in graph["nodes"] if node["id"] == node_id)

    def links(self, graph, node):
        """Expose constructor references as ordinary visible graph connections."""
        graph["connections"] = [edge for edge in graph["connections"] if edge["target"]["nodeId"] != node.name()]
        for name, port in node.pending_terminals.items():
            if port["io"] != "in":
                continue
            source = self.runtime.element(node.name(), name)._value_source
            if source is not None:
                graph["connections"].append({"id": f"{node.name()}:{name}", "source": serialize(source),
                                            "target": {"nodeId": node.name(), "element": name}})

    async def parameters(self, node_id):
        from backend.components.elements.parameters import DataElement, ArrayElement
        node = self.runtime.nodes[node_id]
        sources = [source for source in self.outputs() if source.node is not node]
        locked = {name for name, element in self.runtime._parameters(node)
                  if element._value_source is not None or isinstance(element, DataElement) and not isinstance(element, ArrayElement)}
        if node.nodeName == "SCPlaylistPlayer":
            locked.add("playlist_url")
        if node.nodeName == "BarGraphChart":
            return
        if node.nodeName == "Gathering":
            arrays = [source for source in sources if isinstance(source.value, np.ndarray)]
            groups = {f"source_{i}": [source] for i, source in enumerate(arrays)}
            for source in arrays:
                shape = source.value.shape
                groups[f"all_shape_{shape}"] = [item for item in arrays if item.value.shape == shape]
            if not groups:
                raise ValueError("Gathering requires an existing array source")
            selected = await self.choose("sources", "Select matching data sources for Gathering; enable inputs are connected next.", groups)
            graph = deepcopy(self.runtime.graph)
            self.spec(graph, node_id)["parameters"].update(input_datas=serialize(selected), input_booleans=[None] * len(selected))
            self.runtime.load(graph)
            return
        questions, resolve = prepare_parameters([node], sources, locked, editing=self.mode == "edit")
        graph = deepcopy(self.runtime.graph)
        self.spec(graph, node_id)["parameters"].update(resolve(await self.ask(questions)).get(node_id, {}))
        try:
            self.runtime.load(graph)
        except INVALID_GRAPH as error:
            raise ValueError(f"{error}; rejected parameters: {summary(self.spec(graph, node_id)['parameters'])}") from error

    def connection_options(self, node_id, name):
        from backend.components.elements.node_selector.node_selector import NodeSelector
        from backend.components.elements.parameters import validate_shape
        node = self.runtime.nodes[node_id]
        target = self.runtime.element(node_id, name)
        options = {"none": None}
        for source in self.outputs():
            if source.node is node:
                continue
            if isinstance(target, NodeSelector) and target.selection_elements.value and source.name not in target.selection_elements.value:
                continue
            if isinstance(target, NodeSelector) and source.node not in target.selection_nodes.value:
                continue
            try:
                if node.pending_terminals[name].get("adaptiveShape"):
                    validate_shape(np.shape(source.value))
                    if np.asarray(source.value).dtype.kind not in "biuf":
                        continue
                else:
                    self.runtime._check_connection(source.value, target.value)
            except ValueError:
                continue
            options[f"{source.node.name()}.{source.name}"] = source
        return options

    async def wire(self, node_id):
        node = self.runtime.nodes[node_id]
        graph = deepcopy(self.runtime.graph)
        self.links(graph, node)
        self.runtime.load(graph)
        # Parameters create dynamic ports first, then each port gets compatible choices.
        for name, port in list(node.pending_terminals.items()):
            if port["io"] != "in" or node.nodeName == "BarGraphChart" and name != "brushes":
                continue
            node = self.runtime.nodes[node_id]
            target = self.runtime.element(node_id, name)
            if target._value_source is not None:
                continue
            options = self.connection_options(node_id, name)
            if node.nodeName == "BarGraphChart":
                del options["none"]
            if not options:
                raise ValueError(f"No compatible source for {node_id}.{name}")
            if len(options) == 1 and "none" in options:
                continue
            while options:
                source = await self.choose("source", f"Connect {node_id}.{name}. {inspect.getdoc(type(node))} Use none only for an intended constant/default.", options)
                if source is None:
                    break
                graph = deepcopy(self.runtime.graph)
                try:
                    parameters = self.spec(graph, node_id)["parameters"]
                    terminal, _ = node.connect_input(name, serialize(source), parameters)
                    graph["connections"].append({"id": f"{node_id}:{terminal}", "source": serialize(source),
                                                "target": {"nodeId": node_id, "element": terminal}})
                    self.runtime.load(graph)
                    break
                except INVALID_GRAPH as error:
                    self.error = f"Cannot connect {source.node.name()}.{source.name} to {node_id}.{name}: {error}"
                    logger.warning("%s; trying another source", self.error)
                    del options[f"{source.node.name()}.{source.name}"]
            else:
                raise ValueError(f"No valid source for {node_id}.{name}: {self.error}")

    def complete(self):
        nodes = [self.runtime.nodes[item["id"]] for item in self.runtime.graph["nodes"]]
        first, last = nodes[0], nodes[-1]
        if first.nodeName != "SCPlaylistPlayer" or first.playlist_url.value != self.runtime.catalog.defaults["SCPlaylistPlayer"]["playlist_url"]:
            raise ValueError("Start with the default SoundCloud playlist")
        if last.nodeName != "BarGraphChart" or last.number_points.value != 180 or not np.array_equal(last.data.value, np.ones(180)):
            raise ValueError("End with 180 bars at fixed height 1")
        if last.data._value_source is not None or last.brushes._value_source is None:
            raise ValueError("Connect lighting to chart brushes; keep heights fixed")
        dependencies = nx.DiGraph((edge["source"]["nodeId"], edge["target"]["nodeId"])
                                  for edge in self.runtime.graph["connections"])
        dependencies.add_edges_from((source, item["id"]) for item in self.runtime.graph["nodes"]
                                    for source in self.runtime._references(item["parameters"]))
        if first.name() not in dependencies or not nx.has_path(dependencies, first.name(), last.name()):
            raise ValueError("Lighting must react to the playlist's playback/analysis pipeline")
        return deepcopy(self.runtime.graph)

    async def add(self, node_type, node_id, position):
        graph = deepcopy(self.runtime.graph)
        parameters = dict(self.runtime.catalog.defaults[node_type])
        if node_type == "BarGraphChart":
            parameters.update(number_points=180, data=np.ones(180), brushes=np.zeros((180, 4)))
        index = len(graph["nodes"])
        if self.mode == "edit" and graph["nodes"] and graph["nodes"][-1]["type"] == "BarGraphChart":
            index -= 1
        graph["nodes"].insert(index, {"id": node_id, "type": node_type, "position": position, "parameters": parameters})
        self.runtime.load(graph)
        await self.parameters(node_id)
        await self.wire(node_id)

    async def generate(self, prompt, current, report, preview, mode="generate"):
        self.prompt, self.current, self.mode = prompt, current, mode
        rejected = set()
        try:
            from .audition import Audition
            await report("running", "Loading song for silent evaluation")
            self.audition = await asyncio.to_thread(Audition)
            if mode == "edit":
                self.runtime.load(current)
                await preview(self.runtime)
                return await self.edit(report, preview)
            for step in range(int(os.environ.get("JEV_MAX_STEPS", "128"))):
                types = {name: name for name in self.runtime.catalog.classes
                         if name not in {"SCPlaylistPlayer", "BarGraphChart"} | rejected}
                if not self.runtime.nodes:
                    types = {"SCPlaylistPlayer": "SCPlaylistPlayer"}
                elif "BarGraphChart" not in rejected and any(np.shape(source.value) == (180, 4) for source in self.outputs()):
                    types["BarGraphChart"] = "BarGraphChart"
                if not self.outputs():
                    types.pop("Gathering", None)
                if not types:
                    raise ValueError(f"No usable node types remain: {self.error}")
                await report("running", f"Choosing node {step + 1}", step)
                node_type = await self.choose("next_node", "Choose the next node type. Build sources before consumers, avoid duplicate roles, and finish with BarGraphChart once the effect is complete.", types)
                node_id = f"{node_type} {step + 1}"
                previous = deepcopy(self.runtime.graph)
                for attempt in range(3):
                    try:
                        await report("running", f"Configuring {node_id} · attempt {attempt + 1}/3", len(previous["nodes"]) + 1)
                        await self.add(node_type, node_id, [step * 340, 0])
                        completed = self.complete() if node_type == "BarGraphChart" else None
                        await report("running", f"Evaluating {node_id} on the song", len(self.runtime.nodes))
                        await self.review("finish" if node_type == "BarGraphChart" else f"Added {node_id}")
                        await preview(self.runtime)
                        if node_type == "BarGraphChart":
                            return completed
                        self.error = ""
                        rejected.clear()
                        break
                    except INVALID_GRAPH as error:
                        self.error = f"{node_id}: {error}; revise its parameters/connections or choose another node."
                        logger.warning("%s", self.error)
                        self.runtime.load(previous)
                else:
                    rejected.add(node_type)
                    await report("running", f"Skipping {node_id}: {self.error}", len(previous["nodes"]))
            raise ValueError("Generation reached JEV_MAX_STEPS without finishing")
        finally:
            self.runtime.close()

    async def edit(self, report, preview):
        from backend.api.handlers import Handlers

        async def quiet(_message):
            pass

        handlers = Handlers(self.runtime, quiet)
        rejected = set()
        for step in range(int(os.environ.get("JEV_MAX_STEPS", "128"))):
            actions = {"add": "add", "finish": "finish"}
            if self.runtime.graph["connections"]:
                actions["disconnect"] = "disconnect"
            for node_id, node in self.runtime.nodes.items():
                actions[f"parameters:{node_id}"] = f"parameters:{node_id}"
                if any(port["io"] == "in" and not (node.nodeName == "BarGraphChart" and name != "brushes")
                       for name, port in node.pending_terminals.items()):
                    actions[f"connect:{node_id}"] = f"connect:{node_id}"
                if not any(node_id in self.runtime._references(item["parameters"])
                           for item in self.runtime.graph["nodes"] if item["id"] != node_id):
                    actions[f"remove:{node_id}"] = f"remove:{node_id}"
            actions = {key: value for key, value in actions.items() if key not in rejected}
            await report("running", f"Choosing edit {step + 1}", len(self.runtime.nodes))
            action = await self.choose("edit", "Choose a targeted edit required by the prompt. Parameters edits values; connect adds/replaces an input; disconnect removes a wire; remove deletes a node. Finish once the requested changes are complete.", actions)
            if action == "finish":
                try:
                    await self.review("finish")
                    return deepcopy(self.runtime.graph)
                except INVALID_GRAPH as error:
                    self.error = str(error)
                    rejected.add(action)
                    continue
            previous = deepcopy(self.runtime.graph)
            kind, _, node_id = action.partition(":")
            for attempt in range(3):
                try:
                    await report("running", f"{action} · attempt {attempt + 1}/3", len(self.runtime.nodes))
                    if kind == "add":
                        types = {name: name for name in self.runtime.catalog.classes
                                 if name not in {item["type"] for item in previous["nodes"] if item["type"] in {"SCPlaylistPlayer", "BarGraphChart"}}}
                        node_type = await self.choose("node_type", "Choose a node needed for this edit.", types)
                        suffix = 1
                        while f"{node_type} {suffix}" in self.runtime.nodes:
                            suffix += 1
                        node_id = f"{node_type} {suffix}"
                        await self.add(node_type, node_id, [len(previous["nodes"]) * 340, 0])
                    elif kind == "parameters":
                        await self.parameters(node_id)
                        graph = deepcopy(self.runtime.graph)
                        self.links(graph, self.runtime.nodes[node_id])
                        self.runtime.load(graph)
                    elif kind == "connect":
                        node = self.runtime.nodes[node_id]
                        ports = {name: name for name, port in node.pending_terminals.items()
                                 if port["io"] == "in" and not (node.nodeName == "BarGraphChart" and name != "brushes")}
                        terminal = await self.choose("input", f"Choose the input to connect on {node_id}.", ports)
                        sources = self.connection_options(node_id, terminal)
                        sources.pop("none")
                        if not sources:
                            raise ValueError(f"No compatible source for {node_id}.{terminal}")
                        source = await self.choose("source", f"Choose a source for {node_id}.{terminal}.", sources)
                        await handlers.connection_add(None, {"source": serialize(source), "target": {"nodeId": node_id, "element": terminal}})
                    elif kind == "disconnect":
                        edges = {edge["id"]: edge["id"] for edge in previous["connections"]}
                        edge_id = await self.choose("connection", "Choose the connection to remove; endpoints are in the draft graph.", edges)
                        await handlers.connection_remove(None, {"connectionId": edge_id})
                    else:
                        await handlers.node_remove(None, {"nodeId": node_id})
                    await report("running", f"Evaluating {action} on the song", len(self.runtime.nodes))
                    await self.review(f"{action} {node_id}")
                    await preview(self.runtime)
                    self.error = ""
                    rejected.clear()
                    break
                except INVALID_GRAPH as error:
                    self.error = f"{action}: {error}; revise the edit or choose another action."
                    logger.warning("%s", self.error)
                    self.runtime.load(previous)
            else:
                rejected.add(action)
        raise ValueError("Editing reached JEV_MAX_STEPS without finishing")
