"""Curve interpolation and persistent dynamic input integration."""
from copy import deepcopy
import unittest
import numpy as np

from backend.api.handlers import Handlers
from backend.api.protocol import decode, encode
from backend.api.runtime import Runtime


class FunctionCurveTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.runtime = Runtime()
        async def broadcast(message):
            pass
        self.handlers = Handlers(self.runtime, broadcast)
        self.runtime.load({'nodes': [
            {'id': 'curve', 'type': 'Function', 'parameters': {'number_points': 101}},
            {'id': 'source', 'type': 'ConstantArray', 'parameters': {'length': 1, 'input_value': 0.25}},
        ], 'connections': []})

    def tearDown(self):
        self.runtime.close()

    async def link(self, input):
        await self.handlers.connection_add(None, {'connectionId': input,
            'source': {'nodeId': 'source', 'element': 'data'},
            'target': {'nodeId': 'curve', 'element': input}})

    def test_linear_legacy_and_nonlinear_endpoints(self):
        curve = self.runtime.nodes['curve']
        np.testing.assert_allclose(curve.data.value, np.linspace(0, 1, 101))
        self.runtime.configure('curve', {'slopes': [0.5]})
        curve = self.runtime.nodes['curve']
        self.assertEqual(curve.data.value[50], 0.375)
        self.assertEqual(curve.data.value[0], 0)
        self.assertEqual(curve.data.value[-1], 1)
        self.runtime.configure('curve', {'slopes': [-0.5]})
        self.assertEqual(self.runtime.nodes['curve'].data.value[50], 0.625)
        for slope in (-1, 1):
            self.runtime.configure('curve', {'slopes': [slope]})
            differences = np.diff(self.runtime.nodes['curve'].data.value)
            self.assertTrue(np.all((differences >= 0) & (differences <= 0.02)))

    async def test_linked_coordinates_and_slopes_update_live_and_survive_reload(self):
        await self.link('point_p1_y')
        self.assertEqual(self.runtime.nodes['curve'].data.value[-1], 0.25)
        self.runtime.set_element('source', 'input_value', 0.7)
        self.assertAlmostEqual(self.runtime.nodes['curve'].data.value[-1], 0.7)
        await self.link('point_p0_slope')
        self.assertLess(self.runtime.nodes['curve'].data.value[50], 0.35)
        self.assertGreater(self.runtime.nodes['curve'].data.value[50], 0.175)
        await self.link('point_p0_x')
        curve = self.runtime.nodes['curve']
        self.assertEqual(curve.data.value[50], 0)
        graph = decode(encode({'type': 'graph', 'payload': {'graph': self.runtime.graph}}))['payload']['graph']
        self.runtime.load(graph, replace=True)
        self.assertAlmostEqual(self.runtime.nodes['curve'].data.value[-1], 0.7)
        await self.handlers.connection_remove(None, {'connectionId': 'point_p1_y'})
        self.assertEqual(self.runtime.nodes['curve'].data.value[-1], 1)
        self.runtime.set_element('source', 'input_value', 0.3)
        self.assertEqual(self.runtime.nodes['curve'].data.value[-1], 1)

    async def test_point_identity_survives_insertion_and_unlinked_deletion(self):
        await self.link('point_p1_y')
        self.runtime.configure('curve', {'points': [[0, 0], [0.5, 0.8], [1, 1]],
            'point_ids': ['p0', 'inserted', 'p1'], 'slopes': [0.2, -0.3]})
        curve = self.runtime.nodes['curve']
        self.assertEqual(curve.data.value[-1], 0.25)
        self.assertEqual(curve.data.value[50], 0.8)
        self.runtime.configure('curve', {'points': [[0, 0], [1, 1]], 'point_ids': ['p0', 'p1'], 'slopes': [0]})
        self.assertEqual(self.runtime.nodes['curve'].data.value[-1], 0.25)
        self.assertNotIn('point_inserted_x', self.runtime.nodes['curve'].pending_terminals)

    async def test_crossing_drivers_are_clamped_and_invalid_edits_are_atomic(self):
        await self.link('point_p0_x')
        await self.link('point_p1_x')
        self.runtime.set_element('source', 'input_value', 100)
        self.assertTrue(np.isfinite(self.runtime.nodes['curve'].data.value).all())
        self.runtime.set_element('source', 'input_value', -100)
        self.assertTrue(np.isfinite(self.runtime.nodes['curve'].data.value).all())
        before = deepcopy(self.runtime.graph)
        with self.assertRaises(ValueError):
            self.runtime.configure('curve', {'slopes': [2]})
        self.assertEqual(self.runtime.graph, before)

    def test_input_shape_and_edited_endpoint_coordinates(self):
        self.runtime.configure('curve', {'input_data': np.zeros((7, 3)),
            'points': [[0.2, 0.4], [0.8, 0.9]], 'point_ids': ['left', 'right'], 'slopes': [0]})
        data = self.runtime.nodes['curve'].data.value
        self.assertEqual(data.shape, (7, 3))
        np.testing.assert_allclose(data[0], 0.4)
        np.testing.assert_allclose(data[-1], 0.9)
