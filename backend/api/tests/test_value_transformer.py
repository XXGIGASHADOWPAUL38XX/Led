import unittest
import numpy as np

from backend.api.handlers import Handlers
from backend.api.runtime import Runtime


class ValueTransformerTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.runtime = Runtime(preview=True)

    def tearDown(self):
        self.runtime.close()

    def test_mapping_preserves_full_shapes_and_source_values(self):
        for shape in ((1,), (180,), (8, 3), (2, 4, 3)):
            values = np.linspace(0, 1, np.prod(shape)).reshape(shape)
            self.runtime.load({'nodes': [{'id': 'map', 'type': 'ValueTransformer', 'parameters': {
                'input_value': values, 'input_value_interval': [.3, .6], 'output_value_interval': [0, 1],
            }}], 'connections': []})
            self.assertEqual(self.runtime.tick(), [])
            node = self.runtime.nodes['map']
            self.assertEqual(node.output_value.value.shape, shape)
            np.testing.assert_allclose(node.output_value.value, np.clip((values - .3) / .3, 0, 1))
            np.testing.assert_array_equal(node.input_value.value, values)

    async def test_shape_is_editable_and_adopts_connected_rgb(self):
        async def broadcast(_message):
            pass
        self.runtime.load({'nodes': [
            {'id': 'rgb', 'type': 'SingleColor', 'parameters': {'number_points': 178}},
            {'id': 'map', 'type': 'ValueTransformer', 'parameters': {}},
        ], 'connections': []})
        self.runtime.configure('map', {'shape': [180]})
        self.assertEqual(self.runtime.nodes['map'].output_value.value.shape, (180,))
        await Handlers(self.runtime, broadcast).connection_add(None, {
            'source': {'nodeId': 'rgb', 'element': 'data'}, 'target': {'nodeId': 'map', 'element': 'input_value'},
        })
        self.assertEqual(self.runtime.nodes['map'].output_value.value.shape, (178, 3))
        with self.assertRaisesRegex(ValueError, 'incompatible'):
            self.runtime.configure('map', {'shape': [180, 3]})

    def test_scalar_and_reversed_ranges_remain_supported(self):
        self.runtime.load({'nodes': [{'id': 'map', 'type': 'ValueTransformer', 'parameters': {
            'input_value': .4, 'input_value_interval': [.6, .3], 'output_value_interval': [0, 1],
        }}], 'connections': []})
        self.assertEqual(self.runtime.tick(), [])
        np.testing.assert_allclose(self.runtime.nodes['map'].output_value.value, [2 / 3])
