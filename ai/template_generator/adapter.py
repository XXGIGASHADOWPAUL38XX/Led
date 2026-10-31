"""Turn Led Elements into Jev choices and typed constructor values."""

from dataclasses import dataclass
from enum import Enum
import inspect

import numpy as np
import webcolors


@dataclass
class Choice:
    options: dict


@dataclass
class Group:
    children: dict
    build: object
    original: object = None


def current(element):
    source = element._value_source
    return source if source is not None else element.value


def boolean(element, sources=()):
    return Choice({"original": current(element), "false": False, "true": True})


def number(element, sources=()):
    if np.ndim(element.value):
        shapes = {(1,), (180,), (180, 3), (180, 4), *(np.shape(source.value) for source in sources)}
        return Choice({"original": current(element), **{
            f"shape_{'x'.join(map(str, shape))}": shape for shape in sorted(shapes) if shape and all(shape)
        }})
    values = np.linspace(element.minimum, element.maximum, 50)
    values = list(dict.fromkeys(int(round(value)) if element.integer else float(value) for value in values))
    options = {"original": current(element), **{f"value_{i}": value for i, value in enumerate(values)}}
    if element.optional:
        options["none"] = None
    return Choice(options)


def choices(element, sources=()):
    return Choice({"original": current(element), **{f"item_{name}": value for name, value in element.choices.items()}})


def parameter(element, sources=()):
    return {"number": number, "boolean": boolean, "text": text, "color": color,
            "interval": interval, "enum": choices, "choice": choices, "axis": choices}[element.kind](element, sources)


def text(element, sources=()):
    structured = ("url", "ip", "path", "file", "profile", "browser")
    options = {"original": current(element)}
    if not any(word in element.name.lower() for word in structured):
        options["element_name"] = element.name
    return Choice(options)


def color(element, sources=()):
    return Choice({"original": current(element), **{
        name: tuple(webcolors.name_to_rgb(name)) for name in webcolors.names()
    }})


def interval(element, sources=()):
    values = np.asarray(element.value, dtype=float)
    if values.shape != (2,) or not np.all(np.isfinite(values)):
        return fixed(element)
    low, high = sorted(values)
    candidates = list(dict.fromkeys(float(value) for value in np.linspace(low, high, 50)))
    children = {str(i): Choice({"original": float(value), **{
        f"value_{j}": candidate for j, candidate in enumerate(candidates)
    }}) for i, value in enumerate(values)}

    def build(selected):
        result = [selected["0"], selected["1"]]
        if element.name in ("input_value_interval", "interval_input") and result[0] >= result[1]:
            raise ValueError(f"{element.name} must have increasing endpoints")
        return result

    return Group(children, build, element.value)


def array(element, sources=()):
    value = np.asarray(element.value)
    options = {"original": current(element)}
    low, high = element.min_value, element.max_value
    if not value.size or value.dtype.kind not in "biuf" or low is None or high is None:
        return Choice(options)
    if low > high or not np.all(np.isfinite([low, high])):
        raise ValueError(f"Invalid array bounds for {element.name}")
    if "constant" in element.builders:
        for i, number in enumerate(np.linspace(low, high, 50)):
            options[f"constant_{i}"] = np.full(value.shape, number, dtype=value.dtype)
    if value.ndim == 0:
        return Choice(options)
    # Curve points are (x, y) rows. Other arrays repeat a profile along axis 0.
    points = element.name == "points" and value.ndim == 2 and value.shape[1] == 2
    x = np.linspace(0, 1, value.shape[0])
    profiles = {}
    if "ramp" in element.builders:
        profiles.update(ramp=x, reversed_ramp=1 - x)
    if "curve" in element.builders:
        profiles.update(center_peak=1 - abs(2 * x - 1), edge_peaks=abs(2 * x - 1))
    for name, profile in profiles.items():
        y = low + (high - low) * profile
        built = np.column_stack((x, y)) if points else np.broadcast_to(
            y.reshape(-1, *([1] * (value.ndim - 1))), value.shape)
        options[name] = np.array(built, dtype=value.dtype, copy=True)
    # Constant curves also need ordered x coordinates.
    if points:
        for name, built in options.items():
            if name.startswith("constant_"):
                built[:, 0] = x
    return Choice(options)


