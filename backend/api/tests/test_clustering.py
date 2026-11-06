import unittest
import numpy as np

from backend.api.handlers import Handlers
from backend.api.protocol import decode, encode
from backend.api.runtime import Runtime


class ClusteringTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.runtime = Runtime(preview=True)
        async def broadcast(_message):
            pass
        self.handlers = Handlers(self.runtime, broadcast)
        self.runtime.load({'nodes': [
            {'id': 'a', 'type': 'ConstantArray', 'parameters': {'length': 1, 'input_value': .25}},
            {'id': 'b', 'type': 'ConstantArray', 'parameters': {'length': 1, 'input_value': 5}},
            {'id': 'cluster', 'type': 'Clustering', 'parameters': {}},
        ], 'connections': []})

    def tearDown(self):
        self.runtime.close()

    async def test_drop_edit_remove_and_roundtrip_preserve_scalar_references(self):
        for source in ('a', 'b'):
            await self.handlers.connection_add(None, {'source': {'nodeId': source, 'element': 'data'},
                                                       'target': {'nodeId': 'cluster', 'element': 'add_element'}})
        self.runtime.configure('cluster', {'inputs': [
            {'source': {'nodeId': 'a', 'element': 'data'}, 'interval': [0, 1]},
            {'source': {'nodeId': 'b', 'element': 'data'}, 'interval': [10, 0]},
        ]})
        self.assertEqual(self.runtime.tick(), [])
        np.testing.assert_allclose(self.runtime.nodes['cluster'].data.value, [[.25, .25], [5, .5]])
        saved = decode(encode({'type': 'template', 'payload': {'graph': self.runtime.graph}}))['payload']['graph']
        self.runtime.load(saved, replace=True)
        edge = next(e for e in self.runtime.graph['connections'] if e['target'] == {'nodeId': 'cluster', 'element': 'input_0'})
        await self.handlers.connection_remove(None, {'connectionId': edge['id']})
        self.assertEqual(self.runtime.tick(), [])
        np.testing.assert_allclose(self.runtime.nodes['cluster'].data.value, [[0, 0], [5, .5]])
        self.runtime.configure('cluster', {'inputs': [{'source': {'nodeId': 'b', 'element': 'data'}, 'interval': [0, 10]}]})
        self.assertEqual(self.runtime.tick(), [])
        np.testing.assert_allclose(self.runtime.nodes['cluster'].data.value, [[5, .5]])
        self.assertEqual([e['source']['nodeId'] for e in self.runtime.graph['connections']], ['b'])

    def test_invalid_intervals_and_vector_sources_are_rejected_atomically(self):
        node = self.runtime.nodes['cluster']
        for interval in ([1, 1], [0, float('inf')]):
            with self.assertRaisesRegex(ValueError, 'interval'):
                self.runtime.configure('cluster', {'inputs': [{'source': None, 'interval': interval}]})
            self.assertIs(self.runtime.nodes['cluster'], node)
        self.runtime.configure('a', {'length': 3})
        with self.assertRaisesRegex(ValueError, 'one finite numeric value'):
            self.runtime.configure('cluster', {'inputs': [{'source': {'nodeId': 'a', 'element': 'data'}, 'interval': [0, 1]}]})
