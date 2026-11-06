import subprocess
import sys
import unittest
from threading import Thread
from pathlib import Path

import numpy as np

from backend.api.runtime import Runtime
from backend.nodes.simple.constant_array import ConstantArrayNode
from backend.nodes.visual.single_line_chart import SingleLineChartNode
from backend.nodes.visual.multi_line_chart import MultiLineChartNode


class HeadlessTests(unittest.TestCase):
    def test_worker_notifications_are_applied_on_the_processing_thread(self):
        runtime = Runtime()
        try:
            runtime.load({'nodes': [{'id': 'source', 'type': 'ConstantArray',
                          'parameters': {'length': 1}}], 'connections': []})
            node = runtime.nodes['source']
            def change_values():
                node.input_value.value = 0.5
                node.input_value.value = 0.75
            worker = Thread(target=change_values)
            worker.start()
            worker.join()
            self.assertEqual(node.data.value[0], 0)
            self.assertEqual(runtime.tick(), [])
            self.assertEqual(node.data.value[0], 0.75)
            self.assertEqual(runtime.setting_updates()[0]['value'], 0.75)
        finally:
            runtime.close()

    def test_runtime_works_when_gui_imports_are_blocked(self):
        program = '''
import importlib.abc
import sys
class NoGUI(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path, target=None):
        if fullname.split('.')[0] in {'PyQt5', 'pyqtgraph', 'pyqt_switch'}:
            raise AssertionError(f'GUI dependency imported: {fullname}')
sys.meta_path.insert(0, NoGUI())
from backend.api.runtime import Runtime
from backend.api.tests.test_runtime import graph
runtime = Runtime()
runtime.load(graph())
runtime.set_element('amp', 'powering', 0.75)
assert runtime.tick() == []
assert runtime.frame([('amp', 'data')])[0]['value'].shape == (180,)
runtime.close()
'''
        subprocess.run([sys.executable, '-c', program], cwd=Path(__file__).resolve().parents[3],
                       check=True, capture_output=True, text=True, timeout=20)

    def test_histories_sample_sources_resize_and_disconnect(self):
        source = ConstantArrayNode(input_value=0.75, length=1)
        single = SingleLineChartNode(input_data=source.data, number_points=4)
        multi = MultiLineChartNode(node_selectors=[source.data, source.data], number_points=4)
        try:
            single.c_update()
            multi.c_update()
            np.testing.assert_array_equal(single.data.value, [0, 0, 0, 0.75])
            np.testing.assert_array_equal(multi.data.value[:, -1], [0.75, 0.75])
            single.number_points.value = 8
            single.parameters_changed('number_points')
            self.assertEqual(single.data.value.shape, (8,))
            single.input_data.set_default_element(None)
            source.input_value.value = 1
            single.c_update()
            self.assertEqual(single.data.value[-1], 0)
        finally:
            single.close()
            multi.close()
            source.close()

    def test_playlist_worker_results_wait_for_processing_tick(self):
        runtime = Runtime()
        try:
            runtime.load({'nodes': [{'id': 'player', 'type': 'SCPlaylistPlayer',
                          'parameters': {'playlist_url': ''}}], 'connections': []})
            node = runtime.players['player']
            entry = {'url': 'https://soundcloud.com/artist/test'}
            track = (np.zeros((128, 2), dtype=np.float32), 44100)
            node._events.put(('add', (entry, track)))
            self.assertEqual(node._entries, [])
            self.assertEqual(runtime.tick(), [])
            self.assertEqual(node._entries, [entry])
            self.assertIs(node._tracks[0], track)
            node._events.put(('track', (entry, track)))
            node.remove_music(0)
            self.assertEqual(runtime.tick(), [])
            self.assertEqual(node._entries, [])
        finally:
            runtime.close()
