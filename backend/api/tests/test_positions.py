import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock

from backend.api.handlers import Handlers


class PositionTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.runtime = SimpleNamespace(graph={"nodes": [{"id": "a", "position": [0, 0]}, {"id": "b", "position": [0, 0]}]}, revision=1)
        self.broadcast = AsyncMock()
        self.handlers = Handlers(self.runtime, self.broadcast)

    async def test_batch_broadcasts_once_without_rebuilding_nodes(self):
        nodes = list(self.runtime.graph["nodes"])
        payload = {"positions": {"a": [24, 24], "b": [400, 24]}}
        await self.handlers.graph_move(None, payload)
        self.assertEqual([node["position"] for node in nodes], [[24, 24], [400, 24]])
        self.assertEqual(self.runtime.revision, 2)
        self.broadcast.assert_awaited_once()
        self.assertEqual(self.broadcast.call_args.args[0]["payload"], payload)

    async def test_invalid_batch_never_partially_moves_nodes(self):
        for positions in ({"a": [1, 2], "b": [float("nan"), 0]}, {"a": [1, 2], "missing": [0, 0]}):
            with self.assertRaises(ValueError):
                await self.handlers.graph_move(None, {"positions": positions})
            self.assertEqual([node["position"] for node in self.runtime.graph["nodes"]], [[0, 0], [0, 0]])
        self.assertEqual(self.runtime.revision, 1)
        self.broadcast.assert_not_awaited()
