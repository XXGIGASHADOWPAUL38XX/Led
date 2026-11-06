import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
import numpy as np

from backend.api.handlers import Handlers
from backend.api.runtime import Runtime


class DimensionalFlatteningTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.runtime = Runtime(preview=True)

    def tearDown(self):
        self.runtime.close()

    def test_variable_dimensions_fit_and_publish_scalar_coordinates(self):
        samples = np.tile(np.eye(5), (8, 1)) * np.repeat(np.linspace(.1, 1, 8), 5)[:, None]
        for dimensions in (2, 3, 5):
            with self.subTest(dimensions=dimensions):
                self.runtime.load({'nodes': [{'id': 'nmf', 'type': 'DimensionalFlattening', 'parameters': {
                    'shape': [5], 'dimensions': dimensions, 'calibration_samples': len(samples),
                }}], 'connections': []}, replace=True)
                node = self.runtime.nodes['nmf']
                for vector in samples:
                    node.input_data.value[:] = vector
                    node.c_update()
                node.future.result(timeout=5)
                events = []
                node.x.valueChanged.connect(lambda value: events.append(np.array(value)))
                node.input_data.value[:] = [.2, .4, .6, .8, 1]
                node.c_update()
                self.assertEqual(node.model[2].shape, (dimensions, 5))
                self.assertEqual(node.data.value.shape, (1, dimensions))
                self.assertTrue(np.isfinite(node.data.value).all() and (node.data.value >= 0).all())
                self.assertEqual(len(events), 1)
                for index, coordinate in enumerate(node.coordinates):
                    np.testing.assert_array_equal(coordinate.value, node.data.value[:, index])
                np.testing.assert_array_equal(node.xy.value, node.data.value[:, :2])

    def test_dimension_changes_clear_saved_model_and_keep_xy_consumers(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / 'model.npz'
            np.savez(path, minimum=np.zeros(4), scale=np.ones(4), components=np.eye(4)[:2])
            self.runtime.close()
            self.runtime = Runtime()
            self.runtime.load({'nodes': [
                {'id': 'nmf', 'type': 'DimensionalFlattening', 'parameters': {'shape': [4], 'model_path': str(path)}},
                {'id': 'history', 'type': 'Window', 'parameters': {'input_data': {'nodeId': 'nmf', 'element': 'xy'}, 'shape': [1, 2]}},
                {'id': 'average', 'type': 'AveragedWindowFct', 'parameters': {'window': {'nodeId': 'history', 'element': 'data'}, 'avg_axis': 0}},
                {'id': 'movement', 'type': 'OperatorPipeline', 'parameters': {'arguments': [
                    {'nodeId': 'nmf', 'element': 'xy'}, '-', {'nodeId': 'average', 'element': 'data'},
                ]}},
            ], 'connections': []})
            self.runtime.configure('nmf', {'dimensions': 3})
            node = self.runtime.nodes['nmf']
            self.assertEqual(node.model_path.value, '')
            self.assertIsNone(node.model)
            self.assertEqual(node.data.value.shape, (1, 3))
            self.assertEqual(self.runtime.nodes['history'].input_data.value.shape, (1, 2))
            self.assertEqual(self.runtime.nodes['movement'].data.value.shape, (1, 2))
            self.runtime.set_element('nmf', 'dimensions', 4)
            node.data.value[0] = [1, 2, 3, 4]
            np.testing.assert_array_equal(node.xy.value, [[1, 2]])
            np.testing.assert_array_equal(node.dimension_4.value, [4])
            with self.assertRaisesRegex(ValueError, 'Dimensions'):
                self.runtime.configure('nmf', {'dimensions': 5})
            graph = self.runtime.graph | {'nodes': self.runtime.graph['nodes'] + [
                {'id': 'sink', 'type': 'OperatorPipeline', 'parameters': {'arguments': [{'nodeId': 'nmf', 'element': 'z'}]}},
            ], 'connections': [{'id': 'z-wire', 'source': {'nodeId': 'nmf', 'element': 'z'}, 'target': {'nodeId': 'sink', 'element': 'nmf:z'}}]}
            self.runtime.load(graph)
            with self.assertRaisesRegex(ValueError, 'Disconnect'):
                self.runtime.configure('nmf', {'dimensions': 2})

    def test_saved_model_loads_without_live_calibration_and_checks_dimensions(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / 'model.npz'
            np.savez(path, minimum=np.zeros(3), scale=np.ones(3), components=[[1, 0, 0], [0, 1, 0]])
            graph = {'nodes': [{'id': 'nmf', 'type': 'DimensionalFlattening', 'parameters': {
                'shape': [3], 'model_path': str(path),
            }}], 'connections': []}
            self.runtime.close()
            self.runtime = Runtime()
            self.runtime.load(graph)
            node = self.runtime.nodes['nmf']
            np.testing.assert_array_equal(node.calibration.value, [1, 1])
            node.input_data.value[:] = [2, 3, 4]
            node.c_update()
            np.testing.assert_array_equal(node.data.value, [[2, 3]])
            self.assertIsNone(node.future)
            self.runtime.set_element('nmf', 'model_path', '')
            self.assertIsNone(node.model)
            np.testing.assert_array_equal(node.calibration.value, [0, 0])
            np.savez(path, minimum=np.zeros(2), scale=np.ones(2), components=np.eye(2))
            with self.assertRaisesRegex(ValueError, 'compatible'):
                self.runtime.load(graph, replace=True)
            np.savez(path, minimum=np.zeros(3), scale=np.ones(3), components=np.eye(3))
            with self.assertRaisesRegex(ValueError, 'compatible'):
                self.runtime.load(graph, replace=True)
            graph['nodes'][0]['parameters']['dimensions'] = 3
            self.runtime.load(graph, replace=True)
            node = self.runtime.nodes['nmf']
            node.input_data.value[:] = [4, 5, 6]
            node.c_update()
            np.testing.assert_array_equal(node.data.value, [[4, 5, 6]])
            np.testing.assert_array_equal(node.z.value, [6])

    def test_dimension_bounds_follow_the_calibration_sample_count(self):
        self.runtime.load({'nodes': [{'id': 'nmf', 'type': 'DimensionalFlattening', 'parameters': {
            'shape': [8], 'calibration_samples': 4,
        }}], 'connections': []})
        self.assertEqual(self.runtime.nodes['nmf'].dimensions.maximum, 4)
        self.runtime.set_element('nmf', 'calibration_samples', 8)
        self.assertEqual(self.runtime.nodes['nmf'].dimensions.maximum, 8)
        self.runtime.configure('nmf', {'dimensions': 5})
        self.assertEqual(self.runtime.nodes['nmf'].data.value.shape, (1, 5))

    async def test_calibration_normalizes_units_and_projection_stays_fixed(self):
        self.runtime.load({'nodes': [{'id': 'nmf', 'type': 'DimensionalFlattening', 'parameters': {
            'shape': [3], 'calibration_samples': 32,
        }}], 'connections': []})
        node = self.runtime.nodes['nmf']
        for angle in np.arange(32) * 2 * np.pi / 32:
            node.input_data.value[:] = [np.sin(angle), 1000 * np.cos(angle), 5]
            node.c_update()
        node.future.result(timeout=5)
        node.input_data.value[:] = [1, 0, 5]
        node.c_update()
        self.assertEqual(node.data.value.shape, (1, 2))
        np.testing.assert_array_equal(node.x.value, node.data.value[:, 0])
        np.testing.assert_array_equal(node.y.value, node.data.value[:, 1])
        minimum, scale, components = node.model
        np.testing.assert_allclose(minimum, [-1, -1000, 5])
        np.testing.assert_allclose(scale, [2, 2000, 1])
        self.assertTrue((components >= 0).all() and (node.data.value >= 0).all())
        np.testing.assert_allclose(np.linalg.norm(components, axis=1), 1)
        np.testing.assert_allclose(node.data.value[0] @ components, [1, .5, 0], atol=1e-3)
        fixed = tuple(value.copy() for value in node.model)
        first = node.data.value.copy()
        for angle in np.arange(100) / 10:
            node.input_data.value[:] = [np.sin(angle), 1000 * np.cos(angle), 5]
            node.c_update()
        for actual, expected in zip(node.model, fixed):
            np.testing.assert_array_equal(actual, expected)
        node.input_data.value[:] = [1, 0, 5]
        node.c_update()
        np.testing.assert_array_equal(node.data.value, first)
        node.input_data.value[:] = [-2, -2000, 5]
        node.c_update()
        np.testing.assert_array_equal(node.data.value, [[0, 0]])
        async def broadcast(_message):
            pass
        await Handlers(self.runtime, broadcast).node_recalibrate(None, {'nodeId': 'nmf'})
        self.assertIsNone(node.model)
        np.testing.assert_array_equal(node.calibration.value, [0, 0])
        np.testing.assert_array_equal(node.x.value, [0])
        np.testing.assert_array_equal(node.y.value, [0])

    def test_static_silence_does_not_finish_calibration_and_shapes_can_change(self):
        self.runtime.load({'nodes': [{'id': 'nmf', 'type': 'DimensionalFlattening', 'parameters': {
            'shape': [3], 'calibration_samples': 4,
        }}], 'connections': []})
        node = self.runtime.nodes['nmf']
        for _ in range(20):
            node.c_update()
        self.assertEqual(len(node.samples), 1)
        self.assertIsNone(node.future)
        self.runtime.configure('nmf', {'shape': [2, 2]})
        node = self.runtime.nodes['nmf']
        self.assertEqual(node.data.value.shape, (1, 2))
        node.data.value[0] = [2, 3]
        np.testing.assert_array_equal(node.x.value, [2])
        np.testing.assert_array_equal(node.y.value, [3])
        with self.assertRaisesRegex(ValueError, 'at least two features'):
            self.runtime.configure('nmf', {'shape': [1]})
