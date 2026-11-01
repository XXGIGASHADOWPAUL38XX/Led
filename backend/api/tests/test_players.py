import asyncio
import os
import unittest
from unittest.mock import patch

import numpy as np
from backend.api.runtime import Runtime
from backend.api.handlers import Handlers


class PlayerTests(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        cls.runtime = Runtime()

    async def asyncSetUp(self):
        self.runtime.load({'nodes': [{'id': 'player', 'type': 'SCPlaylistPlayer', 'parameters': {'playlist_url': ''}}], 'connections': []})
        self.node = self.runtime.players['player']
        self.node._entries = [{'url': 'https://soundcloud.com/artist/track'}]
        self.node._tracks = [(np.zeros((40960, 2), dtype=np.float32), 40960)]
        self.node._seek_ratios = [0.0]
        self.messages = []
        async def send(message):
            self.messages.append(message)
        self.session = type('Session', (), {})()
        self.session.send = send
        self.session.search_results = {}
        self.handlers = Handlers(self.runtime, send)

    async def asyncTearDown(self):
        self.runtime.close()

    async def test_play_pause_seek_and_remove(self):
        await self.handlers.player_play(self.session, {'nodeId': 'player', 'trackId': self.node._entries[0]['url']})
        self.assertTrue(self.node._is_playing)
        await self.handlers.player_seek(self.session, {'nodeId': 'player', 'position': 0.5})
        self.assertEqual(self.node._seek_ratios[0], 0.5)
        await self.handlers.player_pause(self.session, {'nodeId': 'player'})
        self.assertFalse(self.node._is_playing)
        track_id = self.node._entries[0]['url']
        await self.handlers.playlist_remove(self.session, {'nodeId': 'player', 'trackId': track_id})
        self.assertEqual(self.node._entries, [])
        self.assertEqual(self.node._current_track_index, -1)

    async def test_search_results_and_add_are_bound_to_the_requesting_session(self):
        result = {'url': 'https://soundcloud.com/artist/new', 'title': 'New', 'uploader': 'Artist', 'duration': 12}
        with patch('backend.nodes.playlist_player.soundcloud.api.search_tracks', return_value=[result]):
            await self.handlers.player_search(self.session, {'nodeId': 'player', 'query': 'new'})
        self.assertEqual(self.messages[-1]['type'], 'player.results')
        with patch.object(self.node, 'add_music') as add:
            await self.handlers.playlist_add(self.session, {'nodeId': 'player', 'trackId': result['url']})
            add.assert_called_once_with(result)
        with self.assertRaises(ValueError):
            await self.handlers.playlist_add(self.session, {'nodeId': 'player', 'trackId': 'untrusted-url'})

    async def test_url_edit_clears_loaded_playlist_before_play(self):
        self.node.on_play_requested(0)
        old_queue = self.node._events
        self.runtime.set_element('player', 'playlist_url', 'https://soundcloud.com/artist/sets/new')
        self.assertEqual(self.node._entries, [])
        self.assertEqual(self.node._current_track_index, -1)
        self.assertFalse(self.node._is_playing)
        self.assertEqual(self.node.audio.value.shape, (0, 2))
        old_queue.put(('playlist', [{'url': 'old-track'}]))
        self.node.c_update()
        self.assertEqual(self.node._entries, [])
        with patch.object(self.node, 'start') as start:
            result = await self.handlers.player_play(self.session, {'nodeId': 'player'})
            start.assert_called_once()
            self.assertEqual(result, {'loading': True})

    async def test_replaced_playlist_ignores_old_worker_finishing_later(self):
        import threading
        started, release = threading.Event(), threading.Event()
        old_url, new_url = 'https://soundcloud.com/a/sets/old', 'https://soundcloud.com/b/sets/new'
        def extract(url, opts):
            if url == old_url:
                started.set()
                release.wait(2)
            return [{'url': url + '/track', 'duration': 12}]
        self.runtime.set_element('player', 'cache', False)
        with patch.object(self.node, '_extract_entries', side_effect=extract) as fetch, patch.object(self.node, '_download_track', return_value=(np.zeros((128, 2)), 40960)):
            self.runtime.set_element('player', 'playlist_url', old_url)
            self.node.start()
            old_worker = self.node._thread
            try:
                self.assertTrue(started.wait(1))
                self.runtime.set_element('player', 'playlist_url', new_url)
                self.node.start()
                self.node._thread.join(1)
                self.assertFalse(self.node._thread.is_alive())
            finally:
                release.set()
                old_worker.join(1)
            self.node.c_update()
            self.assertEqual([entry['url'] for entry in self.node._entries], [new_url + '/track'])
            self.assertEqual([call.args[0] for call in fetch.call_args_list], [old_url, new_url])

    async def test_ready_track_plays_while_the_next_track_downloads(self):
        import threading
        started, release = threading.Event(), threading.Event()
        entries = [{'url': f'https://soundcloud.com/artist/track-{i}', 'duration': 60} for i in (1, 2)]
        def download(entry, *args):
            if entry is entries[1]:
                started.set()
                release.wait(2)
            return np.zeros((40960, 2), dtype=np.float32), 40960
        self.runtime.set_element('player', 'playlist_url', 'https://soundcloud.com/artist/sets/new')
        self.runtime.set_element('player', 'cache', False)
        self.runtime.set_element('player', 'prefetch_seconds', 300)
        with patch.object(self.node, '_extract_entries', return_value=entries), patch.object(self.node, '_download_track', side_effect=download):
            self.node.start()
            try:
                self.assertTrue(started.wait(1))
                self.node.c_update()
                state = self.handlers.player_state(self.node)
                self.assertTrue(state['loading'])
                self.assertEqual([track['downloadState'] for track in state['tracks']], ['ready', 'downloading'])
                self.assertEqual([track['loaded'] for track in state['tracks']], [True, False])
                result = await self.handlers.player_play(self.session, {'nodeId': 'player', 'trackId': entries[0]['url']})
                self.assertTrue(result['playing'])
                self.assertTrue(result['loading'])
                self.assertEqual(result['activeTrackId'], entries[0]['url'])
            finally:
                release.set()
                self.node._thread.join(1)
            self.node.c_update()
            state = self.handlers.player_state(self.node)
            self.assertFalse(state['loading'])
            self.assertEqual([track['downloadState'] for track in state['tracks']], ['ready', 'ready'])

    async def test_default_play_skips_a_track_whose_download_failed(self):
        self.node._entries = [{'url': 'failed', '_download_state': 'failed'}, {'url': 'ready'}]
        self.node._tracks = [None, (np.zeros((40960, 2), dtype=np.float32), 40960)]
        self.node._seek_ratios = [0.0, 0.0]
        result = await self.handlers.player_play(self.session, {'nodeId': 'player'})
        self.assertTrue(result['playing'])
        self.assertEqual(result['activeTrackId'], 'ready')
        self.assertEqual(result['tracks'][0]['downloadState'], 'failed')
