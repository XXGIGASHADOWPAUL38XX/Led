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
