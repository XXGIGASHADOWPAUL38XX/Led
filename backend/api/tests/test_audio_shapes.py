"""Shape adaptation, explicit edits, DSP, and saved audio graphs."""
import unittest
import numpy as np
from scipy.signal import butter, lfilter

from backend.api.handlers import Handlers
from backend.api.protocol import decode, encode
from backend.api.runtime import Runtime


class AudioShapeTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.runtime = Runtime()
        async def broadcast(_message):
            pass
        self.handlers = Handlers(self.runtime, broadcast)

    def tearDown(self):
        self.runtime.close()

    async def link(self, source, output, target, input_name):
        await self.handlers.connection_add(None, {'source': {'nodeId': source, 'element': output},
                                                'target': {'nodeId': target, 'element': input_name}})

    async def test_stereo_chain_adopts_shapes_and_filters_actual_samples(self):
        self.runtime.load({'nodes': [
            {'id': 'stream', 'type': 'StreamPlayer', 'parameters': {'chunk_size': 335}},
            {'id': 'buffer', 'type': 'Buffer', 'parameters': {'length': 512}},
            *[{'id': kind, 'type': kind, 'parameters': {}} for kind in ('LowFilter', 'BandFilter', 'HighFilter')],
        ], 'connections': []})
        await self.link('stream', 'chunk', 'buffer', 'indata')
        source = 'buffer'
        for kind in ('LowFilter', 'BandFilter', 'HighFilter'):
            await self.link(source, 'data', kind, 'buffer_data')
            self.assertEqual(self.runtime.nodes[kind].shape.value, (2, 512))
            source = kind
        stream = self.runtime.nodes['stream']
        stream.chunk.value[:] = np.sin(np.arange(670).reshape(2, 335) * .1)
        self.assertEqual(self.runtime.tick(), [])
        expected = np.pad(stream.chunk.value, ((0, 0), (177, 0)))
        np.testing.assert_array_equal(self.runtime.nodes['buffer'].data.value, expected)
        for kind, cutoff, btype in [('LowFilter', 1000, 'lowpass'), ('BandFilter', [500, 3000], 'bandpass'), ('HighFilter', 20, 'highpass')]:
            coefficients = butter(1, cutoff, fs=40960, btype=btype)
            expected = lfilter(*coefficients, expected)
            np.testing.assert_allclose(self.runtime.nodes[kind].data.value, expected)
        self.assertEqual(self.runtime.nodes['buffer'].shape.value, (2, 335))
        restored = decode(encode({'type': 'graph', 'payload': {'graph': self.runtime.graph}}))['payload']['graph']
        self.runtime.load(restored, replace=True)
        self.assertEqual(self.runtime.tick(), [])
        self.assertEqual(self.runtime.nodes['HighFilter'].data.value.shape, (2, 512))

    async def test_mono_link_resize_relink_and_incompatible_edits(self):
        self.runtime.load({'nodes': [
            {'id': 'source', 'type': 'ConstantArray', 'parameters': {'length': 37, 'input_value': 1}},
            {'id': 'buffer', 'type': 'Buffer', 'parameters': {'length': 64}},
            *[{'id': kind, 'type': kind, 'parameters': {}} for kind in ('LowFilter', 'BandFilter', 'HighFilter')],
        ], 'connections': []})
        await self.link('source', 'data', 'buffer', 'indata')
        for kind in ('LowFilter', 'BandFilter', 'HighFilter'):
            await self.link('buffer', 'data', kind, 'buffer_data')
            original = self.runtime.nodes[kind]
            with self.assertRaisesRegex(ValueError, 'incompatible with input data'):
                self.runtime.configure(kind, {'shape': [2, 64]})
            self.assertIs(self.runtime.nodes[kind], original)
            self.assertEqual(original.shape.value, (64,))
        self.assertEqual(self.runtime.tick(), [])
        np.testing.assert_array_equal(self.runtime.nodes['buffer'].data.value, np.r_[np.zeros(27), np.ones(37)])
        original = self.runtime.nodes['buffer']
        with self.assertRaisesRegex(ValueError, 'incompatible with input data'):
            self.runtime.configure('buffer', {'shape': [2, 37]})
        self.assertIs(self.runtime.nodes['buffer'], original)
        edge = next(edge for edge in self.runtime.graph['connections'] if edge['target']['nodeId'] == 'buffer')
        await self.handlers.connection_remove(None, {'connectionId': edge['id']})
        self.runtime.configure('buffer', {'shape': [17]})
        self.assertEqual(self.runtime.nodes['buffer'].indata.value.shape, (17,))
        self.assertEqual(self.runtime.nodes['buffer'].data.value.shape, (64,))
        await self.link('source', 'data', 'buffer', 'indata')
        self.assertEqual(self.runtime.nodes['buffer'].shape.value, (37,))

    def test_unlinked_shapes_resize_and_reject_excessive_allocations(self):
        for kind in ('Buffer', 'LowFilter', 'BandFilter', 'HighFilter'):
            with self.subTest(node=kind):
                self.runtime.load({'nodes': [{'id': 'node', 'type': kind, 'parameters': {}}], 'connections': []})
                self.runtime.set_element('node', 'shape', [3, 17])
                node = self.runtime.nodes['node']
                expected = (3, 2048) if kind == 'Buffer' else (3, 17)
                self.assertEqual(node.data.value.shape, expected)
                descriptor = self.runtime.describe(node)
                self.assertTrue(next(port for port in descriptor['ports'] if port['direction'] == 'in')['adaptiveShape'])
                with self.assertRaises(ValueError):
                    self.runtime.configure('node', {'shape': [65536, 65536]})
                self.assertIs(self.runtime.nodes['node'], node)
                self.assertEqual(self.runtime.tick(), [])

    async def test_amplitudes_adopts_mono_shape_and_matches_numpy_fft(self):
        self.runtime.load({'nodes': [
            {'id': 'source', 'type': 'ConstantArray', 'parameters': {'length': 128}},
            {'id': 'amp', 'type': 'Amplitudes', 'parameters': {'freq_bins': 24}},
        ], 'connections': []})
        await self.link('source', 'data', 'amp', 'buffer')
        amp = self.runtime.nodes['amp']
        self.assertEqual(amp.shape.value, (128,))
        self.assertEqual(amp.fft_size.value, 128)
        samples = np.sin(np.arange(128) * 2 * np.pi * 1000 / 40960)
        self.runtime.nodes['source'].data.value[:] = samples
        amp.c_update()
        magnitude = np.abs(np.fft.rfft(samples * amp.window))
        spectrum = np.interp(amp.frequencies.value, np.fft.rfftfreq(128, 1 / 40960), magnitude)
        expected = 20 * np.log10(1 + np.maximum(spectrum * amp.frequencies.value ** .5 / amp.window.sum(), 1e-12))
        np.testing.assert_allclose(amp.data.value, expected)
        with self.assertRaisesRegex(ValueError, 'incompatible with input data'):
            self.runtime.configure('amp', {'shape': [2, 128]})
        edge = self.runtime.graph['connections'][0]
        await self.handlers.connection_remove(None, {'connectionId': edge['id']})
        self.runtime.configure('amp', {'shape': [3, 256]})
        amp = self.runtime.nodes['amp']
        self.assertEqual(amp.buffer.value.shape, (3, 256))
        self.assertEqual(amp.window.shape, (256,))
        self.assertEqual(amp.data.value.shape, (24,))
        self.assertEqual(self.runtime.tick(), [])