def compatible(source, target):
    output, value = source.value, target.value
    if value is None:
        return isinstance(output, np.ndarray)
    if isinstance(value, np.ndarray):
        return isinstance(output, np.ndarray) and output.ndim == value.ndim and all(
            expected == 0 or expected == actual for expected, actual in zip(value.shape, output.shape)
        ) and np.can_cast(output.dtype, value.dtype, casting="same_kind")
    if isinstance(value, (int, float, np.number)) and not isinstance(value, (bool, np.bool_)):
        numeric = (int, np.integer) if isinstance(value, (int, np.integer)) else (int, float, np.number)
        return isinstance(output, numeric) and not isinstance(output, (bool, np.bool_))
    return type(output) is type(value)


def signal(element, sources=()):
    options = {"original": current(element)}
    for source in sources:
        terminal = source.node.pending_terminals.get(source.name.lower(), {})
        if source.node is not element.node and terminal.get("io") == "out" and compatible(source, element):
            options[f"source_{source.node.name()}_{source.name}"] = source
    return Choice(options)


def node_selector(element, sources=()):
    nodes = element.selection_nodes.value
    names = element.selection_elements.value
    allowed = [source for source in sources if source.node in nodes and (not names or source.name in names)]
    spec = signal(element, allowed)
    spec.options["none"] = None
    return spec


def node_reference(element, sources=()):
    from backend.nodes.pipelines.amplitudes.amplitude_level_function import AmplitudesLevelFunction
    from backend.nodes.windows_fcts.window_fct import WindowFct
    value = element.value
    expected = {"amplitudes_level_fct": AmplitudesLevelFunction, "window_function": WindowFct}[element.name]
    return Choice({"original": value, **{source.node.name(): source.node for source in sources
        if isinstance(source.node, expected)}})


def fixed(element, sources=()):
    return Choice({"original": current(element)})


def value_spec(value, sources):
    if any(cls.__name__ == "Element" for cls in type(value).__mro__):
        if value.node.pending_terminals.get(value.name.lower(), {}).get("io") == "out":
            return Choice({"original": value})
        return adapt(value, sources)
    if type(value) is dict:
        return Group({key: value_spec(item, sources) for key, item in value.items()}, dict, value)
    if type(value) in (list, tuple):
        return Group({str(i): value_spec(item, sources) for i, item in enumerate(value)},
                     lambda items: type(value)(items.values()), value)
    if isinstance(value, (bool, np.bool_)):
        return Choice({"original": value, "false": type(value)(False), "true": type(value)(True)})
    if isinstance(value, Enum):
        return Choice({"original": value, **type(value).__members__})
    # Plain numbers/strings have no declared constraints: retain them.
    return Choice({"original": value})


def sequence(element, sources=()):
    value = element.value
    if element.name in ("operator_nodes", "nodes", "auto_start_nodes", "offline_pipelines"):
        from backend.overrides.CNode import OfflineCNode
        nodes = {source.node.name(): source.node for source in sources
                 if (element.name != "operator_nodes" or source.name == "data" and np.size(source.value) == 1)
                 and (element.name != "auto_start_nodes" or source.node.nodeName in {"StreamPlayer", "StreamMic", "SCPlaylistPlayer"})
                 and (element.name != "offline_pipelines" or isinstance(source.node, OfflineCNode))}
        return Choice({"original": value, **{name: [node] for name, node in nodes.items()},
                       **({"all": list(nodes.values())} if nodes else {})})
    if element.name in ("input_datas", "input_booleans"):
        return fixed(element)
    if element.name == "arguments" and not value:
        options = {"original": None}
        for source in sources:
            if source.node is not element.node and source.node.pending_terminals.get(source.name.lower(), {}).get("io") == "out":
                options[f"source_{source.node.name()}_{source.name}"] = source
        return Group({
            "source": Choice(options),
            "operation": Choice({"original": "*", "add": "+", "subtract": "-"}),
            "number": Choice({"original": 1.0, **{f"value_{i}": float(number)
                for i, number in enumerate(np.linspace(0, 2, 50))}}),
        }, lambda selected: [] if selected["source"] is None else
           [selected["source"], selected["operation"], selected["number"]], value)
    return value_spec(value, sources)


