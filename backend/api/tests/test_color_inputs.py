"""RGB vectors and individual channels are live inputs, with editable fallbacks."""
import unittest
import numpy as np
from backend.api.handlers import Handlers
from backend.api.protocol import encode, decode
from backend.api.runtime import Runtime


class ColorInputTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.runtime = Runtime()
        async def broadcast(message):
            pass
        self.handlers = Handlers(self.runtime, broadcast)
        self.runtime.load({'nodes': [
            {'id': 'source', 'type': 'ConstantArray', 'parameters': {'input_value': 64, 'length': 1}},
            {'id': 'rgb', 'type': 'ConstantArray', 'parameters': {'input_value': 100, 'length': 3}},
            {'id': 'color', 'type': 'SingleColor', 'parameters': {'color': [20, 40, 60]}},
            {'id': 'gradient', 'type': 'Gradiant', 'parameters': {'color_in': [10, 20, 30], 'color_out': [200, 210, 220], 'cycle': 1}},
        ], 'connections': []})

    def tearDown(self):
        self.runtime.close()

    async def link(self, node, input, source='source'):
        await self.handlers.connection_add(None, {'connectionId': input,
            'source': {'nodeId': source, 'element': 'data'},
            'target': {'nodeId': node, 'element': input}})

    async def test_independent_channels_update_without_metadata_churn(self):
        await self.link('color', 'color_red')
        np.testing.assert_array_equal(self.runtime.nodes['color'].data.value[0], [64, 40, 60])
        self.runtime.set_element('source', 'input_value', 80)
        self.assertEqual(self.runtime.setting_updates(), [])
        np.testing.assert_array_equal(self.runtime.nodes['color'].data.value[0], [80, 40, 60])
        self.runtime.set_element('color', 'color', [10, 80, 90])
        np.testing.assert_array_equal(self.runtime.nodes['color'].data.value[0], [80, 80, 90])
        await self.handlers.connection_remove(None, {'connectionId': 'color_red'})
        np.testing.assert_array_equal(self.runtime.nodes['color'].data.value[0], [10, 80, 90])

    async def test_both_gradient_endpoints_have_live_channel_inputs(self):
        await self.link('gradient', 'color_in_green')
        await self.link('gradient', 'color_out_blue')
        self.runtime.set_element('source', 'input_value', 70)
        gradient = self.runtime.nodes['gradient'].data.value
        np.testing.assert_array_equal(gradient[0], [10, 70, 30])
        np.testing.assert_array_equal(gradient[-1], [200, 210, 70])
        self.runtime.set_element('gradient', 'cycle', 0)
        np.testing.assert_array_equal(self.runtime.nodes['gradient'].data.value, np.tile([10, 70, 30], (180, 1)))

    async def test_whole_rgb_links_channel_overrides_and_roundtrip(self):
        await self.link('color', 'color', 'rgb')
        await self.link('color', 'color_blue')
        await self.link('gradient', 'color_in', 'rgb')
        np.testing.assert_array_equal(self.runtime.nodes['color'].data.value[0], [100, 100, 64])
        self.runtime.set_element('rgb', 'input_value', 80)
        np.testing.assert_array_equal(self.runtime.nodes['color'].data.value[0], [80, 80, 64])
        np.testing.assert_array_equal(self.runtime.nodes['gradient'].data.value[0], [80, 80, 80])
        graph = decode(encode({'type': 'graph', 'payload': {'graph': self.runtime.graph}}))['payload']['graph']
        self.runtime.load(graph, replace=True)
        np.testing.assert_array_equal(self.runtime.nodes['color'].data.value[0], [80, 80, 64])

    async def test_channel_clamping_and_vector_shape_validation(self):
        await self.link('color', 'color_red')
        self.runtime.nodes['source'].data.value[:] = 300
        self.assertEqual(self.runtime.nodes['color'].data.value[0, 0], 255)
        self.runtime.nodes['source'].data.value[:] = -10
        self.assertEqual(self.runtime.nodes['color'].data.value[0, 0], 0)
        with self.assertRaises(ValueError):
            await self.link('gradient', 'color_in_red', 'rgb')
        self.assertEqual(self.runtime.tick(), [])
