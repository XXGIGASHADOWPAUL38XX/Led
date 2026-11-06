"""Four-band routing and rendering checks for the saved template5 graph."""
from pathlib import Path
import unittest
from unittest.mock import patch

import numpy as np

from backend.api.protocol import decode
from backend.api.runtime import Runtime
from backend.nodes.stream.stream_player_node import StreamPlayerNode

TEMPLATE = Path(__file__).resolve().parents[2] / 'templates' / 'template5.led'


class Template5Tests(unittest.TestCase):
    def setUp(self):
        self.runtime = Runtime()
        self.runtime.load(decode(TEMPLATE.read_bytes())['payload']['graph'])

    def tearDown(self):
        self.runtime.close()

    def feed(self, frequency, amplitude=0.3):
        chunk = self.runtime.nodes['stream'].chunk.value
        time = np.arange(chunk.shape[1]) / 40960
        tone = amplitude * np.sin(2 * np.pi * frequency * time)
        with patch.object(StreamPlayerNode, 'c_update'):
            for _ in range(5):
                chunk[:] = tone
                self.assertEqual(self.runtime.tick(), [])
        rgba = self.runtime.nodes['rgba'].rgba.value
        self.assertEqual(rgba.shape, (180, 4))
        self.assertTrue(np.isfinite(rgba).all())
        self.assertGreaterEqual(rgba.min(), 0)
        self.assertLessEqual(rgba.max(), 255)
        np.testing.assert_array_equal(self.runtime.nodes['lights'].data.value, np.ones(180))
        return rgba.copy()

    def test_requested_node_counts_and_solid_close_colors(self):
        nodes = self.runtime.graph['nodes']
        self.assertEqual(sum(node['type'] in {'LowFilter', 'BandFilter', 'HighFilter'} for node in nodes), 4)
        for kind, count in [('Gradiant', 4), ('Routing', 1), ('Gathering', 1), ('BarGraphChart', 1)]:
            self.assertEqual(sum(node['type'] == kind for node in nodes), count)
        self.assertEqual(nodes[-1]['type'], 'BarGraphChart')
        colors = []
        for node in nodes:
            if node['type'] == 'Gradiant':
                self.assertEqual(node['parameters']['cycle'], 0)
                color = self.runtime.nodes[node['id']].data.value
                np.testing.assert_array_equal(color, np.tile(color[0], (180, 1)))
                colors.append(color[0])
        self.assertLess(np.max(np.ptp(colors, axis=0)), 100)

    def test_each_band_selects_its_gradient(self):
        for index, (frequency, band) in enumerate([(80, 'bass'), (300, 'bass_mid'), (1200, 'mid_high'), (6000, 'high')]):
            with self.subTest(band=band):
                rgba = self.feed(frequency)
                np.testing.assert_array_equal(self.runtime.nodes['routing'].data.value, np.eye(4)[index])
                np.testing.assert_array_equal(rgba[:, :3], self.runtime.nodes[f'{band}_gradient'].data.value)
                self.assertGreater(rgba[:, 3].mean(), 100)

    def test_volume_drives_alpha_and_silence_disables_all_routes(self):
        quiet = self.feed(80, amplitude=0.03)
        loud = self.feed(80, amplitude=0.3)
        self.assertGreater(loud[:, 3].mean(), quiet[:, 3].mean() * 3)
        silent = self.feed(80, amplitude=0)
        self.assertFalse(silent[:, 3].any())
        self.assertFalse(self.runtime.nodes['routing'].data.value.any())

    def test_routing_ties_choose_first_and_multiple_enables_are_deterministic(self):
        routing = self.runtime.nodes['routing']
        for source in routing.inputs:
            source.value = np.array([0.2])
        routing.c_update()
        np.testing.assert_array_equal(routing.data.value, [1, 0, 0, 0])
        gathering = self.runtime.nodes['gathering']
        for enabled in gathering.enable_elements:
            enabled.value = np.ones(1)
        gathering.c_update()
        np.testing.assert_array_equal(gathering.data.value, self.runtime.nodes['bass_gradient'].data.value)
