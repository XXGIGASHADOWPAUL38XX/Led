import asyncio
import base64
import os
import unittest

import httpx
import numpy as np
from websockets.asyncio.client import connect

from backend.api.protocol import from_json, to_json
from unittest.mock import patch

from backend.api.tests.test_generation import FakeGenerator
from backend.api.tests.test_server import LiveServer, receive_kind


class JsonArrayTests(unittest.TestCase):
    def test_arrays_round_trip_losslessly_through_json(self):
        value = {'curve': np.array([[0.5, -1.25], [3, 4]], dtype='<f8'), 'level': np.float32(0.5), 'items': [np.arange(3, dtype='<i4')]}
        encoded = to_json(value)
        self.assertEqual(encoded['curve'], {'__ndarray__': True, 'dtype': '<f8', 'shape': [2, 2],
                                            'data': base64.b64encode(value['curve'].tobytes()).decode()})
        self.assertEqual(encoded['level'], 0.5)
        decoded = from_json(encoded)
        np.testing.assert_array_equal(decoded['curve'], value['curve'])
        self.assertEqual(decoded['items'][0].dtype, np.dtype('<i4'))

    def test_malformed_arrays_are_refused(self):
        for envelope in [{'__ndarray__': True, 'dtype': '<f8', 'shape': [3], 'data': base64.b64encode(b'1234').decode()},
                         {'__ndarray__': True, 'dtype': 'object', 'shape': [0], 'data': ''},
                         {'__ndarray__': True, 'dtype': '<f8', 'shape': [1], 'data': 'not base64!'}]:
            with self.subTest(envelope=envelope), self.assertRaises(ValueError):
                from_json({'value': envelope})


