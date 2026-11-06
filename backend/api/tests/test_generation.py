import asyncio
import os
import unittest
from unittest.mock import patch

from backend.api.handlers import Handlers
from backend.api.router import Router
from backend.api.runtime import Runtime
from backend.api.tests.test_runtime import graph
from backend.api.tests.test_schemas import Session


def generated(current):
    """Jev returns the whole graph: here the current one plus a new buffer."""
    return {'nodes': [*current['nodes'], {'id': f"extra-{len(current['nodes'])}", 'type': 'Buffer', 'position': [0, 0], 'parameters': {}}],
            'connections': current['connections']}


class FakeGenerator:
    """Stands in for Jev: reports progress, publishes one preview, then waits for `release`."""
    release = None

    def __init__(self, catalog):
        pass

    async def generate(self, prompt, current, report, preview, mode):
        await report('running', f'{mode}: {prompt}')
        await FakeGenerator.release.wait()
        return generated(current)


class GenerationTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.runtime = Runtime(preview=True)
        self.runtime.load(graph())
        self.events = []

        async def broadcast(message):
            self.events.append(message)

        self.router = Router(Handlers(self.runtime, broadcast))
        self.session = Session()
        FakeGenerator.release = asyncio.Event()
        patcher = patch('ai.template_generator.agent.Generator', FakeGenerator)
        patcher.start()
        self.addCleanup(patcher.stop)
        environment = patch.dict(os.environ, {'OPENCODE_API_KEY': 'key'})
        environment.start()
        self.addCleanup(environment.stop)

    async def asyncTearDown(self):
        await self.router.generation.cancel()
        self.runtime.close()

    async def send(self, kind, payload):
        await self.router.dispatch(self.session, {'type': kind, 'requestId': 1, 'payload': payload})
        return self.session.sent[-1]

    def statuses(self):
        return [event['payload']['status'] for event in self.events if event['type'] == 'jev.update']

    async def finish(self):
        FakeGenerator.release.set()
        await self.router.generation.task

    async def test_a_generated_graph_replaces_the_current_one_and_is_undoable(self):
        reply = await self.send('jev.generate', {'prompt': '  pulse on kicks  '})
        self.assertEqual(reply['payload']['result']['status'], 'running')
        await self.finish()
        self.assertEqual([node['id'] for node in self.runtime.graph['nodes']], ['buffer', 'amp', 'extra-2'])
        self.assertEqual(self.router.generation.state['status'], 'complete')
        self.assertIn({'type': 'history.update', 'requestId': None, 'revision': self.runtime.revision,
                       'payload': {'canUndo': True}}, self.events)
        await self.send('graph.undo', {})
        self.assertEqual([node['id'] for node in self.runtime.graph['nodes']], ['buffer', 'amp'])

    async def test_edit_mode_keeps_running_nodes_and_generate_mode_rebuilds_them(self):
        amp = self.runtime.nodes['amp']
        await self.send('jev.generate', {'prompt': 'add a buffer', 'mode': 'edit'})
        await self.finish()
        self.assertIs(self.runtime.nodes['amp'], amp)
        FakeGenerator.release = asyncio.Event()
        await self.send('jev.generate', {'prompt': 'start over'})
        await self.finish()
        self.assertIsNot(self.runtime.nodes['amp'], amp)

    async def test_one_generation_at_a_time_and_blank_prompts_or_missing_keys_are_refused(self):
        await self.send('jev.generate', {'prompt': 'first'})
        self.assertEqual((await self.send('jev.generate', {'prompt': 'second'}))['type'], 'error')
        await self.finish()
        self.assertEqual((await self.send('jev.generate', {'prompt': '   '}))['type'], 'error')
        with patch.dict(os.environ, {'OPENCODE_API_KEY': ''}):
            self.assertEqual((await self.send('jev.generate', {'prompt': 'third'}))['type'], 'error')

    async def test_an_edit_during_generation_keeps_the_user_graph(self):
        await self.send('jev.generate', {'prompt': 'pulse'})
        await self.send('node.remove', {'nodeId': 'amp'})
        await self.finish()
        self.assertEqual([node['id'] for node in self.runtime.graph['nodes']], ['buffer'])
        self.assertEqual(self.router.generation.state['status'], 'error')
        self.assertIn('graph changed', self.router.generation.state['message'])

    async def test_cancel_stops_the_job_and_reports_it(self):
        await self.send('jev.generate', {'prompt': 'pulse'})
        await asyncio.sleep(0)
        reply = await self.send('jev.cancel', {})
        self.assertEqual(reply['payload']['result']['status'], 'cancelled')
        self.assertEqual(self.statuses()[-1], 'cancelled')
        self.assertEqual([node['id'] for node in self.runtime.graph['nodes']], ['buffer', 'amp'])


if __name__ == '__main__':
    unittest.main()
