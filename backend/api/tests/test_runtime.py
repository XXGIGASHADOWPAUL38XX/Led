import os
import unittest
from copy import deepcopy

from backend.api.runtime import Runtime
from backend.api.protocol import encode, decode


def graph():
    return {'nodes': [
        {'id': 'buffer', 'type': 'Buffer', 'position': [0, 0], 'parameters': {}},
        {'id': 'amp', 'type': 'Amplitudes', 'position': [350, 0], 'parameters': {}},
    ], 'connections': [{'id': 'wire', 'source': {'nodeId': 'buffer', 'element': 'data'}, 'target': {'nodeId': 'amp', 'element': 'buffer'}}]}


class RuntimeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.runtime = Runtime()

    def setUp(self):
        self.runtime.load(graph())

    def tearDown(self):
        self.runtime.close()

    def test_edit_keeps_instances_and_rebuilds_derived_arrays(self):
        amp = self.runtime.nodes['amp']
        self.runtime.set_element('amp', 'freq_bins', 256)
        self.assertIs(self.runtime.nodes['amp'], amp)
        self.assertEqual(amp.data.value.shape, (256,))
        self.assertEqual(amp.frequencies.value.shape, (256,))
        self.assertEqual(self.runtime.tick(), [])
        self.assertEqual(self.runtime.frame([('amp', 'data')])[0]['value'].shape, (256,))

    def test_coupled_changes_and_bad_types_are_rejected_without_mutation(self):
        for node, field, value in [('amp', 'fft_size', 1024), ('amp', 'min_frequency', 6000), ('amp', 'powering', 4), ('amp', 'freq_bins', 1.5), ('amp', 'data', [1]), ('buffer', 'length', 1000)]:
            with self.subTest(field=field):
                with self.assertRaises(ValueError):
                    self.runtime.set_element(node, field, value)
        self.assertEqual(self.runtime.nodes['buffer'].data.value.shape, (2, 2048))
        self.assertEqual(self.runtime.tick(), [])

    def test_failed_graph_transaction_preserves_live_graph(self):
        original = self.runtime.nodes['amp']
        invalid = deepcopy(graph())
        invalid['connections'].append({'id': 'cycle', 'source': {'nodeId': 'amp', 'element': 'data'}, 'target': {'nodeId': 'buffer', 'element': 'indata'}})
        with self.assertRaises(ValueError):
            self.runtime.load(invalid)
        self.assertIs(self.runtime.nodes['amp'], original)
        invalid = {'nodes': [{'id': 'source', 'type': 'ConstantArray', 'parameters': {}}, {'id': 'amp', 'type': 'Amplitudes', 'parameters': {}}],
                   'connections': [{'id': 'bad', 'source': {'nodeId': 'source', 'element': 'data'}, 'target': {'nodeId': 'amp', 'element': 'buffer'}}]}
        with self.assertRaises(ValueError):
            self.runtime.load(invalid)

    def test_empty_graph_is_valid(self):
        self.runtime.load({'nodes': [], 'connections': []})
        self.assertEqual(self.runtime.nodes, {})

    def test_broadcast_inputs_follow_the_node_contract_instead_of_default_array_rank(self):
        self.runtime.load({'nodes': [
            {'id': 'red', 'type': 'SingleColor', 'parameters': {'color': [255, 0, 0]}},
            {'id': 'blue', 'type': 'SingleColor', 'parameters': {'color': [0, 0, 255]}},
            {'id': 'level', 'type': 'ConstantArray', 'parameters': {'input_value': 0.5}},
            {'id': 'blend', 'type': 'BroadcastAddition', 'parameters': {}},
        ], 'connections': [
            {'id': 'red-input', 'source': {'nodeId': 'red', 'element': 'data'}, 'target': {'nodeId': 'blend', 'element': 'input_data'}},
            {'id': 'blue-input', 'source': {'nodeId': 'blue', 'element': 'data'}, 'target': {'nodeId': 'blend', 'element': 'secondary_data'}},
            {'id': 'level-input', 'source': {'nodeId': 'level', 'element': 'data'}, 'target': {'nodeId': 'blend', 'element': 'level'}},
        ]})
        self.assertEqual(self.runtime.tick(), [])
        value = self.runtime.nodes['blend'].data.value
        self.assertEqual(value.shape, (180, 3))
        self.assertEqual(value[0].tolist(), [127, 0, 127])

    def test_unrelated_edits_preserve_processing_instances(self):
        original = self.runtime.nodes['amp']
        changed = deepcopy(self.runtime.graph)
        changed['nodes'].append({'id': 'extra', 'type': 'ConstantArray', 'position': [0,0], 'parameters': {}})
        self.runtime.load(changed)
        self.assertIs(self.runtime.nodes['amp'], original)
        self.assertEqual(self.runtime.tick(), [])

    def test_reference_selector_accepts_and_clears_an_output(self):
        self.runtime.load({'nodes': [
            {'id': 'source', 'type': 'ConstantArray', 'parameters': {}},
            {'id': 'chart', 'type': 'SingleLineChart', 'parameters': {}},
        ], 'connections': []})
        result = self.runtime.set_element('chart', 'input_data', {'nodeId': 'source', 'element': 'data'})
        message = decode(encode({'type': 'ack', 'payload': result}))
        self.assertEqual(message['payload']['value'], {'nodeId': 'source', 'element': 'data'})
        self.assertIs(self.runtime.nodes['chart'].input_data._value_source, self.runtime.nodes['source'].data)
        self.runtime.set_element('chart', 'input_data', None)
        self.assertIsNone(self.runtime.nodes['chart'].input_data._value_source)

    def test_python_side_control_changes_are_published(self):
        self.runtime.nodes['amp'].powering.value = 0.9
        updates = self.runtime.setting_updates()
        self.assertEqual(len(updates), 1)
        self.assertEqual(updates[0]['value'], 0.9)
        self.assertEqual(updates[0]['element'], 'powering')
        self.assertEqual(self.runtime.setting_updates(), [])
