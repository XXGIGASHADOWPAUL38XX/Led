"""Exercise the saved techno graph with deterministic audio, without playback/network."""
from pathlib import Path
from time import perf_counter
import unittest
from unittest.mock import patch

import numpy as np

from backend.api.protocol import decode, encode
from backend.api.runtime import Runtime
from backend.nodes.stream.stream_player_node import StreamPlayerNode

TEMPLATE = Path(__file__).resolve().parents[2] / 'templates' / 'template7.led'
SAMPLE_RATE = 40960
CHUNK = 2048


def techno(seconds=8, bpm=132, hats=True, wide=False, gain=1):
    """Four-on-the-floor pitched kicks, offbeat bass, and seeded stereo hats."""
    t = np.arange(int(seconds * SAMPLE_RATE)) / SAMPLE_RATE
    beat = 60 / bpm
    phase = t % beat
    kick = 0.9 * np.exp(-phase / 0.045) * np.sin(2 * np.pi * (48 * phase + 3.5 * (1 - np.exp(-phase / 0.025))))
    bass = 0.14 * np.sin(2 * np.pi * 55 * t) * (0.3 + 0.7 * (phase > beat / 2))
    rng = np.random.default_rng(7)
    hat_env = np.exp(-((t + beat / 8) % (beat / 4)) / 0.012)
    hat_l = 0.18 * rng.normal(size=t.size) * hat_env if hats else np.zeros_like(t)
    hat_r = 0.18 * rng.normal(size=t.size) * hat_env if hats and wide else hat_l
    return np.column_stack((kick + bass + hat_l, kick + bass + hat_r)) * gain


def simulate(audio):
    runtime = Runtime()
    frames, features, durations = [], [], []
    try:
        runtime.load(decode(TEMPLATE.read_bytes())['payload']['graph'])
        # Only replace the hardware source. The complete saved downstream graph runs normally.
        with patch.object(StreamPlayerNode, 'c_update'):
            for start in range(0, len(audio) - CHUNK + 1, CHUNK):
                runtime.nodes['stream'].chunk.value[:] = audio[start:start + CHUNK].T
                before = perf_counter()
                errors = runtime.tick()
                durations.append(perf_counter() - before)
                if errors:
                    raise AssertionError(errors)
                frames.append(runtime.nodes['lights_rgba'].rgba.value.copy())
                features.append([runtime.nodes['transients'].data.value[0], runtime.nodes['texture'].data.value[0], runtime.nodes['stereo'].mid_ratio.value[0]])
                np.testing.assert_array_equal(runtime.nodes['techno_lights'].data.value, np.ones(180))
        return np.asarray(frames), np.asarray(features), np.asarray(durations)
    finally:
        runtime.close()


class Template7Tests(unittest.TestCase):
    def test_saved_graph_and_output_contract(self):
        template = decode(TEMPLATE.read_bytes())
        graph = template['payload']['graph']
        self.assertEqual(decode(encode(template))['payload']['graph'], graph)
        self.assertEqual(graph['nodes'][0]['type'], 'SCPlaylistPlayer')
        self.assertEqual(graph['nodes'][-1]['type'], 'BarGraphChart')
        self.assertFalse(any('Amplitude' in node['type'] or node['type'] == 'RMS' for node in graph['nodes']))
        frames, _, _ = simulate(techno(seconds=2))
        self.assertEqual(frames.shape, (40, 180, 4))
        self.assertTrue(np.isfinite(frames).all())
        self.assertGreaterEqual(frames.min(), 0)
        self.assertLessEqual(frames.max(), 255)

    def test_silence_and_decay_after_music(self):
        frames, _, _ = simulate(np.vstack((techno(seconds=2), np.zeros((SAMPLE_RATE, 2)))))
        self.assertTrue(np.all(frames[-10:, :, 3] == 0))
        silent, _, _ = simulate(np.zeros((SAMPLE_RATE, 2)))
        self.assertTrue(np.all(silent[:, :, 3] == 0))

    def test_reacts_across_techno_tempos(self):
        for bpm in (120, 132, 150):
            with self.subTest(bpm=bpm):
                frames, _, _ = simulate(techno(bpm=bpm))
                intensity = frames[10:, :, 3].mean(axis=1) / 255
                self.assertGreater(np.ptp(intensity), 0.08)
                self.assertLess(np.mean(frames[10:, :, 3] > 250), 0.1)
                self.assertGreater(np.mean(np.std(frames[10:, :, 3], axis=1)), 10)

    def test_timbre_and_stereo_affect_the_visuals(self):
        dry, _, _ = simulate(techno(hats=False))
        hats, _, _ = simulate(techno())
        wide, _, _ = simulate(techno(wide=True))
        self.assertGreater(np.mean(np.abs(hats[10:, :, :3] - dry[10:, :, :3])), 3)
        self.assertGreater(np.mean(np.abs(wide[10:, :, 3] - hats[10:, :, 3])), 1)

    def test_pulses_follow_the_kick_at_different_tempos(self):
        for bpm in (120, 132, 150):
            with self.subTest(bpm=bpm):
                frames, _, _ = simulate(techno(bpm=bpm, hats=False))
                time = (np.arange(len(frames)) + 0.5) * CHUNK / SAMPLE_RATE
                phase = time % (60 / bpm)
                intensity = frames[:, :, 3].mean(axis=1) / 255
                beat = intensity[(time > 1) & (phase < 0.15)]
                gap = intensity[(time > 1) & (phase > 0.25) & (phase < 60 / bpm - 0.05)]
                self.assertGreater(beat.mean(), gap.mean() * 1.4)

    def test_features_are_independent_of_playback_volume(self):
        loud, _, _ = simulate(techno(seconds=2))
        quiet, _, _ = simulate(techno(seconds=2, gain=0.1))
        np.testing.assert_allclose(loud, quiet, atol=1e-5)


if __name__ == '__main__':
    unittest.main()
