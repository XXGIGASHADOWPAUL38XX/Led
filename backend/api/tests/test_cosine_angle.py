import unittest

import numpy as np

from backend.api.runtime import Runtime


class CosineAngleTests(unittest.TestCase):
    def test_quadrants_magnitude_and_origin(self):
        runtime = Runtime(preview=True)
        self.addCleanup(runtime.close)
        runtime.load({'nodes': [{'id': 'angle', 'type': 'CosineAngle', 'parameters': {
            'input_data': [[3, 0], [0, 4], [-2, 0], [0, -5], [3, 3], [0, 0]],
        }}], 'connections': []})
        self.assertEqual(runtime.tick(), [])
        values = runtime.nodes['angle'].data.value
        np.testing.assert_allclose(values, [0, np.pi / 2, np.pi, -np.pi / 2, np.pi / 4, 0])
        np.testing.assert_allclose(np.cos(values) ** 2 + np.sin(values) ** 2, 1)

    def test_adaptive_rows_and_fixed_xy_columns(self):
        runtime = Runtime(preview=True)
        self.addCleanup(runtime.close)
        runtime.load({'nodes': [
            {'id': 'nmf', 'type': 'DimensionalFlattening', 'parameters': {}},
            {'id': 'angle', 'type': 'CosineAngle', 'parameters': {'input_data': {'nodeId': 'nmf', 'element': 'data'}}},
        ], 'connections': []})
        nmf, node = runtime.nodes['nmf'], runtime.nodes['angle']
        nmf.data.value[0] = [3, 4]
        node.c_update()
        np.testing.assert_allclose(node.data.value, [np.arctan2(4, 3)])
        self.assertEqual(runtime.describe(node)['ports'][0]['accepts'], [0, 2])
        runtime.load({'nodes': [{'id': 'angle', 'type': 'CosineAngle', 'parameters': {'shape': [4, 2]}}], 'connections': []})
        self.assertEqual(runtime.nodes['angle'].data.value.shape, (4,))
        with self.assertRaises(ValueError):
            runtime.configure('angle', {'shape': [4, 3]})