ADAPTERS = {
    "Parameter": parameter, "ArrayElement": array,
    "DataElement": signal, "NodeSelector": node_selector,
    "SequenceElement": sequence, "NodeReferenceElement": node_reference, "ReferenceElement": fixed,
}


def adapt(element, sources=()):
    for cls in type(element).__mro__:
        if cls.__name__ in ADAPTERS:
            return ADAPTERS[cls.__name__](element, sources)
    return fixed(element)


def serialize(value):
    if any(cls.__name__ == "Element" for cls in type(value).__mro__):
        terminal = value.name.lower()
        if value.node.pending_terminals.get(terminal, {}).get("io") != "out":
            terminal = next((name for name, options in value.node.pending_terminals.items()
                             if options.get("io") == "out" and value.node.terminal_element_name(name) == value.name), value.name)
        return {"nodeId": value.node.name(), "element": terminal}
    if any(cls.__name__ == "CNode" for cls in type(value).__mro__):
        return {"nodeId": value.name()}
    if isinstance(value, Enum):
        return value.name
    if isinstance(value, np.ndarray):
        return np.array(value, copy=True)
    if isinstance(value, np.generic):
        return value.item()
    if type(value) in (list, tuple):
        return [serialize(item) for item in value]
    if isinstance(value, dict):
        return {key: serialize(item) for key, item in value.items()}
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    raise TypeError(f"No serializer for {type(value).__name__}")


def summary(value):
    if isinstance(value, np.ndarray):
        return f"array shape={value.shape}, dtype={value.dtype}, range=[{value.min()}, {value.max()}]" if value.size else "empty array"
    return str(serialize(value))


def prepare_parameters(nodes, sources=None, locked=(), editing=False):
    """Snapshot parameter choices before asking Jev."""
    nodes = list(nodes)
    sources = sources if sources is not None else [element for node in nodes for element in node.elements
               if any(cls.__name__ == "Element" for cls in type(element).__mro__) and element.node in nodes]
    specs, questions, paths = {}, {}, {}

    def collect(spec, path, description):
        if isinstance(spec, Group):
            for name, child in spec.children.items():
                collect(child, (*path, str(name)), description)
        elif len(spec.options) > 1:
            key = f"parameter_{len(questions)}"
            paths[path] = key
            questions[key] = {
                "type": "choice",
                "instructions": f"Choose {'.'.join(path)}. {description} " + (
                    "Keep original unless the requested edit requires changing it." if editing else
                    "Choose a value that supports the requested lighting effect. Explore suitable alternatives when the prompt leaves it unspecified."),
                "criteria": {name: f"{name}: {summary(value)}"
                             for name, value in spec.options.items()},
            }

    for node in nodes:
        for name in inspect.signature(type(node).__init__).parameters:
            if name in ("self", "alias", "parent", "terminals", "node_selector", *locked):
                continue
            element = vars(node)[name]
            spec = adapt(element, sources)
            path = (node.name(), name)
            specs[path] = spec
            collect(spec, path, inspect.getdoc(type(node)) or "")
    def resolve(answers):
        return _resolve_parameters(specs, paths, answers)

    return questions, resolve


def _resolve_parameters(specs, paths, answers):
    def select(spec, path):
        if isinstance(spec, Group):
            selected = {name: select(child, (*path, str(name))) for name, child in spec.children.items()}
            changed = any(item[1] for item in selected.values())
            if not changed:
                return spec.original, False
            values = {name: item[0] for name, item in selected.items()}
            return spec.build(values), changed
        key = answers[paths[path]]["choice"] if path in paths else "original"
        return spec.options[key], key != "original"

    changes = {}
    for (node, name), spec in specs.items():
        value, changed = select(spec, (node, name))
        if changed:
            changes.setdefault(node, {})[name] = serialize(value)
    return changes
