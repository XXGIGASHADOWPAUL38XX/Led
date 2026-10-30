"""Route handlers translate API commands into main-thread runtime operations."""
import asyncio
from copy import deepcopy
import math
from uuid import uuid4

from .protocol import event


class Handlers:
    def __init__(self, runtime, broadcast):
        self.runtime, self.broadcast = runtime, broadcast

    async def _load(self, graph, replace=False):
        snapshot = self.runtime.load(graph, replace=replace)
        await self.broadcast(event("graph.snapshot", snapshot, self.runtime.revision))
        return {"revision": self.runtime.revision}

    async def graph_get(self, session, payload):
        await session.send(event("graph.snapshot", self.runtime.snapshot(), self.runtime.revision))
        return {"graph": self.runtime.graph}

    async def graph_load(self, session, payload):
        if "connects" in payload["graph"]:
            snapshot = self.runtime.load_template(payload["graph"], replace=True)
            await self.broadcast(event("graph.snapshot", snapshot, self.runtime.revision))
            return {"revision": self.runtime.revision}
        return await self._load(payload["graph"], replace=True)

    async def node_add(self, session, payload):
        graph = deepcopy(self.runtime.graph)
        node_id = payload.get("nodeId", str(uuid4()))
        graph["nodes"].append({"id": node_id, "type": payload["nodeType"], "position": payload.get("position", [0, 0]), "parameters": payload.get("parameters", {})})
        graph["connections"].extend(payload.get("connections", []))
        await self._load(graph)
        return {"nodeId": node_id}

    async def graph_restore(self, session, payload):
        return await self._load(payload["graph"])

    async def node_describe(self, session, payload):
        cls = self.runtime.catalog.classes[payload["nodeType"]]
        node = next(node for node in self.runtime.catalog.prototypes[1:] if type(node) is cls)
        descriptor = self.runtime.describe(node)
        for element in descriptor["elements"]:
            if element["kind"] == "sequence" and any(source not in self.runtime.nodes for source in self.runtime._references(element["value"])):
                element["value"] = []
        return descriptor

    async def node_remove(self, session, payload):
        node_id = payload["nodeId"]
        if node_id not in self.runtime.nodes:
            raise ValueError("Unknown node")
        graph = deepcopy(self.runtime.graph)
        # Never leave hidden constructor references pointing at a removed node.
        if any(node_id in self.runtime._references(item.get("parameters", {})) for item in graph["nodes"] if item["id"] != node_id):
            raise ValueError("Clear references to this node before removing it")
        graph["nodes"] = [item for item in graph["nodes"] if item["id"] != node_id]
        graph["connections"] = [edge for edge in graph["connections"] if node_id not in (edge["source"]["nodeId"], edge["target"]["nodeId"])]
        return await self._load(graph)

    async def node_configure(self, session, payload):
        snapshot = self.runtime.configure(payload["nodeId"], payload["parameters"])
        await self.broadcast(event("graph.snapshot", snapshot, self.runtime.revision))
        return {"revision": self.runtime.revision}

    async def node_start(self, session, payload):
        node = self.runtime.nodes[payload["nodeId"]]
        if node.nodeName not in {"StreamMic", "StreamPlayer"}:
            raise ValueError("This node has no manual stream lifecycle")
        node.start()

    async def node_stop(self, session, payload):
        node = self.runtime.nodes[payload["nodeId"]]
        if node.nodeName not in {"StreamMic", "StreamPlayer"}:
            raise ValueError("This node has no manual stream lifecycle")
        node.stop()

    async def node_move(self, session, payload):
        await self.graph_move(session, {"positions": {payload["nodeId"]: payload["position"]}})
        return payload

    async def graph_move(self, session, payload):
        positions = payload["positions"]
        nodes = {node["id"]: node for node in self.runtime.graph["nodes"]}
        if not positions.keys() <= nodes.keys():
            raise ValueError("Unknown node")
        for position in positions.values():
            if len(position) != 2 or any(type(value) not in (int, float) or not math.isfinite(value) for value in position):
                raise ValueError("Position must contain two finite coordinates")
        for node_id, position in positions.items():
            nodes[node_id]["position"] = position
        self.runtime.revision += 1
        await self.broadcast(event("state.update", {"positions": positions}, self.runtime.revision))
        return payload

    async def connection_add(self, session, payload):
        graph = deepcopy(self.runtime.graph)
        edge = {"id": payload.get("connectionId", str(uuid4())), "source": payload["source"], "target": payload["target"]}
        self._disconnect(graph, {existing["id"] for existing in graph["connections"] if existing["id"] == edge["id"] or existing["target"] == edge["target"]}, edge["target"])
        target = edge["target"]
        node = self.runtime.nodes[target["nodeId"]]
        spec = next(item for item in graph["nodes"] if item["id"] == target["nodeId"])
        target["element"], renamed = node.connect_input(target["element"], edge["source"], spec.setdefault("parameters", {}))
        for existing in graph["connections"]:
            source = existing["source"]
            if source["nodeId"] == target["nodeId"] and source["element"] in renamed:
                source["element"] = renamed[source["element"]]
        graph["connections"] = [existing for existing in graph["connections"] if existing["target"] != target]
        graph["connections"].append(edge)
        await self._load(graph)
        return edge

    async def connection_remove(self, session, payload):
        graph = deepcopy(self.runtime.graph)
        if not any(edge["id"] == payload["connectionId"] for edge in graph["connections"]):
            raise ValueError("Unknown connection")
        self._disconnect(graph, {payload["connectionId"]})
        return await self._load(graph)

    def _disconnect(self, graph, connection_ids, keep_target=None):
        nodes = {node["id"]: node for node in graph["nodes"]}
        removed_outputs = set()
        for edge in graph["connections"]:
            if edge["id"] not in connection_ids or edge["target"] == keep_target:
                continue
            parameters = nodes[edge["target"]["nodeId"]].setdefault("parameters", {})
            node = self.runtime.nodes[edge["target"]["nodeId"]]
            removed_outputs.update((node.name(), name) for name in node.disconnect_input(edge["target"]["element"], parameters))
        downstream = {edge["id"] for edge in graph["connections"] if (edge["source"]["nodeId"], edge["source"]["element"]) in removed_outputs}
        if downstream:
            self._disconnect(graph, downstream, keep_target)
        graph["connections"] = [edge for edge in graph["connections"] if edge["id"] not in connection_ids]

    async def element_set(self, session, payload):
        result = self.runtime.set_element(payload["nodeId"], payload["element"], payload["value"])
        await self.broadcast(event("state.update", {**result, "node": self.runtime.describe(self.runtime.nodes[payload["nodeId"]])}, self.runtime.revision))
        return result

    async def subscribe(self, session, payload):
        subscriptions = set()
        for item in payload["elements"]:
            node_id, name = item["nodeId"], item["element"]
            self.runtime.element(node_id, name)
            if name not in self.runtime.nodes[node_id].pending_terminals:
                raise ValueError("Only graph ports may be streamed")
            subscriptions.add((node_id, name))
        session.subscriptions = tuple(sorted(subscriptions))
        return {"elements": payload["elements"]}

    async def frame_ack(self, session, payload):
        if payload["sequence"] == session.in_flight:
            session.in_flight = None

    def _player(self, payload):
        node = self.runtime.players[payload["nodeId"]]
        return node

    @staticmethod
    def _track_id(entry):
        return str(entry.get("webpage_url") or entry.get("url") or entry.get("id"))

    def player_state(self, node):
        with node._data_lock:
            tracks = [{"id": self._track_id(entry), **node._entry_metadata(entry), "loaded": index < len(node._tracks) and node._tracks[index] is not None}
                      for index, entry in enumerate(node._entries)]
            index = node._current_track_index
        return {"nodeId": node.name(), "tracks": tracks,
                "activeTrackId": tracks[index]["id"] if 0 <= index < len(tracks) else None,
                "playing": node._is_playing, "position": max(0.0, node._current_position()) if index >= 0 else 0.0}

    async def _player_update(self, node):
        state = self.player_state(node)
        await self.broadcast(event("player.update", state, self.runtime.revision))
        return state

    async def player_play(self, session, payload):
        node = self._player(payload)
        if not node._entries:
            node.start()
            return {"loading": True}
        index = next((index for index, entry in enumerate(node._entries) if self._track_id(entry) == payload.get("trackId")), 0)
        if "trackId" in payload and self._track_id(node._entries[index]) != payload["trackId"]:
            raise ValueError("Unknown track")
        if node._tracks[index] is None:
            raise ValueError("Track is still loading")
        node.on_play_requested(index)
        return await self._player_update(node)

    async def player_pause(self, session, payload):
        node = self._player(payload)
        if node._current_track_index >= 0:
            node.on_pause_requested(node._current_track_index)
        return await self._player_update(node)

    async def player_seek(self, session, payload):
        node = self._player(payload)
        index = node._current_track_index
        seconds = payload["position"]
        if index < 0 or node._tracks[index] is None or type(seconds) not in (int, float) or not math.isfinite(seconds):
            raise ValueError("Select a loaded track and a finite seek position")
        audio, rate = node._tracks[index]
        duration = len(audio) / rate
        node.on_seek_requested(index, max(0, min(1, seconds / duration)) if duration else 0)
        return await self._player_update(node)

    async def player_search(self, session, payload):
        from backend.nodes.playlist_player.soundcloud.api import search_tracks
        node = self._player(payload)
        results = await asyncio.to_thread(search_tracks, payload["query"], node._ydl_opts(), 10)
        if self.runtime.players.get(payload["nodeId"]) is not node:
            raise ValueError("Playlist changed during search")
        results = results or []
        session.search_results[node.name()] = results
        tracks = [{"id": self._track_id(entry), "title": entry.get("title", ""), "artist": entry.get("uploader", ""), "duration": entry.get("duration") or 0}
                  for entry in results]
        await session.send(event("player.results", {"nodeId": node.name(), "query": payload["query"], "tracks": tracks}, self.runtime.revision))
        return {"count": len(tracks)}

    async def playlist_add(self, session, payload):
        node = self._player(payload)
        track_id = payload["trackId"]
        if any(self._track_id(entry) == track_id for entry in node._entries):
            raise ValueError("Track already queued")
        track = next((entry for entry in session.search_results.get(node.name(), []) if self._track_id(entry) == track_id), None)
        if track is None:
            raise ValueError("Choose a track returned by search")
        node.add_music(track)
        return {"loading": True}

    async def playlist_remove(self, session, payload):
        node = self._player(payload)
        index = next((at for at, entry in enumerate(node._entries) if self._track_id(entry) == payload["trackId"]), None)
        if index is None:
            raise ValueError("Unknown track")
        if index == node._current_track_index:
            node.on_pause_requested(index)
            node._current_track_index = -1
        elif index < node._current_track_index:
            node._current_track_index -= 1
        node.remove_music(index)
        return await self._player_update(node)
