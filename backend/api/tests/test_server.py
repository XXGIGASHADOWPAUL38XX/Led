import asyncio
import os
import unittest
from copy import deepcopy

import httpx
import uvicorn
from websockets.asyncio.client import connect
from websockets.exceptions import InvalidStatus

from backend.api.runtime import Runtime
from backend.api.server import Server, create_app, uvicorn_options
from backend.api.protocol import encode, decode
from backend.api.tests.test_runtime import graph


async def receive_kind(socket, kind):
    async with asyncio.timeout(3):
        while True:
            message = decode(await socket.recv())
            if message['type'] == kind:
                return message


class ServerTests(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        cls.runtime = Runtime()

    async def asyncSetUp(self):
        self.runtime.load(graph())
        self.service = Server(self.runtime)
        self.server = uvicorn.Server(uvicorn.Config(create_app(self.service), host='127.0.0.1', port=0,
                                                    log_level='warning', **uvicorn_options))
        self.serving = asyncio.create_task(self.server.serve())
        while not self.server.started:
            await asyncio.sleep(0.01)
        port = self.server.servers[0].sockets[0].getsockname()[1]
        self.http = f'http://127.0.0.1:{port}'
        self.url = f'ws://127.0.0.1:{port}/ws'

    async def asyncTearDown(self):
        self.server.should_exit = True
        await self.serving
        self.runtime.close()

    async def test_http_api_reports_health_and_documents_itself_for_local_origins(self):
        async with httpx.AsyncClient(base_url=self.http) as client:
            health = await client.get('/api/v1/health', headers={'Origin': 'http://localhost:3000'})
            self.assertEqual(health.json(), {'status': 'ok', 'revision': self.runtime.revision})
            self.assertEqual(health.headers['access-control-allow-origin'], 'http://localhost:3000')
            foreign = await client.get('/api/v1/health', headers={'Origin': 'https://example.com'})
            self.assertNotIn('access-control-allow-origin', foreign.headers)
            self.assertEqual((await client.get('/docs')).status_code, 200)
            schemas = (await client.get('/openapi.json')).json()['components']['schemas']
            self.assertIn('Snapshot', schemas)

    async def test_websocket_refuses_foreign_origins_and_other_paths(self):
        with self.assertRaises(InvalidStatus):
            async with connect(self.url, origin='https://example.com'):
                pass
        async with connect(self.url, origin='http://127.0.0.1:3000') as socket:
            await receive_kind(socket, 'graph.snapshot')
        with self.assertRaises(InvalidStatus):
            async with connect(self.url.replace('/ws', '/other')):
                pass

    async def test_text_frames_are_rejected_without_closing_the_session(self):
        async with connect(self.url) as socket:
            await receive_kind(socket, 'graph.snapshot')
            await socket.send('{"type": "graph.get"}')
            self.assertIn('binary', (await receive_kind(socket, 'error'))['payload']['message'])
            await socket.send(encode({'type': 'graph.get', 'requestId': 1, 'payload': {}}))
            self.assertEqual((await receive_kind(socket, 'ack'))['requestId'], 1)

    async def test_binary_frames_backpressure_and_reliable_controls(self):
        async with connect(self.url) as slow, connect(self.url) as editor:
            snapshot = await receive_kind(slow, 'graph.snapshot')
            await receive_kind(editor, 'graph.snapshot')
            self.assertEqual(len(snapshot['payload']['graph']['nodes']), 2)
            await slow.send(encode({'type': 'subscribe', 'requestId': 1, 'payload': {'elements': [{'nodeId': 'amp', 'element': 'data'}]}}))
            await receive_kind(slow, 'ack')
            first = await receive_kind(slow, 'frame')
            self.assertEqual(first['payload']['values'][0]['value'].shape, (180,))
            with self.assertRaises(TimeoutError):
                await asyncio.wait_for(slow.recv(), timeout=0.13)
            await editor.send(encode({'type': 'element.set', 'requestId': 2, 'payload': {'nodeId': 'amp', 'element': 'powering', 'value': 0.75}}))
            update = await receive_kind(slow, 'state.update')
            self.assertEqual(update['payload']['value'], 0.75)
            ack = await receive_kind(editor, 'ack')
            self.assertEqual(ack['requestId'], 2)
            await slow.send(encode({'type': 'frame.ack', 'payload': {'sequence': first['payload']['sequence']}}))
            second = await receive_kind(slow, 'frame')
            self.assertGreater(second['payload']['sequence'], first['payload']['sequence'])
            self.assertEqual(second['revision'], update['revision'])

    async def test_graph_commands_and_correlated_errors(self):
        async with connect(self.url) as socket:
            await receive_kind(socket, 'graph.snapshot')
            original = self.runtime.nodes['amp']
            commands = [
                ('node.add', {'nodeId': 'constant', 'nodeType': 'ConstantArray'}),
                ('node.move', {'nodeId': 'constant', 'position': [10, 20]}),
                ('graph.move', {'positions': {'buffer': [24, 24], 'amp': [424, 24]}}),
                ('node.remove', {'nodeId': 'constant'}),
                ('connection.remove', {'connectionId': 'wire'}),
                ('connection.add', {'connectionId': 'wire', 'source': {'nodeId': 'buffer', 'element': 'data'}, 'target': {'nodeId': 'amp', 'element': 'buffer'}}),
            ]
            for request_id, (kind, payload) in enumerate(commands, 1):
                await socket.send(encode({'type': kind, 'requestId': request_id, 'payload': payload}))
                ack = await receive_kind(socket, 'ack')
                self.assertEqual(ack['requestId'], request_id)
                if kind == 'node.add':
                    self.assertIs(self.runtime.nodes['amp'], original)
                if kind == 'graph.move':
                    self.assertIs(self.runtime.nodes['amp'], original)
                    self.assertEqual(next(node['position'] for node in self.runtime.graph['nodes'] if node['id'] == 'amp'), [424, 24])
            await socket.send(encode({'type': 'element.set', 'requestId': 99, 'payload': {'nodeId': 'amp', 'element': 'powering', 'value': 100}}))
            error = await receive_kind(socket, 'error')
            self.assertEqual(error['requestId'], 99)
            self.assertEqual(self.runtime.nodes['amp'].powering.value, 0.5)

    async def test_reconnect_gets_current_snapshot_without_command_replay(self):
        async with connect(self.url) as socket:
            await receive_kind(socket, 'graph.snapshot')
            await socket.send(encode({'type': 'element.set', 'requestId': 1, 'payload': {'nodeId': 'amp', 'element': 'freq_bins', 'value': 256}}))
            await receive_kind(socket, 'ack')
        async with connect(self.url) as socket:
            snapshot = await receive_kind(socket, 'graph.snapshot')
            amp = next(node for node in snapshot['payload']['nodes'] if node['id'] == 'amp')
            bins = next(field for field in amp['elements'] if field['name'] == 'freq_bins')
            self.assertEqual(bins['value'], 256)
            await socket.send(encode({'type': 'graph.get', 'requestId': 2, 'payload': {}}))
            await receive_kind(socket, 'graph.snapshot')
            self.assertEqual((await receive_kind(socket, 'ack'))['requestId'], 2)

    async def test_search_does_not_block_control_commands(self):
        started, release = asyncio.Event(), asyncio.Event()

        async def delayed_search(session, payload):
            started.set()
            await release.wait()
            return {'count': 0}

        self.service.router.routes['player.search'] = delayed_search
        async with connect(self.url) as socket:
            await receive_kind(socket, 'graph.snapshot')
            await socket.send(encode({'type': 'player.search', 'requestId': 1, 'payload': {'nodeId': 'amp', 'query': 'kick'}}))
            await asyncio.wait_for(started.wait(), 3)
            await socket.send(encode({'type': 'element.set', 'requestId': 2, 'payload': {'nodeId': 'amp', 'element': 'powering', 'value': 0.75}}))
            self.assertEqual((await receive_kind(socket, 'ack'))['requestId'], 2)
            release.set()
            self.assertEqual((await receive_kind(socket, 'ack'))['requestId'], 1)

    async def test_python_side_settings_reach_connected_clients(self):
        async with connect(self.url) as socket:
            await receive_kind(socket, 'graph.snapshot')
            self.runtime.nodes['amp'].powering.value = 0.9
            update = await receive_kind(socket, 'state.update')
            self.assertEqual(update['payload']['value'], 0.9)
            self.assertEqual(update['payload']['element'], 'powering')

    async def test_chart_inputs_stream_without_backend_rendering(self):
        self.runtime.load({'nodes': [{'id': 'lights', 'type': 'BarGraphChart', 'parameters': {}}], 'connections': []})
        async with connect(self.url) as socket:
            await receive_kind(socket, 'graph.snapshot')
            await socket.send(encode({'type': 'subscribe', 'requestId': 1, 'payload': {'elements': [
                {'nodeId': 'lights', 'element': 'data'}, {'nodeId': 'lights', 'element': 'brushes'}]}}))
            await receive_kind(socket, 'ack')
            frame = await receive_kind(socket, 'frame')
            values = {item['element']: item['value'] for item in frame['payload']['values']}
            self.assertEqual(values['data'].shape, (180,))
            self.assertEqual(values['brushes'].shape, (180, 4))

    async def test_structural_configuration_updates_schema_and_streams_real_results(self):
        self.runtime.load({'nodes': [
            {'id': 'source', 'type': 'ConstantArray', 'parameters': {'input_value': 0.75}},
            {'id': 'expression', 'type': 'OperatorPipeline', 'parameters': {}},
        ], 'connections': []})
        async with connect(self.url) as socket:
            await receive_kind(socket, 'graph.snapshot')
            await socket.send(encode({'type': 'node.configure', 'requestId': 1, 'payload': {
                'nodeId': 'expression', 'parameters': {
                    'arguments': [{'nodeId': 'source', 'element': 'data'}, '*', 0.5], 'length': 180}}}))
            snapshot = await receive_kind(socket, 'graph.snapshot')
            expression = next(node for node in snapshot['payload']['nodes'] if node['id'] == 'expression')
            self.assertIn('source:data', [port['name'] for port in expression['ports']])
            self.assertEqual((await receive_kind(socket, 'ack'))['requestId'], 1)
            await socket.send(encode({'type': 'subscribe', 'requestId': 2, 'payload': {
                'elements': [{'nodeId': 'expression', 'element': 'data'}]}}))
            await receive_kind(socket, 'ack')
            frame = await receive_kind(socket, 'frame')
            self.assertTrue((frame['payload']['values'][0]['value'] == 0.375).all())

    async def test_save_and_load_template_restores_authoritative_values_and_fresh_instances(self):
        async with connect(self.url) as socket:
            await receive_kind(socket, 'graph.snapshot')
            await socket.send(encode({'type': 'element.set', 'requestId': 1, 'payload': {'nodeId': 'amp', 'element': 'powering', 'value': 0.75}}))
            await receive_kind(socket, 'ack')
            await socket.send(encode({'type': 'graph.get', 'requestId': 2, 'payload': {}}))
            await receive_kind(socket, 'graph.snapshot')
            saved = (await receive_kind(socket, 'ack'))['payload']['result']['graph']
            self.assertEqual(saved['nodes'][1]['parameters']['powering'], 0.75)
            original = self.runtime.nodes['amp']
            await socket.send(encode({'type': 'graph.load', 'requestId': 3, 'payload': {'graph': saved}}))
            await receive_kind(socket, 'graph.snapshot')
            self.assertEqual((await receive_kind(socket, 'ack'))['requestId'], 3)
            self.assertIsNot(self.runtime.nodes['amp'], original)
            self.assertEqual(self.runtime.nodes['amp'].powering.value, 0.75)
            restored = self.runtime.nodes['amp']
            invalid = deepcopy(saved)
            invalid['nodes'][1]['type'] = 'UnknownNode'
            await socket.send(encode({'type': 'graph.load', 'requestId': 4, 'payload': {'graph': invalid}}))
            self.assertEqual((await receive_kind(socket, 'error'))['requestId'], 4)
            self.assertIs(self.runtime.nodes['amp'], restored)