class RestTests(LiveServer):
    async def asyncSetUp(self):
        await super().asyncSetUp()
        self.client = httpx.AsyncClient(base_url=f'{self.http}/api/v1', headers={'X-Client-Id': 'tab-1'})

    async def asyncTearDown(self):
        await self.client.aclose()
        await super().asyncTearDown()

    async def test_new_nodes_appear_in_catalog_and_recalibration_is_an_http_action(self):
        catalog = (await self.client.get('/catalog')).json()
        definitions = {node['type']: node for node in catalog}
        self.assertTrue({'ArrayReshaper', 'Blend', 'Clustering', 'Correlate', 'CosineAngle', 'DimensionalFlattening'} <= definitions.keys())
        self.assertEqual(definitions['Blend']['fields'][0]['control'], 'blend')
        self.assertEqual(definitions['Clustering']['fields'][0]['control'], 'clustering')
        scatter = next(view for view in definitions['DimensionalFlattening']['views'] if view['kind'] == 'scatter')
        self.assertEqual(scatter['status'], 'calibration')
        created = await self.client.post('/nodes', json={'nodeType': 'DimensionalFlattening', 'nodeId': 'nmf'})
        self.assertEqual(created.status_code, 200)
        node = self.runtime.nodes['nmf']
        node.calibration.value[:] = 1
        response = await self.client.post('/nodes/nmf/recalibrate')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {'nodeId': 'nmf'})
        self.assertEqual(node.calibration.value[1], 0)
        unsupported = await self.client.post('/nodes/amp/recalibrate')
        self.assertEqual(unsupported.status_code, 422)

    async def test_nodes_and_connections_are_resources_and_edits_reach_clients_as_patches(self):
        async with connect(self.url) as socket:
            await receive_kind(socket, 'graph.snapshot')
            added = await self.client.post('/nodes', json={'nodeType': 'ConstantArray', 'position': [10, 20]},
                                           headers={'Origin': 'http://localhost:3000'})
            self.assertEqual(added.status_code, 200)
            self.assertEqual(added.headers['x-revision'], str(self.runtime.revision))
            self.assertIn('x-revision', added.headers['access-control-expose-headers'].lower())
            node_id = added.json()['nodeId']
            message = await receive_kind(socket, 'graph.patch')
            self.assertEqual(str(message['revision']), added.headers['x-revision'])
            patch = message['payload']
            self.assertEqual([node['id'] for node in patch['nodes']], [node_id])
            self.assertEqual([node['id'] for node in patch['descriptors']], [node_id])

            connection = (await self.client.post('/connections', json={
                'source': {'nodeId': node_id, 'element': 'data'}, 'target': {'nodeId': 'amp', 'element': 'buffer'}})).json()
            self.assertEqual(connection['target'], {'nodeId': 'amp', 'element': 'buffer'})
            self.assertEqual((await receive_kind(socket, 'graph.patch'))['payload']['connectionOrder'], [connection['id']])

            moved = await self.client.patch('/graph/positions', json={'positions': {node_id: [5, 6]}})
            self.assertEqual(moved.status_code, 200)
            self.assertEqual((await receive_kind(socket, 'state.update'))['payload']['positions'], {node_id: [5, 6]})

            self.assertEqual((await self.client.delete(f'/connections/{connection["id"]}')).status_code, 200)
            self.assertEqual((await self.client.delete(f'/nodes/{node_id}')).status_code, 200)
            snapshot = (await self.client.get('/graph')).json()
            self.assertEqual([node['id'] for node in snapshot['graph']['nodes']], ['buffer', 'amp'])
            self.assertEqual([node['id'] for node in snapshot['nodes']], ['buffer', 'amp'])

    async def test_refusals_are_http_errors_with_a_message(self):
        unknown = await self.client.delete('/connections/missing')
        self.assertEqual(unknown.status_code, 422)
        self.assertEqual(unknown.json(), {'detail': 'Unknown connection'})
        invalid = await self.client.patch('/graph/positions', json={'positions': {'amp': [1, 2, 3]}})
        self.assertEqual(invalid.status_code, 422)
        self.assertEqual((await self.client.get('/node-types/Nope')).status_code, 422)

    async def test_graph_parameters_with_arrays_survive_a_save_and_load(self):
        graph = (await self.client.get('/graph')).json()['graph']
        graph['nodes'].append({'id': 'const', 'type': 'ConstantArray', 'position': [0, 0],
                               'parameters': {'input_value': 0.25, 'length': 3}})
        self.assertEqual((await self.client.put('/graph', json={'graph': graph})).status_code, 200)
        saved = (await self.client.get('/graph')).json()['graph']
        self.assertEqual((await self.client.put('/graph', json={'graph': saved})).status_code, 200)
        self.assertEqual((await self.client.get('/graph')).json()['graph'], saved)
        envelope = to_json(np.linspace(0, 1, 4))
        loaded = await self.client.put('/graph', json={'graph': {'nodes': [
            {'id': 'points', 'type': 'BarGraphChart', 'parameters': {'data': envelope}}], 'connections': []}})
        self.assertEqual(loaded.status_code, 200, loaded.text)
        self.assertEqual((await self.client.get('/graph')).json()['graph']['nodes'][0]['parameters']['data'], envelope)

    async def test_undo_groups_one_gesture_per_client(self):
        await self.client.post('/nodes', json={'nodeType': 'Buffer'}, headers={'X-History-Group': '4'})
        await self.client.post('/nodes', json={'nodeType': 'ConstantArray'}, headers={'X-History-Group': '5'})
        self.assertEqual((await self.client.post('/graph/undo')).status_code, 200)
        self.assertEqual([node['id'] for node in self.runtime.graph['nodes']], ['buffer', 'amp', 'Buffer'])
        await self.client.post('/graph/undo')
        self.assertEqual([node['id'] for node in self.runtime.graph['nodes']], ['buffer', 'amp'])
        self.assertEqual((await self.client.post('/graph/undo')).json(), {'detail': 'Nothing to undo'})

    async def test_copy_paste_configure_describe_and_streams(self):
        copied = (await self.client.post('/graph/copy', json={'nodeIds': ['amp']})).json()['graph']
        pasted = (await self.client.post('/graph/paste', json={'graph': copied, 'position': [400, 0]})).json()
        self.assertEqual(len(pasted['nodeIds']), 1)
        configured = await self.client.put(f'/nodes/{pasted["nodeIds"][0]}/parameters', json={'parameters': {'freq_bins': 64}})
        self.assertEqual(configured.status_code, 200, configured.text)
        descriptor = (await self.client.get('/node-types/Amplitudes')).json()
        self.assertEqual(descriptor['type'], 'Amplitudes')
        self.assertEqual((await self.client.post('/nodes/amp/start')).json(), {'detail': 'This node has no manual stream lifecycle'})


