"""Compact expression editing keeps legacy graph semantics and live bindings."""
import unittest
import numpy as np
from backend.api.runtime import Runtime


class OperatorExpressionTests(unittest.TestCase):
    def setUp(self):
        self.runtime = Runtime(preview=True)
        self.runtime.load({'nodes': [
            {'id': 'bass', 'type': 'ConstantArray', 'parameters': {'length': 4, 'input_value': .3}},
            {'id': 'highs', 'type': 'ConstantArray', 'parameters': {'length': 4, 'input_value': .6}},
            {'id': 'op', 'type': 'OperatorPipeline', 'parameters': {
                'arguments': ['(', {'nodeId': 'bass', 'element': 'data'}, '+', {'nodeId': 'highs', 'element': 'data'}, ')', '*', .5], 'length': 4}},
        ], 'connections': []})

    def tearDown(self):
        self.runtime.close()

    def test_function_expression_keeps_bindings_and_compiles_once(self):
        self.runtime.configure('op', {'arguments': ['clip(', {'nodeId': 'bass', 'element': 'data'}, '+', {'nodeId': 'highs', 'element': 'data'}, '* .2, 0, 1)'], 'input_names': ['bass', 'highs']})
        op = self.runtime.nodes['op']
        compiled = op.compiled
        self.assertEqual(len(self.runtime.graph['connections']), 2)
        for _ in range(3):
            self.assertEqual(self.runtime.tick(), [])
            np.testing.assert_allclose(op.data.value, np.full(4, .42))
            self.assertIs(op.compiled, compiled)
        self.runtime.nodes['bass'].data.value[:] = .8
        op.c_update()
        np.testing.assert_allclose(op.data.value, np.full(4, .92))

    def test_edit_and_remove_input_reconcile_wires(self):
        self.runtime.configure('op', {'arguments': [{'nodeId': 'highs', 'element': 'data'}, '* 2'], 'input_names': ['highs']})
        self.assertEqual([edge['target']['element'] for edge in self.runtime.graph['connections']], ['highs:data'])
        np.testing.assert_allclose(self.runtime.nodes['op'].data.value, np.full(4, 1.2))
        self.runtime.configure('op', {'arguments': ['2 + 3'], 'input_names': []})
        self.assertEqual(self.runtime.graph['connections'], [])
        np.testing.assert_array_equal(self.runtime.nodes['op'].data.value, [5])

    def test_invalid_syntax_shapes_and_python_access_are_atomic(self):
        original = self.runtime.nodes['op']
        np.testing.assert_allclose(original.data.value, np.full(4, .45))
        for expression in ('1 +', '__import__(1)', '(1).__class__', 'sum([1,2], axis=9)'):
            with self.subTest(expression=expression), self.assertRaises(ValueError):
                self.runtime.configure('op', {'arguments': [expression]})
            self.assertIs(self.runtime.nodes['op'], original)
