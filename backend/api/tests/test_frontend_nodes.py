import json
from pathlib import Path
import unittest

import numpy as np

from backend.api.protocol import encode
from backend.api.runtime import Runtime
from backend.components.elements.element import Element
from backend.updatable.updatable import Updatable


class FrontendNodeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.runtime = Runtime()

    def tearDown(self):
        self.runtime.close()

    def test_every_registered_node_and_parameter_has_an_explicit_ui(self):
        directory = Path(__file__).resolve().parents[3] / 'frontend/src/components/node'
        definitions = {}
        for path in directory.rglob('*-node.ts'):
            source = path.read_text()
            if 'satisfies NodeDefinition' in source:
                definition = json.loads(source.split('export default ', 1)[1].rsplit(' satisfies NodeDefinition;', 1)[0])
                self.assertNotIn(definition['type'], definitions)
                definitions[definition['type']] = definition
        self.assertEqual(set(definitions), set(self.runtime.catalog.classes))
        for node in self.runtime.catalog.prototypes[1:]:
            with self.subTest(node=node.nodeName):
                definition = definitions[node.nodeName]
                parameters = {name for name, _ in self.runtime._parameters(node)}
                self.assertEqual(parameters, {field['name'] for field in definition['fields']})
                self.assertEqual(parameters, {field['name'] for field in self.runtime.describe(node)['elements']})
                outputs = {name for name, options in node.pending_terminals.items()
                           if options['io'] == 'out' and isinstance(vars(node).get(node.terminal_element_name(name)), Element)}
                self.assertTrue(outputs.issubset({view.get('data') for view in definition['views']}))
                encode(self.runtime.describe(node))

    def test_nonzero_values_propagate_through_processing_nodes(self):
        self.runtime.load({'nodes': [
            {'id': 'source', 'type': 'ConstantArray', 'parameters': {'input_value': 0.75, 'length': 180}},
            {'id': 'clip', 'type': 'Clip', 'parameters': {'max_value': 0.5}},
            {'id': 'entropy', 'type': 'Entropy', 'parameters': {}},
        ], 'connections': [
            {'id': 'first', 'source': {'nodeId': 'source', 'element': 'data'}, 'target': {'nodeId': 'clip', 'element': 'input_value'}},
            {'id': 'second', 'source': {'nodeId': 'clip', 'element': 'data'}, 'target': {'nodeId': 'entropy', 'element': 'amplitudes'}},
        ]})
        self.assertEqual(self.runtime.tick(), [])
        np.testing.assert_allclose(self.runtime.nodes['clip'].data.value, 0.5)
        self.assertAlmostEqual(self.runtime.nodes['entropy'].data.value[0], 1, places=6)
        for key in ('clip', 'entropy'):
            self.assertEqual(self.runtime.updates.count(self.runtime.nodes[key]), 1)

    def test_expression_configuration_rebuilds_dynamic_ports_and_computes(self):
        self.runtime.load({'nodes': [
            {'id': 'source', 'type': 'ConstantArray', 'parameters': {'input_value': 0.75}},
            {'id': 'expression', 'type': 'OperatorPipeline', 'parameters': {}},
        ], 'connections': []})
        source = self.runtime.nodes['source']
        self.runtime.configure('expression', {'arguments': [{'nodeId': 'source', 'element': 'data'}, '*', 0.5], 'length': 180})
        self.assertIs(self.runtime.nodes['source'], source)
        self.assertEqual(self.runtime.tick(), [])
        np.testing.assert_allclose(self.runtime.nodes['expression'].data.value, 0.375)
        descriptor = self.runtime.describe(self.runtime.nodes['expression'])
        arguments = next(field for field in descriptor['elements'] if field['name'] == 'arguments')
        self.assertEqual(arguments['value'][0], {'nodeId': 'source', 'element': 'data'})
        original = self.runtime.nodes['expression']
        with self.assertRaises(ValueError):
            self.runtime.configure('expression', {'arguments': [{'nodeId': 'expression', 'element': 'data'}]})
        self.assertIs(self.runtime.nodes['expression'], original)

    def test_typed_axes_references_and_dynamic_outputs_are_serializable(self):
        self.runtime.load({'nodes': [
            {'id': 'window', 'type': 'Window', 'parameters': {'input_data': [1, 2], 'length': 3}},
            {'id': 'average', 'type': 'AveragedWindowFct', 'parameters': {'window': {'nodeId': 'window', 'element': 'data'}, 'avg_axis': [0]}},
            {'id': 'stems', 'type': 'StemsRecognition', 'parameters': {}},
        ], 'connections': []})
        self.assertEqual(self.runtime.nodes['average'].avg_axis.value, (0,))
        self.assertEqual(self.runtime.tick(), [])
        self.runtime.nodes['stems']._add_stem_output()
        updates = self.runtime.schema_updates()
        stems = next(item for item in updates if item['nodeId'] == 'stems')
        self.assertIn('stem_1', [port['name'] for port in stems['node']['ports']])
        self.assertEqual(self.runtime.schema_updates(), [])
        encode(self.runtime.snapshot())

    def test_group_references_do_not_own_or_close_other_nodes(self):
        self.runtime.load({'nodes': [
            {'id': 'source', 'type': 'ConstantArray', 'parameters': {}},
            {'id': 'group', 'type': 'GroupNode', 'parameters': {'nodes': [{'nodeId': 'source'}]}},
        ], 'connections': []})
        source = self.runtime.nodes['source']
        self.runtime.load({'nodes': [self.runtime.graph['nodes'][0]], 'connections': []})
        self.assertIs(self.runtime.nodes['source'], source)
        self.runtime.set_element('source', 'input_value', 0.5)
        np.testing.assert_allclose(source.data.value, 0.5)

    def test_node_function_reference_and_curve_edits_drive_numpy(self):
        self.runtime.load({'nodes': [
            {'id': 'function', 'type': 'AmplitudeLevelFunction', 'parameters': {'number_points': 180, 'rise_center': 135}},
            {'id': 'source', 'type': 'ConstantArray', 'parameters': {'input_value': 1}},
            {'id': 'transform', 'type': 'FctAmplitudesTransformer', 'parameters': {}},
            {'id': 'curve', 'type': 'Function', 'parameters': {}},
        ], 'connections': [
            {'id': 'wire', 'source': {'nodeId': 'source', 'element': 'data'}, 'target': {'nodeId': 'transform', 'element': 'input_data'}},
        ]})
        self.runtime.configure('transform', {'amplitudes_level_fct': {'nodeId': 'function'}})
        self.assertEqual(self.runtime.tick(), [])
        self.assertTrue(np.any(self.runtime.nodes['transform'].data.value > 0))
        reference = next(field for field in self.runtime.describe(self.runtime.nodes['transform'])['elements'] if field['name'] == 'amplitudes_level_fct')
        self.assertEqual(reference['value'], {'nodeId': 'function'})
        self.runtime.configure('curve', {'points': [[0, 0], [0.5, 1], [1, 1]]})
        self.assertEqual(self.runtime.nodes['curve'].points.value.shape, (3, 2))
        self.assertGreater(self.runtime.nodes['curve'].data.value[90], 0.99)

    def test_amplitude_curve_is_visible_without_a_caller_and_stays_independent(self):
        self.runtime.load({'nodes': [
            {'id': 'curve', 'type': 'AmplitudeLevelFunction', 'parameters': {'number_points': 180, 'rise_center': 135}},
        ], 'connections': []})
        curve = self.runtime.nodes['curve']
        initial = self.runtime.frame([('curve', 'data')])[0]['value'].copy()
        self.assertGreater(initial.max(), 0)
        self.assertGreater(np.ptp(initial), 0.1)
        self.runtime.set_element('curve', 'offset', 1.0)
        np.testing.assert_allclose(curve.data.value, initial + 0.15)
        expected = curve.data.value.copy()
        self.runtime.load({'nodes': [*self.runtime.graph['nodes'],
            {'id': 'transform', 'type': 'FctAmplitudesTransformer', 'parameters': {
                'input_data': np.full(180, 0.5), 'log': 2,
                'amplitudes_level_fct': {'nodeId': 'curve'},
            }},
        ], 'connections': []})
        self.assertEqual(self.runtime.tick(), [])
        np.testing.assert_allclose(self.runtime.nodes['transform'].data.value, (expected * 0.5) ** 2)
        np.testing.assert_array_equal(curve.data.value, expected)
        self.runtime.load({'nodes': [self.runtime.graph['nodes'][0]], 'connections': []})
        self.runtime.configure('curve', {'number_points': 300, 'rise_center': 225})
        frame = self.runtime.frame([('curve', 'data')])[0]['value']
        self.assertEqual(frame.shape, (300,))
        self.assertTrue(np.isfinite(frame).all())

    def test_all_default_nodes_can_be_added_before_connections(self):
        for name in self.runtime.catalog.classes:
            if name in {'ESP32', 'SCPlaylistPlayer'}:
                continue
            with self.subTest(node=name):
                self.runtime.load({'nodes': [{'id': name, 'type': name, 'parameters': {}}], 'connections': []})
                self.assertEqual(self.runtime.tick(), [])
                if isinstance(self.runtime.nodes[name], Updatable):
                    self.assertIn(self.runtime.nodes[name], self.runtime.updates)
