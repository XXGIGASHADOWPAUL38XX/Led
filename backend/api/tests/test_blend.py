import unittest
from backend.api.schemas import parse_command

import numpy as np

from backend.api.handlers import Handlers
from backend.api.protocol import decode, encode
from backend.api.runtime import Runtime


class BlendTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.runtime = Runtime(preview=True)
        self.addCleanup(self.runtime.close)

    def load(self, inputs):
        self.runtime.load({'nodes': [{'id': 'blend', 'type': 'Blend', 'parameters': {'inputs': inputs}}], 'connections': []})
        return self.runtime.nodes['blend']

    def test_normalization_broadcasting_and_input_storage(self):
        source = np.array([[255., 0, 0], [0, 255, 0]])
        inputs = [{'source': source, 'weight': 1}, {'source': [0, 0, 255], 'weight': 2},
                  {'source': 10, 'weight': 2}, {'source': 20, 'weight': 1}, {'source': 30, 'weight': 2}]
        node = self.load(inputs)
        np.testing.assert_allclose(node.data.value, (source + np.array([0, 0, 255]) * 2 + 100) / 8)
        self.assertFalse(np.shares_memory(node.data.value, node.sources[0].value))
        np.testing.assert_array_equal(node.sources[0].value, source)

    def test_empty_zero_weights_and_invalid_edits(self):
        node = self.load([])
        np.testing.assert_array_equal(node.data.value, [0])
        node = self.load([{'source': [20, 40], 'weight': 0}])
        np.testing.assert_array_equal(node.data.value, [0, 0])
        for inputs in ([{'source': [1], 'weight': -1}], [{'source': [1], 'weight': float('nan')}],
                       [{'source': [1, 2], 'weight': 1}, {'source': [1, 2, 3], 'weight': 1}]):
            with self.subTest(inputs=inputs), self.assertRaises(ValueError):
                self.runtime.configure('blend', {'inputs': inputs})
            self.assertIs(self.runtime.nodes['blend'], node)

    async def test_drag_live_updates_weights_removal_and_roundtrip(self):
        self.runtime.load({'nodes': [
            {'id': 'a', 'type': 'ConstantArray', 'parameters': {'length': 3, 'input_value': 10}},
            {'id': 'b', 'type': 'ConstantArray', 'parameters': {'length': 3, 'input_value': 30}},
            {'id': 'blend', 'type': 'Blend', 'parameters': {}},
        ], 'connections': []})
        async def broadcast(_message):
            pass
        handlers = Handlers(self.runtime, broadcast)
        for source in ('a', 'b'):
            await handlers.connection_add(None, parse_command('connection.add', {'source': {'nodeId': source, 'element': 'data'},
                                                  'target': {'nodeId': 'blend', 'element': 'add_element'}}))
        self.runtime.configure('blend', {'inputs': [
            {'source': {'nodeId': 'a', 'element': 'data'}, 'weight': 1},
            {'source': {'nodeId': 'b', 'element': 'data'}, 'weight': 3},
        ]})
        self.assertEqual(self.runtime.tick(), [])
        np.testing.assert_allclose(self.runtime.nodes['blend'].data.value, [25] * 3)
        self.runtime.nodes['a'].data.value[:] = 50
        self.runtime.nodes['blend'].c_update()
        np.testing.assert_allclose(self.runtime.nodes['blend'].data.value, [35] * 3)
        saved = decode(encode({'type': 'template', 'payload': {'graph': self.runtime.graph}}))['payload']['graph']
        self.runtime.load(saved, replace=True)
        self.assertEqual(self.runtime.tick(), [])
        np.testing.assert_allclose(self.runtime.nodes['blend'].data.value, [25] * 3)
        self.runtime.configure('blend', {'inputs': [{'source': {'nodeId': 'b', 'element': 'data'}, 'weight': 3}]})
        self.assertEqual(self.runtime.tick(), [])
        np.testing.assert_allclose(self.runtime.nodes['blend'].data.value, [30] * 3)
        self.assertEqual([edge['source']['nodeId'] for edge in self.runtime.graph['connections']], ['b'])
