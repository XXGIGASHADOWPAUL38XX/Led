"""Trigger thresholds supplied by scalar-array graph outputs."""
import unittest
import numpy as np

from backend.api.runtime import Runtime


class TriggerThresholdTests(unittest.TestCase):
    def test_linked_threshold_emits_only_on_rising_condition(self):
        runtime = Runtime(preview=True)
        try:
            runtime.load({'nodes': [
                {'id': 'threshold', 'type': 'ConstantArray', 'parameters': {'length': 1, 'input_value': .1}},
                {'id': 'trigger', 'type': 'Trigger', 'parameters': {'input_data': np.array([.2]), 'trigger_mode': 'GREATER',
                    'threshold': {'nodeId': 'threshold', 'element': 'data'}}},
            ], 'connections': []})
            node = runtime.nodes['trigger']
            self.assertEqual(runtime.tick(), [])
            np.testing.assert_array_equal(node.data.value, [1])
            self.assertEqual(runtime.tick(), [])
            np.testing.assert_array_equal(node.data.value, [0])
            runtime.set_element('threshold', 'input_value', .3)
            self.assertEqual(runtime.tick(), [])
            np.testing.assert_array_equal(node.data.value, [0])
            runtime.set_element('threshold', 'input_value', .1)
            self.assertEqual(runtime.tick(), [])
            np.testing.assert_array_equal(node.data.value, [1])
        finally:
            runtime.close()
