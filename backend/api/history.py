"""Bounded command inverses; array frames and playback never enter history."""
from collections import deque
from copy import deepcopy


class History:
    structural = {"node.add", "node.remove", "node.configure", "connection.add", "connection.remove", "graph.load", "graph.restore"}
    commands = structural | {"element.set", "node.move", "graph.move"}

    def __init__(self, runtime):
        self.runtime = runtime
        self.entries = deque(maxlen=100)

    def capture(self, kind, payload):
        if kind == "element.set":
            element = {item["name"]: item for item in self.runtime.describe(self.runtime.nodes[payload["nodeId"]])["elements"]}[payload["element"]]
            value = self.runtime.element(payload["nodeId"], payload["element"]).value if element["kind"] == "data" else element["value"]
            return kind, {"nodeId": payload["nodeId"], "element": payload["element"],
                          "value": deepcopy(value)}
        if kind in {"node.move", "graph.move"}:
            desired = {payload["nodeId"]: payload["position"]} if kind == "node.move" else payload["positions"]
            positions = {node["id"]: node["position"][:] for node in self.runtime.graph["nodes"] if node["id"] in desired}
            return None if positions == desired else ("graph.move", {"positions": positions})
        return "graph.restore", {"graph": deepcopy(self.runtime.graph)}

    def record(self, inverse, session, kind, payload):
        group = payload.get("historyGroup")
        key = (session, group, kind, payload.get("nodeId"), payload.get("element")) if group is not None else None
        if key is None or not self.entries or self.entries[-1][1] != key:
            self.entries.append((inverse, key))

    def peek(self):
        if not self.entries:
            raise ValueError("Nothing to undo")
        return self.entries[-1][0]
