"""Graph deltas: what changed between two snapshots, so clients keep untouched nodes and their streams."""
from .protocol import encode


def _changed(before, after):
    known = {item["id"]: encode(item) for item in before}
    return [item for item in after if known.get(item["id"]) != encode(item)]


def diff(before, after, base):
    """A graph.patch payload turning `before` (the client's state at revision `base`) into `after`.

    Lists are rebuilt from the id orders, so removals and moves need no separate fields.
    """
    return {
        "base": base,
        "nodeOrder": [node["id"] for node in after["graph"]["nodes"]],
        "connectionOrder": [connection["id"] for connection in after["graph"]["connections"]],
        "nodes": _changed(before["graph"]["nodes"], after["graph"]["nodes"]),
        "connections": _changed(before["graph"]["connections"], after["graph"]["connections"]),
        "descriptors": _changed(before["nodes"], after["nodes"]),
    }
