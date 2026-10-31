"""Clipboard nodes own their parameters and remap copied graph references."""
import unittest
import numpy as np

from backend.api.clipboard import copy_nodes
from backend.api.handlers import Handlers
from backend.api.history import History
from backend.api.runtime import Runtime


class ClipboardTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.runtime = Runtime()
        async def broadcast(_message):
            pass
        self.handlers = Handlers(self.runtime, broadcast)

    def tearDown(self):
        self.runtime.close()

    async def paste(self, copied):
        return await self.handlers.graph_paste(None, {'graph': copied, 'position': [400, 300]})

    async def test_curve_arrays_and_repeated_pastes_are_independent(self):
        self.runtime.load({'nodes': [{'id': 'curve', 'type': 'Function', 'position': [0, 0],
            'parameters': {'points': [[0, .2], [1, .8]], 'point_ids': ['a', 'b']}}], 'connections': []})
        copied = copy_nodes(self.runtime, ['curve'])
        self.runtime.set_element('curve', 'points', [[0, .4], [1, .9]])
        history = History(self.runtime)
        inverse = history.capture('graph.paste', {})
        first, second = await self.paste(copied), await self.paste(copied)
        self.assertEqual(first['nodeIds'], ['curve copy'])
        self.assertEqual(second['nodeIds'], ['curve copy 2'])
        original, clone = self.runtime.nodes['curve'], self.runtime.nodes['curve copy']
        self.assertIsNot(original, clone)
        self.assertFalse(np.shares_memory(original.points.value, clone.points.value))
        np.testing.assert_array_equal(clone.points.value, [[0, .2], [1, .8]])
        self.runtime.set_element('curve copy', 'points', [[0, .1], [1, .3]])
        np.testing.assert_array_equal(original.points.value, [[0, .4], [1, .9]])
        await self.handlers.graph_restore(None, inverse[1])
        self.assertEqual(set(self.runtime.nodes), {'curve'})

    async def test_group_links_and_dynamic_ports_target_the_copies(self):
        reference = {'nodeId': 'Source Node', 'element': 'data'}
        self.runtime.load({'nodes': [
            {'id': 'Source Node', 'type': 'ConstantArray', 'position': [0, 0], 'parameters': {'length': 4, 'input_value': .3}},
            {'id': 'Operator', 'type': 'OperatorPipeline', 'position': [300, 20], 'parameters': {'arguments': [reference, '*', 2]}},
        ], 'connections': [{'id': 'wire', 'source': reference, 'target': {'nodeId': 'Operator', 'element': 'source node:data'}}]})
        await self.paste(copy_nodes(self.runtime, ['Source Node', 'Operator']))
        self.assertEqual(self.runtime.nodes['Operator copy'].arguments.value[0].node.name(), 'Source Node copy')
        self.assertEqual(self.runtime.graph['connections'][-1]['target'], {'nodeId': 'Operator copy', 'element': 'source node copy:data'})
        self.runtime.set_element('Source Node copy', 'input_value', .8)
        self.assertEqual(self.runtime.tick(), [])
        np.testing.assert_allclose(self.runtime.nodes['Operator copy'].data.value, 1.6)
        np.testing.assert_allclose(self.runtime.nodes['Operator'].data.value, .6)

    async def test_external_audio_input_is_captured_without_sharing_a_source(self):
        self.runtime.load({'nodes': [
            {'id': 'source', 'type': 'ConstantArray', 'position': [0, 0], 'parameters': {'length': 4, 'input_value': .4}},
            {'id': 'buffer', 'type': 'Buffer', 'position': [300, 0], 'parameters': {'length': 8}},
        ], 'connections': [{'id': 'wire', 'source': {'nodeId': 'source', 'element': 'data'}, 'target': {'nodeId': 'buffer', 'element': 'indata'}}]})
        copied = copy_nodes(self.runtime, ['buffer'])
        self.runtime.load({'nodes': [], 'connections': []})
        await self.paste(copied)
        buffer = self.runtime.nodes['buffer copy']
        self.assertIsNone(buffer.indata._value_source)
        self.assertEqual(self.runtime.tick(), [])
        np.testing.assert_allclose(buffer.data.value, np.r_[np.zeros(4), np.full(4, .4)])

    async def test_node_object_dependencies_are_cloned(self):
        self.runtime.load({'nodes': [
            {'id': 'source', 'type': 'ConstantArray', 'position': [0, 0], 'parameters': {}},
            {'id': 'group', 'type': 'GroupNode', 'position': [300, 0], 'parameters': {'nodes': [{'nodeId': 'source'}]}},
        ], 'connections': []})
        await self.paste(copy_nodes(self.runtime, ['group']))
        original = self.runtime.nodes['group'].nodes.value[0]
        clone = self.runtime.nodes['group copy'].nodes.value[0]
        self.assertIsNot(original, clone)
        self.assertIs(clone, self.runtime.nodes['source copy'])

    async def test_default_arrays_and_empty_argument_lists_are_owned_by_the_copy(self):
        self.runtime.load({'nodes': [
            {'id': 'rgba', 'type': 'RGBAPipeline', 'position': [0, 0], 'parameters': {}},
            {'id': 'operator', 'type': 'OperatorPipeline', 'position': [300, 0], 'parameters': {}},
        ], 'connections': []})
        await self.paste(copy_nodes(self.runtime, ['rgba', 'operator']))
        self.assertFalse(np.shares_memory(self.runtime.nodes['rgba'].rgb.value, self.runtime.nodes['rgba copy'].rgb.value))
        self.assertIsNot(self.runtime.nodes['operator'].arguments.value, self.runtime.nodes['operator copy'].arguments.value)

    async def test_nested_operator_references_copy_their_own_dependencies(self):
        self.runtime.load({'nodes': [
            {'id': 'source', 'type': 'ConstantArray', 'position': [0, 0], 'parameters': {'length': 4, 'input_value': .4}},
            {'id': 'operator', 'type': 'OperatorPipeline', 'position': [300, 0], 'parameters': {}},
            {'id': 'consumer', 'type': 'OperatorPipeline', 'position': [600, 0], 'parameters': {}},
        ], 'connections': []})
        await self.handlers.connection_add(None, {'source': {'nodeId': 'source', 'element': 'data'}, 'target': {'nodeId': 'operator', 'element': 'add_element'}})
        await self.handlers.connection_add(None, {'source': {'nodeId': 'operator', 'element': 'source:data_out'}, 'target': {'nodeId': 'consumer', 'element': 'add_element'}})
        await self.paste(copy_nodes(self.runtime, ['consumer']))
        self.assertEqual(self.runtime.graph['connections'][-1]['target']['element'], 'operator copy:source copy:data')
        self.runtime.set_element('source', 'input_value', .9)
        self.assertEqual(self.runtime.tick(), [])
        np.testing.assert_allclose(self.runtime.nodes['consumer copy'].data.value, .4)
