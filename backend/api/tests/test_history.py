import unittest
from unittest.mock import AsyncMock
from types import SimpleNamespace

from backend.api.runtime import Runtime
from backend.api.handlers import Handlers
from backend.api.router import Router
from backend.api.tests.test_runtime import graph


class HistoryTests(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        cls.runtime = Runtime()

    def setUp(self):
        self.runtime.load(graph(), replace=True)
        self.broadcast = AsyncMock()
        self.router = Router(Handlers(self.runtime, self.broadcast))
        self.session = SimpleNamespace(send=AsyncMock())

    def tearDown(self):
        self.runtime.close()

    async def command(self, kind, **payload):
        self.session.send.reset_mock()
        await self.router.dispatch(self.session, {"type": kind, "requestId": 1, "payload": payload})
        return self.session.send.call_args.args[0]

    async def test_slider_gesture_is_one_undo_and_keeps_processing_instances(self):
        original = self.runtime.nodes["amp"]
        for value in (0.6, 0.7, 0.8):
            await self.command("element.set", nodeId="amp", element="powering", value=value, historyGroup=1)
        self.assertEqual(len(self.router.history.entries), 1)
        self.assertEqual((await self.command("graph.undo"))["type"], "ack")
        self.assertEqual(original.powering.value, 0.5)
        self.assertIs(self.runtime.nodes["amp"], original)
        self.assertFalse(self.router.history.entries)

    async def test_add_with_connections_is_atomic_and_undo_preserves_other_nodes(self):
        original = self.runtime.nodes["amp"]
        await self.command("node.add", nodeId="clip", nodeType="Clip", parameters={}, connections=[{
            "id": "new-wire", "source": {"nodeId": "amp", "element": "data"}, "target": {"nodeId": "clip", "element": "input_value"}}])
        self.assertIn("clip", self.runtime.nodes)
        self.assertEqual(len(self.runtime.graph["connections"]), 2)
        await self.command("graph.undo")
        self.assertNotIn("clip", self.runtime.nodes)
        self.assertEqual(len(self.runtime.graph["connections"]), 1)
        self.assertIs(self.runtime.nodes["amp"], original)

    async def test_rejected_edit_does_not_enter_history_and_failed_undo_is_retained(self):
        self.assertEqual((await self.command("element.set", nodeId="amp", element="powering", value=100))["type"], "error")
        self.assertFalse(self.router.history.entries)
        await self.command("element.set", nodeId="amp", element="powering", value=0.75)
        self.router.routes["element.set"] = AsyncMock(side_effect=ValueError("Cannot restore"))
        self.assertEqual((await self.command("graph.undo"))["type"], "error")
        self.assertEqual(len(self.router.history.entries), 1)

    async def test_automatic_layout_is_not_a_user_action_and_move_undo_is_batched(self):
        await self.command("graph.move", positions={"buffer": [24, 24], "amp": [400, 24]}, recordHistory=False)
        self.assertFalse(self.router.history.entries)
        await self.command("graph.move", positions={"buffer": [48, 48], "amp": [800, 48]})
        await self.command("graph.undo")
        self.assertEqual([node["position"] for node in self.runtime.graph["nodes"]], [[24, 24], [400, 24]])

    async def test_describe_only_reads_catalog_without_adding_a_node(self):
        before = dict(self.runtime.nodes)
        message = await self.command("node.describe", nodeType="Amplitudes")
        descriptor = message["payload"]["result"]
        self.assertEqual(descriptor["type"], "Amplitudes")
        self.assertTrue(any(element["name"] == "freq_bins" for element in descriptor["elements"]))
        self.assertEqual(self.runtime.nodes, before)
        self.assertFalse(self.router.history.entries)

    async def test_enum_and_structural_configuration_can_be_undone(self):
        await self.command("node.add", nodeId="trigger", nodeType="Trigger")
        await self.command("element.set", nodeId="trigger", element="trigger_mode", value="GREATER")
        await self.command("graph.undo")
        self.assertEqual(self.runtime.nodes["trigger"].trigger_mode.value.name, "EQUAL")
        await self.command("node.add", nodeId="constant", nodeType="ConstantArray")
        length = self.runtime.nodes["constant"].length.value
        await self.command("node.configure", nodeId="constant", parameters={"length": 25})
        await self.command("graph.undo")
        self.assertEqual(self.runtime.nodes["constant"].length.value, length)

    async def test_removal_undo_restores_connections_and_noop_moves_are_not_recorded(self):
        original = self.runtime.nodes["buffer"]
        await self.command("node.move", nodeId="amp", position=[350, 0])
        self.assertFalse(self.router.history.entries)
        await self.command("node.remove", nodeId="amp")
        await self.command("graph.undo")
        self.assertIn("amp", self.runtime.nodes)
        self.assertEqual(len(self.runtime.graph["connections"]), 1)
        self.assertIs(self.runtime.nodes["buffer"], original)
