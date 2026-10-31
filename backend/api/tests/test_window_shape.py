"""Editable Window frame shapes and template8's scalar history."""
from pathlib import Path
import unittest
import numpy as np
from backend.api.handlers import Handlers
from backend.api.protocol import decode
from backend.api.runtime import Runtime


class WindowShapeTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.runtime = Runtime()
        async def broadcast(message):
            pass
        self.handlers = Handlers(self.runtime, broadcast)

    def tearDown(self):
        self.runtime.close()

    async def test_scalar_input_requires_matching_configured_shape(self):
        self.runtime.load({'nodes': [
            {'id': 'source', 'type': 'ConstantArray', 'parameters': {'length': 1, 'input_value': 0.8}},
            {'id': 'history', 'type': 'Window', 'parameters': {'length': 5}},
        ], 'connections': []})
        connection = {'source': {'nodeId': 'source', 'element': 'data'}, 'target': {'nodeId': 'history', 'element': 'input_data'}}
        with self.assertRaisesRegex(ValueError, 'incompatible with input data'):
            await self.handlers.connection_add(None, connection)
        self.runtime.configure('history', {'shape': [1]})
        await self.handlers.connection_add(None, connection)
        self.assertEqual(self.runtime.tick(), [])
        history = self.runtime.nodes['history']
        self.assertEqual(history.data.value.shape, (5, 1))
        self.assertEqual(history.data.value[-1, 0], 0.8)
        with self.assertRaisesRegex(ValueError, 'incompatible with input data'):
            self.runtime.configure('history', {'shape': [180]})
        self.assertIs(self.runtime.nodes['history'], history)
        self.assertEqual(self.runtime.tick(), [])

    def test_rgb_history_and_window_functions_keep_all_frame_dimensions(self):
        self.runtime.load({'nodes': [
            {'id': 'color', 'type': 'SingleColor', 'parameters': {'number_points': 4, 'color': [20, 40, 60]}},
            {'id': 'history', 'type': 'Window', 'parameters': {'shape': [4, 3], 'length': 3}},
            {'id': 'average', 'type': 'AveragedWindowFct', 'parameters': {'window': {'nodeId': 'history'}, 'avg_axis': 0}},
            {'id': 'decay', 'type': 'DecreasingAvgWindowFct', 'parameters': {'window': {'nodeId': 'history'}, 'avg_axis': 0}},
        ], 'connections': [{'id': 'input', 'source': {'nodeId': 'color', 'element': 'data'}, 'target': {'nodeId': 'history', 'element': 'input_data'}}]})
        for _ in range(3):
            self.assertEqual(self.runtime.tick(), [])
        self.assertEqual(self.runtime.nodes['history'].data.value.shape, (3, 4, 3))
        for name in ('average', 'decay'):
            np.testing.assert_array_equal(self.runtime.nodes[name].data.value, np.tile([20, 40, 60], (4, 1)))

    def test_resize_reinitializes_history_and_delay_buffer(self):
        self.runtime.load({'nodes': [{'id': 'history', 'type': 'Window', 'parameters': {'shape': [1], 'length': 3, 'offset': 2, 'init_value': 0.25}}], 'connections': []})
        history = self.runtime.nodes['history']
        for value in (1, 2, 3):
            history.input_data.value[:] = value
            self.assertEqual(self.runtime.tick(), [])
        self.assertEqual(history.data.value[-1, 0], 1)
        self.runtime.set_element('history', 'length', 4)
        np.testing.assert_array_equal(history.data.value, np.full((4, 1), 0.25))
        self.assertEqual(history._offset_buffer, [])
        self.runtime.configure('history', {'shape': [2, 3]})
        self.assertEqual(self.runtime.nodes['history'].data.value.shape, (4, 2, 3))
        with self.assertRaises(ValueError):
            self.runtime.configure('history', {'shape': [65536, 65536]})

    def test_saved_template8_cycles_speeds_and_window_shape(self):
        path = Path(__file__).resolve().parents[2] / 'templates' / 'template8.led'
        graph = decode(path.read_bytes())['payload']['graph']
        self.assertEqual([node['parameters']['cycle'] for node in graph['nodes'] if node['type'] == 'Gradiant'], [1, 1])
        self.assertEqual([node['parameters']['roll_speed'] for node in graph['nodes'] if node['type'] == 'RollingNode'], [1, -1])
        self.runtime.load(graph)
        for _ in range(10):
            self.assertEqual(self.runtime.tick(), [])
        self.assertEqual(self.runtime.nodes['avg_frequencies_color_level_window'].data.value.shape, (5, 1))
        self.assertEqual(self.runtime.nodes['avg_frequencies_color_level_window_fct'].data.value.shape, (1,))
