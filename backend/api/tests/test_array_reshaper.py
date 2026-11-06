import unittest

import numpy as np

from backend.api.runtime import Runtime


class ArrayReshaperTests(unittest.TestCase):
    def setUp(self):
        self.runtime = Runtime(preview=True)
        self.addCleanup(self.runtime.close)

    def load(self, **parameters):
        self.runtime.load({'nodes': [{'id': 'reshape', 'type': 'ArrayReshaper', 'parameters': parameters}], 'connections': []})
        return self.runtime.nodes['reshape']

    def test_operation_order_and_live_updates(self):
        source = np.arange(200, dtype=float)
        node = self.load(input_data=source, slice_interval=[0, 150], reshape=[15, 10], transpose=True, reverse=True)
        expected = source[:150].reshape(15, 10).T[::-1]
        np.testing.assert_array_equal(node.data.value, expected)
        self.assertFalse(np.shares_memory(node.data.value, node.input_data.value))
        node.input_data.value[:] += 1
        self.assertEqual(self.runtime.tick(), [])
        np.testing.assert_array_equal(node.data.value, expected + 1)

    def test_axis_selection_and_permutation(self):
        source = np.arange(120).reshape(4, 5, 6)
        node = self.load(input_data=source, slice_interval=[1, 4], slice_axis=-2,
                         transpose=True, transpose_axes=[2, 0, 1], reverse=True, reverse_axis=-1)
        np.testing.assert_array_equal(node.data.value, source[:, 1:4, :].transpose(2, 0, 1)[:, :, ::-1])

    def test_invalid_edits_are_atomic(self):
        node = self.load(input_data=np.arange(200))
        for changes in ({'reshape': [3, 7]}, {'slice_interval': [20, 10]}, {'slice_interval': [0, 1.5]},
                        {'transpose': True, 'transpose_axes': [0, 0]}, {'slice_axis': 1},
                        {'reverse_axis': -2}, {'transpose': True, 'transpose_axes': 0}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                self.runtime.configure('reshape', changes)
            np.testing.assert_array_equal(self.runtime.nodes['reshape'].data.value, np.arange(200))
        node.c_update()

    def test_shape_adapts_on_link_and_placeholder_shape_is_editable(self):
        node = self.load(shape=[12, 3])
        self.assertEqual(node.data.value.shape, (12, 3))
        self.runtime.configure('reshape', {'shape': [4, 9]})
        self.assertEqual(self.runtime.nodes['reshape'].data.value.shape, (4, 9))
        self.runtime.load({'nodes': [
            {'id': 'source', 'type': 'ArrayReshaper', 'parameters': {'input_data': np.arange(600).reshape(200, 3)}},
            {'id': 'reshape', 'type': 'ArrayReshaper', 'parameters': {
                'input_data': {'nodeId': 'source', 'element': 'data'}, 'slice_interval': [0, 150],
            }},
        ], 'connections': []})
        self.assertEqual(self.runtime.nodes['reshape'].shape.value, (200, 3))
        self.assertEqual(self.runtime.nodes['reshape'].data.value.shape, (150, 3))
