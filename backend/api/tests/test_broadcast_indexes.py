"""Broadcast Indexes preserves row channels and validates its input shape atomically."""
from copy import deepcopy
import unittest
import numpy as np
from backend.api.handlers import Handlers
from backend.api.protocol import encode, decode
from backend.api.runtime import Runtime


class BroadcastIndexesTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.runtime = Runtime()
        async def broadcast(message):
            pass
        self.handlers = Handlers(self.runtime, broadcast)

    def tearDown(self):
        self.runtime.close()

    async def test_rgb_connection_requires_editing_the_input_shape(self):
        self.runtime.load({'nodes': [
            {'id': 'gradient', 'type': 'Gradiant', 'parameters': {'n_points': 4}},
            {'id': 'sample', 'type': 'BroadcastIndexesNode', 'parameters': {'indexes': [-1, 0, 0.5, 1, 2]}},
        ], 'connections': []})
        descriptor = self.runtime.describe(self.runtime.nodes['sample'])
        port = next(port for port in descriptor['ports'] if port['name'] == 'input_data')
        self.assertNotIn('accepts', port)
        self.assertEqual(port['shape'], [180])
        before = self.runtime.nodes['sample']
        with self.assertRaisesRegex(ValueError, 'incompatible with input data'):
            await self.handlers.connection_add(None, {'source': {'nodeId': 'gradient', 'element': 'data'},
                'target': {'nodeId': 'sample', 'element': 'input_data'}})
        self.assertIs(self.runtime.nodes['sample'], before)
        self.assertEqual(self.runtime.graph['connections'], [])
        self.runtime.configure('sample', {'shape': [4, 3]})
        await self.handlers.connection_add(None, {'source': {'nodeId': 'gradient', 'element': 'data'},
            'target': {'nodeId': 'sample', 'element': 'input_data'}})
        self.assertEqual(self.runtime.tick(), [])
        sample = self.runtime.nodes['sample']
        self.assertEqual(sample.shape.value, (4, 3))
        self.assertEqual(sample.data.value.shape, (5, 3))
        np.testing.assert_array_equal(sample.data.value, self.runtime.nodes['gradient'].data.value[[0, 0, 2, 3, 3]])

    async def test_editable_placeholder_shape_and_rejected_linked_edit(self):
        self.runtime.load({'nodes': [
            {'id': 'gradient', 'type': 'Gradiant', 'parameters': {}},
            {'id': 'sample', 'type': 'BroadcastIndexesNode', 'parameters': {}},
        ], 'connections': []})
        self.runtime.configure('sample', {'shape': [180, 3]})
        self.assertEqual(self.runtime.nodes['sample'].input_data.value.shape, (180, 3))
        await self.handlers.connection_add(None, {'source': {'nodeId': 'gradient', 'element': 'data'},
            'target': {'nodeId': 'sample', 'element': 'input_data'}})
        before = self.runtime.nodes['sample']
        graph = deepcopy(self.runtime.graph)
        with self.assertRaisesRegex(ValueError, 'incompatible with input data'):
            self.runtime.configure('sample', {'shape': [180]})
        self.assertIs(self.runtime.nodes['sample'], before)
        self.assertEqual(self.runtime.graph, graph)
        with self.assertRaisesRegex(ValueError, 'incompatible with input data'):
            self.runtime.set_element('sample', 'shape', [180])
        self.assertEqual(before.shape.value, (180, 3))
        self.assertEqual(self.runtime.tick(), [])
        restored = decode(encode({'type': 'graph', 'payload': {'graph': self.runtime.graph}}))['payload']['graph']
        self.runtime.load(restored, replace=True)
        self.assertEqual(self.runtime.nodes['sample'].data.value.shape, (180, 3))

    def test_vector_compatibility_and_multidimensional_indexes(self):
        self.runtime.load({'nodes': [{'id': 'sample', 'type': 'BroadcastIndexesNode', 'parameters': {
            'input_data': [10, 20, 30, 40], 'shape': [4], 'indexes': [[0, 0.5], [1, 0.25]],
        }}], 'connections': []})
        self.assertEqual(self.runtime.tick(), [])
        np.testing.assert_array_equal(self.runtime.nodes['sample'].data.value, [[10, 30], [40, 20]])
        with self.assertRaisesRegex(ValueError, 'incompatible with input data'):
            self.runtime.configure('sample', {'shape': [4, 3]})

    def test_invalid_shapes_leave_the_graph_running(self):
        self.runtime.load({'nodes': [{'id': 'sample', 'type': 'BroadcastIndexesNode', 'parameters': {}}], 'connections': []})
        for shape in ([], [0], [-1], [2.5], [[180, 3]], [65537], [65536, 65536]):
            with self.subTest(shape=shape), self.assertRaises(ValueError):
                self.runtime.configure('sample', {'shape': shape})
        self.runtime.set_element('sample', 'shape', [4.0, 3.0])
        self.assertEqual(self.runtime.nodes['sample'].input_data.value.shape, (4, 3))
        self.assertEqual(self.runtime.tick(), [])
