import unittest
import numpy as np

from backend.api.handlers import Handlers
from backend.api.runtime import Runtime


class CorrelateTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.runtime = Runtime(preview=True)

    def tearDown(self):
        self.runtime.close()

    def test_rgb_spreads_rows_without_crossing_channels_or_mutating_input(self):
        source = np.zeros((180, 3))
        source[80, 0], source[88, 2] = 255, 100
        self.runtime.load({'nodes': [{'id': 'spread', 'type': 'Correlate', 'parameters': {
            'input_data': source, 'correlation_step': .1,
        }}], 'connections': []})
        self.assertEqual(self.runtime.tick(), [])
        result = self.runtime.nodes['spread'].data.value
        distances = np.arange(180)
        np.testing.assert_allclose(result[:, 0], 255 * np.maximum(1 - abs(distances - 80) / 9, 0))
        np.testing.assert_allclose(result[:, 2], 100 * np.maximum(1 - abs(distances - 88) / 9, 0))
        np.testing.assert_array_equal(result[:, 1], 0)
        np.testing.assert_array_equal(self.runtime.nodes['spread'].input_data.value, source)

    def test_zero_weight_does_not_change_negative_values(self):
        for strength, span in ((0, 1), (1, 0), (1, .01)):
            source = np.array([-3., -1., -2.])
            self.runtime.load({'nodes': [{'id': 'spread', 'type': 'Correlate', 'parameters': {
                'input_data': source, 'correlation_offset': strength, 'correlation_step': span,
            }}], 'connections': []})
            self.assertEqual(self.runtime.tick(), [])
            np.testing.assert_array_equal(self.runtime.nodes['spread'].data.value, source)

    def test_average_blends_rgb_and_normalizes_at_boundaries(self):
        source = np.tile([255., 0., 0.], (20, 1))
        source[10:] = [0, 0, 255]
        self.runtime.load({'nodes': [{'id': 'blend', 'type': 'Correlate', 'parameters': {
            'input_data': source, 'correlation_step': .5, 'mode': 'average',
        }}], 'connections': []})
        self.assertEqual(self.runtime.tick(), [])
        result = self.runtime.nodes['blend'].data.value
        weights = np.array([.2, .4, .6, .8, 1, .8, .6, .4, .2])
        expected = np.stack([np.convolve(source[:, channel], weights, mode='same') for channel in range(3)], axis=1)
        expected /= np.convolve(np.ones(20), weights, mode='same')[:, None]
        np.testing.assert_allclose(result, expected)
        np.testing.assert_allclose(result.sum(axis=1), 255)
        self.assertTrue(np.all(result[9:11, [0, 2]] > 0))
        np.testing.assert_array_equal(self.runtime.nodes['blend'].input_data.value, source)

    async def test_shape_adopts_rgb_and_rejects_incompatible_edits(self):
        async def broadcast(_message):
            pass
        handlers = Handlers(self.runtime, broadcast)
        self.runtime.load({'nodes': [
            {'id': 'rgb', 'type': 'SingleColor', 'parameters': {'number_points': 178}},
            {'id': 'spread', 'type': 'Correlate', 'parameters': {}},
        ], 'connections': []})
        self.runtime.configure('spread', {'shape': [20, 4]})
        self.assertEqual(self.runtime.nodes['spread'].data.value.shape, (20, 4))
        await handlers.connection_add(None, {'source': {'nodeId': 'rgb', 'element': 'data'},
                                              'target': {'nodeId': 'spread', 'element': 'input_data'}})
        self.assertEqual(tuple(self.runtime.nodes['spread'].shape.value), (178, 3))
        self.assertEqual(self.runtime.nodes['spread'].data.value.shape, (178, 3))
        with self.assertRaisesRegex(ValueError, 'incompatible'):
            self.runtime.configure('spread', {'shape': [180, 3]})

    def test_legacy_connections_move_and_migration_runs_once(self):
        self.runtime.load({'nodes': [
            {'id': 'signal', 'type': 'ConstantArray', 'parameters': {'length': 178, 'input_value': .25}},
            {'id': 'span', 'type': 'ConstantArray', 'parameters': {'length': 1, 'input_value': .1}},
            {'id': 'linear', 'type': 'LinearAmplitudesTransformer', 'position': [860, 0], 'parameters': {
                'input_data': {'nodeId': 'signal', 'element': 'data'}, 'correlation_step': .1, 'log': .5,
            }},
        ], 'connections': [
            {'id': 'signal', 'source': {'nodeId': 'signal', 'element': 'data'},
             'target': {'nodeId': 'linear', 'element': 'input_data'}},
            {'id': 'span', 'source': {'nodeId': 'span', 'element': 'data'},
             'target': {'nodeId': 'linear', 'element': 'correlation_step'}},
        ]})
        self.assertEqual(self.runtime.tick(), [])
        np.testing.assert_allclose(self.runtime.nodes['linear'].data.value, .5)
        self.assertEqual(self.runtime.nodes['linear correlation'].data.value.shape, (178,))
        self.assertIs(self.runtime.nodes['linear correlation'].correlation_step._value_source,
                      self.runtime.nodes['span'].data)
        self.runtime.load(self.runtime.graph)
        self.assertEqual(len(self.runtime.nodes), 4)
