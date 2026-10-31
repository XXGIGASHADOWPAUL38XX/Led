"""Dropping a source onto Operator's append input creates an argument and wire."""
import unittest
import numpy as np
from backend.api.handlers import Handlers
from backend.api.history import History
from backend.api.runtime import Runtime


class OperatorDropTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.runtime = Runtime()
        async def broadcast(_message):
            pass
        self.handlers = Handlers(self.runtime, broadcast)
        self.runtime.load({'nodes': [
            {'id': 'source', 'type': 'ConstantArray', 'parameters': {'length': 4, 'input_value': .3}},
            {'id': 'other', 'type': 'ConstantArray', 'parameters': {'length': 4, 'input_value': .6}},
            {'id': 'operator', 'type': 'OperatorPipeline', 'parameters': {}},
        ], 'connections': []})

    def tearDown(self):
        self.runtime.close()

    async def drop(self, source):
        return await self.handlers.connection_add(None, {'source': {'nodeId': source, 'element': 'data'},
                                                        'target': {'nodeId': 'operator', 'element': 'add_element'}})

    async def test_append_preserves_source_references_and_visible_connections(self):
        history = History(self.runtime)
        inverse = history.capture('connection.add', {})
        first = await self.drop('source')
        second = await self.drop('other')
        parameters = self.runtime.graph['nodes'][-1]['parameters']
        self.assertEqual(parameters['arguments'], [{'nodeId': 'source', 'element': 'data'}, '+', {'nodeId': 'other', 'element': 'data'}])
        self.assertEqual(first['target']['element'], 'source:data')
        self.assertEqual(second['target']['element'], 'other:data')
        self.assertEqual(len(self.runtime.graph['connections']), 2)
        self.assertEqual(self.runtime.tick(), [])
        np.testing.assert_allclose(self.runtime.nodes['operator'].data.value, np.full(4, .9))
        await self.handlers.graph_restore(None, inverse[1])
        self.assertEqual(self.runtime.nodes['operator'].arguments.value, [])
        self.assertEqual(self.runtime.graph['connections'], [])

    async def test_invalid_expression_is_rejected_without_changing_the_graph(self):
        with self.assertRaisesRegex(ValueError, 'Invalid expression'):
            self.runtime.configure('operator', {'arguments': [2, '*']})
        self.assertEqual(self.runtime.nodes['operator'].arguments.value, [])
        await self.drop('source')
        np.testing.assert_allclose(self.runtime.nodes['operator'].data.value, np.full(4, .3))

    async def test_passthrough_reference_keeps_the_selected_node_and_port(self):
        await self.drop('source')
        await self.handlers.node_add(None, {'nodeType': 'OperatorPipeline', 'nodeId': 'consumer'})
        reference = {'nodeId': 'operator', 'element': 'source:data_out'}
        await self.handlers.connection_add(None, {'source': reference, 'target': {'nodeId': 'consumer', 'element': 'add_element'}})
        descriptor = self.runtime.describe(self.runtime.nodes['consumer'])
        arguments = next(element for element in descriptor['elements'] if element['name'] == 'arguments')
        self.assertEqual(arguments['value'], [reference])
        self.assertEqual(self.runtime.tick(), [])
        np.testing.assert_allclose(self.runtime.nodes['consumer'].data.value, np.full(4, .3))