class PlayerAndGenerationRestTests(LiveServer):
    async def asyncSetUp(self):
        await super().asyncSetUp()
        self.runtime.load({'nodes': [{'id': 'player', 'type': 'SCPlaylistPlayer', 'parameters': {'playlist_url': ''}}],
                           'connections': []})
        node = self.runtime.players['player']
        node._entries = [{'url': 'https://soundcloud.com/artist/track'}]
        node._tracks = [(np.zeros((40960, 2), dtype=np.float32), 40960)]
        node._seek_ratios = [0.0]
        self.client = httpx.AsyncClient(base_url=f'{self.http}/api/v1', headers={'X-Client-Id': 'tab-1'})

    async def asyncTearDown(self):
        await self.client.aclose()
        await super().asyncTearDown()

    async def test_playback_search_and_playlist_are_player_resources(self):
        track = 'https://soundcloud.com/artist/track'
        played = (await self.client.post('/players/player/play', json={'trackId': track})).json()
        self.assertTrue(played['playing'])
        self.assertEqual(played['activeTrackId'], track)
        self.assertEqual((await self.client.post('/players/player/seek', json={'position': 0.5})).status_code, 200)
        self.assertFalse((await self.client.post('/players/player/pause')).json()['playing'])
        found = {'url': 'https://soundcloud.com/artist/new', 'title': 'New', 'uploader': 'Artist', 'duration': 3}
        with patch('backend.nodes.playlist_player.soundcloud.api.search_tracks', return_value=[found]):
            results = (await self.client.get('/players/player/search', params={'query': 'new'})).json()
        self.assertEqual([item['id'] for item in results['tracks']], [found['url']])
        other = await self.client.post('/players/player/playlist', json={'trackId': found['url']},
                                       headers={'X-Client-Id': 'tab-2'})
        self.assertEqual(other.json(), {'detail': 'Choose a track returned by search'})
        with patch.object(self.runtime.players['player'], 'add_music') as add:
            self.assertEqual((await self.client.post('/players/player/playlist', json={'trackId': found['url']})).json(),
                             {'loading': True})
            add.assert_called_once_with(found)
        removed = await self.client.delete('/players/player/playlist', params={'trackId': track})
        self.assertEqual(removed.json()['tracks'], [])
        self.assertEqual((await self.client.post('/players/missing/pause')).status_code, 422)

    async def test_a_generation_is_an_accepted_job_reported_over_the_websocket(self):
        FakeGenerator.release = asyncio.Event()
        with patch('ai.template_generator.agent.Generator', FakeGenerator), patch.dict(os.environ, {'OPENCODE_API_KEY': 'key'}):
            async with connect(self.url) as socket:
                await receive_kind(socket, 'graph.snapshot')
                started = await self.client.post('/generations', json={'prompt': 'pulse'})
                self.assertEqual(started.status_code, 202)
                self.assertEqual(started.json()['status'], 'running')
                self.assertEqual((await self.client.post('/generations', json={'prompt': 'again'})).status_code, 422)
                cancelled = await self.client.delete('/generations/current')
                self.assertEqual(cancelled.json()['status'], 'cancelled')
                while (await receive_kind(socket, 'jev.update'))['payload']['status'] != 'cancelled':
                    pass


if __name__ == '__main__':
    unittest.main()
