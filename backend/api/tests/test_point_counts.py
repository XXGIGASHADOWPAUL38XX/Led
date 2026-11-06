"""Editable point counts, non-default signal chains, and source validation."""
import unittest
from backend.api.schemas import parse_command
import numpy as np

from backend.api.runtime import Runtime
from backend.api.handlers import Handlers
from backend.api.protocol import encode, decode


class PointCountTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.runtime = Runtime(preview=True)
        async def broadcast(_message):
            pass
        self.handlers = Handlers(self.runtime, broadcast)

    def tearDown(self):
        self.runtime.close()

    def test_point_controls_resize_generators_and_placeholders(self):
        nodes = {
            'LinearAmplitudesTransformer': ('number_points', 'data'),
            'FctAmplitudesTransformer': ('number_points', 'data'),
            'FreqScaledAmplitudesTransformer': ('number_points', 'data'),
            'RGBAPipeline': ('number_points', 'rgba'),
            'SlidingAmpGradientNode': ('number_points', 'data'),
            'Rainbow': ('n_points', 'data'),
            'Function': ('number_points', 'data'),
            'Gradiant': ('n_points', 'data'),
            'SingleColor': ('number_points', 'data'),
            'SinArray': ('number_points', 'data'),
            'AmplitudeLevelFunction': ('number_points', 'data'),
            'ConstantArray': ('length', 'data'),
            'OutboundsFct': ('length', 'data'),
            'BroadcastRescalerNode': ('length', 'data'),
        }
        for kind, (field, output) in nodes.items():
            with self.subTest(node=kind):
                self.runtime.load({'nodes': [{'id': 'node', 'type': kind, 'parameters': {}}], 'connections': []})
                descriptor = self.runtime.describe(self.runtime.nodes['node'])
                self.assertFalse(next(item for item in descriptor['elements'] if item['name'] == field)['disabled'])
                for count in (1, 178, 257):
                    self.runtime.configure('node', {field: count})
                    self.runtime.nodes['node'].c_update()
                    self.assertEqual(self.runtime.element('node', output).value.shape[0], count)
                    self.assertTrue(np.isfinite(self.runtime.element('node', output).value).all())

    async def test_linking_adopts_count_and_rejects_incompatible_edits(self):
        self.runtime.load({'nodes': [
            {'id': 'source', 'type': 'ConstantArray', 'parameters': {'length': 178, 'input_value': .25}},
            *[{'id': kind, 'type': kind, 'parameters': {}} for kind in ('LinearAmplitudesTransformer', 'FctAmplitudesTransformer', 'FreqScaledAmplitudesTransformer')],
        ], 'connections': []})
        for kind in ('LinearAmplitudesTransformer', 'FctAmplitudesTransformer', 'FreqScaledAmplitudesTransformer'):
            await self.handlers.connection_add(None, parse_command('connection.add', {'source': {'nodeId': 'source', 'element': 'data'}, 'target': {'nodeId': kind, 'element': 'input_data'}}))
            node = self.runtime.nodes[kind]
            self.assertEqual(node.number_points.value, 178)
            self.assertEqual(node.data.value.shape, (178,))
            with self.assertRaisesRegex(ValueError, 'must match 257 points'):
                self.runtime.configure(kind, {'number_points': 257})
            self.assertIs(self.runtime.nodes[kind], node)
        self.runtime.nodes['LinearAmplitudesTransformer'].c_update()
        np.testing.assert_allclose(self.runtime.nodes['LinearAmplitudesTransformer'].data.value, .25)

    async def test_rgba_and_chart_adopt_178_points_and_roundtrip(self):
        self.runtime.load({'nodes': [
            {'id': 'color', 'type': 'SingleColor', 'parameters': {'number_points': 178, 'color': [10, 80, 250]}},
            {'id': 'alpha', 'type': 'ConstantArray', 'parameters': {'length': 178, 'input_value': .5}},
            {'id': 'rgba', 'type': 'RGBAPipeline', 'parameters': {}},
            {'id': 'lights', 'type': 'BarGraphChart', 'parameters': {}},
        ], 'connections': []})
        for source, output, target, field in [('color', 'data', 'rgba', 'rgb'), ('alpha', 'data', 'rgba', 'alpha'), ('rgba', 'rgba', 'lights', 'brushes')]:
            await self.handlers.connection_add(None, parse_command('connection.add', {'source': {'nodeId': source, 'element': output}, 'target': {'nodeId': target, 'element': field}}))
        self.assertEqual(self.runtime.tick(), [])
        np.testing.assert_allclose(self.runtime.nodes['lights'].brushes.value, np.tile([10, 80, 250, 127.5], (178, 1)))
        self.assertEqual(self.runtime.nodes['lights'].data.value.shape, (178,))
        restored = decode(encode({'type': 'graph', 'payload': {'graph': self.runtime.graph}}))['payload']['graph']
        self.runtime.load(restored, replace=True)
        self.assertEqual(self.runtime.tick(), [])
        self.assertEqual(self.runtime.nodes['rgba'].rgba.value.shape, (178, 4))

    def test_linear_correlation_preserves_short_signal_length(self):
        self.runtime.load({'nodes': [{'id': 'linear', 'type': 'LinearAmplitudesTransformer', 'parameters': {
            'input_data': np.ones(3), 'number_points': 3, 'correlation_offset': .8, 'correlation_step': .01,
        }}], 'connections': []})
        self.assertEqual(self.runtime.tick(), [])
        self.assertEqual(self.runtime.nodes['linear'].data.value.shape, (3,))

    def test_function_count_overrides_linked_shape_and_rainbow_resizes(self):
        self.runtime.load({'nodes': [
            {'id': 'source', 'type': 'ConstantArray', 'parameters': {'length': 178}},
            {'id': 'curve', 'type': 'Function', 'parameters': {'input_data': {'nodeId': 'source', 'element': 'data'}}},
            {'id': 'rainbow', 'type': 'Rainbow', 'parameters': {}},
        ], 'connections': []})
        self.assertEqual(self.runtime.nodes['curve'].data.value.shape, (178,))
        self.runtime.set_element('curve', 'number_points', 257)
        self.assertEqual(self.runtime.nodes['curve'].data.value.shape, (257,))
        self.runtime.set_element('rainbow', 'n_points', 257)
        self.assertEqual(self.runtime.nodes['rainbow'].data.value.shape, (257, 3))

    def test_controller_accepts_nondefault_rgba_count(self):
        self.runtime.load({'nodes': [{'id': 'leds', 'type': 'ESP32', 'parameters': {
            'rgba': np.tile([10., 80., 250., 255.], (178, 1)), 'power_log': 1, 'min_alpha': 0,
            'remove_alpha': 0, 'led_count': 298,
        }}], 'connections': []})
        frame = self.runtime.nodes['leds']._get_rgb_frame()
        pixels = np.frombuffer(frame, dtype=np.uint8).reshape(-1, 3)
        self.assertEqual(pixels.shape, (298, 3))
        np.testing.assert_array_equal(pixels[:120], np.zeros((120, 3)))
        np.testing.assert_array_equal(pixels[120:], np.tile([10, 80, 250], (178, 1)))


    def test_correlation_step_is_a_fraction_of_bin_count(self):
        for count in (180, 360):
            with self.subTest(count=count):
                impulse = np.zeros(count)
                center = count // 2
                impulse[center] = 1
                self.runtime.load({'nodes': [{'id': 'linear', 'type': 'LinearAmplitudesTransformer', 'parameters': {
                    'input_data': impulse, 'correlation_offset': 1, 'correlation_step': .1,
                }}], 'connections': []})
                self.assertEqual(self.runtime.tick(), [])
                result = self.runtime.nodes['linear'].data.value
                distances = np.arange(count) - center
                expected = np.maximum(1 - np.abs(distances) / (.1 * count / 2), 0)
                np.testing.assert_allclose(result, expected, atol=1e-12)
                self.assertEqual(int(np.argmax(result)), center)
                self.assertEqual(result[center + int(.1 * count / 2)], 0)

    def test_correlation_sample_count_is_stable_at_floating_point_boundaries(self):
        for step in (np.nextafter(.1, 0), .1, np.nextafter(.1, 1)):
            impulse = np.zeros(180)
            impulse[90] = 1
            self.runtime.load({'nodes': [{'id': 'linear', 'type': 'LinearAmplitudesTransformer', 'parameters': {
                'input_data': impulse, 'correlation_offset': 1, 'correlation_step': float(step),
            }}], 'connections': []})
            self.assertEqual(self.runtime.tick(), [])
            result = self.runtime.nodes['linear'].data.value
            self.assertEqual(np.count_nonzero(result > 1e-12), 17)
            np.testing.assert_allclose(result[81:100], result[81:100][::-1], atol=1e-12)

    def test_overlapping_peaks_keep_the_maximum_contribution(self):
        signal = np.zeros(180)
        signal[[80, 88]] = 1
        self.runtime.load({'nodes': [{'id': 'linear', 'type': 'LinearAmplitudesTransformer', 'parameters': {
            'input_data': signal, 'correlation_offset': 1, 'correlation_step': .1,
        }}], 'connections': []})
        self.assertEqual(self.runtime.tick(), [])
        result = self.runtime.nodes['linear'].data.value
        self.assertAlmostEqual(result[84], 1 - 4 / 9)
        self.assertEqual(result.max(), 1)
        self.runtime.set_element('linear correlation', 'correlation_offset', .5)
        self.assertEqual(self.runtime.tick(), [])
        result = self.runtime.nodes['linear'].data.value
        self.assertAlmostEqual(result[84], .5 * (1 - 4 / 9))
        self.assertAlmostEqual(result[80], 1)

    def test_linear_exponent_does_not_modify_its_source(self):
        self.runtime.load({'nodes': [{'id': 'linear', 'type': 'LinearAmplitudesTransformer', 'parameters': {
            'input_data': np.array([.2, .5, .8]), 'log': .5,
        }}], 'connections': []})
        node = self.runtime.nodes['linear']
        self.assertNotIn('correlation_step', node.pending_terminals)
        for _ in range(3):
            node.c_update()
            np.testing.assert_allclose(node.data.value, np.sqrt([.2, .5, .8]))
            np.testing.assert_array_equal(node.input_data.value, [.2, .5, .8])

    def test_correlate_controls_are_numeric_with_neutral_defaults(self):
        self.runtime.load({'nodes': [{'id': 'correlate', 'type': 'Correlate', 'parameters': {
            'input_data': np.array([.2, .5, .8]),
        }}], 'connections': []})
        node = self.runtime.nodes['correlate']
        fields = {field['name']: field for field in self.runtime.describe(node)['elements']}
        for name in ('correlation_offset', 'correlation_step'):
            self.assertFalse(fields[name]['optional'])
            self.assertEqual(fields[name]['value'], 1. if name == 'correlation_offset' else 0.)
        for _ in range(3):
            node.c_update()
            np.testing.assert_allclose(node.data.value, [.2, .5, .8])
            np.testing.assert_array_equal(node.input_data.value, [.2, .5, .8])

    def test_zero_values_still_apply_a_symmetric_correlation(self):
        for offset, step, expected in [(0, 1, [1, 2, 3, 4, 5]), (.4, 0, [1, 2, 3, 4, 5]), (0, 0, [1, 2, 3, 4, 5])]:
            with self.subTest(offset=offset, step=step):
                self.runtime.load({'nodes': [{'id': 'linear', 'type': 'LinearAmplitudesTransformer', 'parameters': {
                    'input_data': np.arange(1., 6.), 'correlation_offset': offset, 'correlation_step': step,
                }}], 'connections': []})
                self.assertEqual(self.runtime.tick(), [])
                np.testing.assert_allclose(self.runtime.nodes['linear'].data.value, expected)

    def test_legacy_disabled_correlation_loads_as_neutral_numeric_values(self):
        self.runtime.load({'nodes': [{'id': 'linear', 'type': 'LinearAmplitudesTransformer', 'parameters': {
            'input_data': np.array([.2, .5, .8]), 'correlation_offset': None, 'correlation_step': .01,
        }}], 'connections': []})
        self.assertEqual(self.runtime.tick(), [])
        node = self.runtime.nodes['linear correlation']
        self.assertEqual(node.correlation_offset.value, 1.)
        self.assertEqual(node.correlation_step.value, 0.)
        np.testing.assert_allclose(node.data.value, [.2, .5, .8])
