import asyncio
from pathlib import Path
import unittest

import msgpack

from backend.api.handlers import Handlers
from backend.api.router import Router
from backend.api.runtime import Runtime
from backend.api.schemas import NodeDescriptor, Snapshot
from backend.api.tests.test_runtime import graph

TEMPLATES = Path(__file__).resolve().parents[2] / 'templates'


class Session:
    def __init__(self):
        self.sent = []

    async def send(self, message):
        self.sent.append(message)


class ContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.runtime = Runtime(preview=True)

    def tearDown(self):
        self.runtime.close()

    def test_saved_template_snapshots_match_the_contract(self):
        for name in ('template4.led', 'template6.led', 'template7.led', 'template8.led'):
            with self.subTest(template=name):
                saved = msgpack.unpackb((TEMPLATES / name).read_bytes(), raw=False)['payload']['graph']
                Snapshot.model_validate(self.runtime.load(saved, replace=True))

    def test_every_catalog_node_describes_itself_within_the_contract(self):
        for node in self.runtime.catalog.prototypes[1:]:
            with self.subTest(node=node.nodeName):
                NodeDescriptor.model_validate(self.runtime.describe(node))


class CommandValidationTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.runtime = Runtime(preview=True)
        self.runtime.load(graph())
        self.broadcasts = []

        async def broadcast(message):
            self.broadcasts.append(message)

        self.router = Router(Handlers(self.runtime, broadcast))
        self.session = Session()

    async def asyncTearDown(self):
        self.runtime.close()

    async def dispatch(self, kind, payload):
        await self.router.dispatch(self.session, {'type': kind, 'requestId': 1, 'payload': payload})
        return self.session.sent[-1]

    async def test_malformed_commands_are_rejected_before_touching_the_graph(self):
        revision = self.runtime.revision
        for kind, payload in [
            ('graph.move', {'positions': {'amp': [float('nan'), 0]}}),
            ('graph.move', {'positions': {'amp': [1, 2, 3]}}),
            ('connection.add', {'source': {'nodeId': 'buffer'}, 'target': {'nodeId': 'amp', 'element': 'buffer'}}),
            ('element.set', {'nodeId': 'amp', 'element': 'powering', 'value': 1, 'typo': True}),
            ('jev.generate', {'prompt': ''}),
            ('node.remove', {}),
        ]:
            with self.subTest(kind=kind, payload=payload):
                reply = await self.dispatch(kind, payload)
                self.assertEqual(reply['type'], 'error')
                self.assertEqual(reply['requestId'], 1)
        self.assertEqual(self.runtime.revision, revision)
        self.assertEqual(self.broadcasts, [])

    async def test_valid_commands_reach_their_handler_with_only_the_fields_sent(self):
        reply = await self.dispatch('node.add', {'nodeType': 'Buffer'})
        self.assertEqual(reply['type'], 'ack')
        self.assertEqual(reply['payload']['result'], {'nodeId': 'Buffer'})
        reply = await self.dispatch('graph.move', {'positions': {'amp': [24, 48]}})
        self.assertEqual(reply['type'], 'ack')
        self.assertEqual(next(node for node in self.runtime.graph['nodes'] if node['id'] == 'amp')['position'], [24, 48])
        reply = await self.dispatch('graph.load', {'graph': {'nodes': [
            {'name': 'buffer', 'class': 'Buffer', 'state': {'ctor_kwargs': {}, 'pos': [0, 0]}}], 'connects': []}})
        self.assertEqual(reply['type'], 'ack')
        self.assertEqual([node['id'] for node in self.runtime.graph['nodes']], ['buffer'])


if __name__ == '__main__':
    unittest.main()
