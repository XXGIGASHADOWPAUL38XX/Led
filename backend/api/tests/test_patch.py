import unittest
from copy import deepcopy

from backend.api.patch import diff
from backend.api.protocol import encode


def apply(snapshot, patch):
    """What a client does with graph.patch: rebuild each list from the id order, preferring the sent items."""
    def merge(items, upserts, order):
        known = {item['id']: item for item in items} | {item['id']: item for item in upserts}
        return [known[item_id] for item_id in order]

    graph = {'nodes': merge(snapshot['graph']['nodes'], patch['nodes'], patch['nodeOrder']),
             'connections': merge(snapshot['graph']['connections'], patch['connections'], patch['connectionOrder'])}
    return {'graph': graph, 'nodes': merge(snapshot['nodes'], patch['descriptors'], patch['nodeOrder'])}


def node(node_id, value=0):
    return {'id': node_id, 'type': 'Buffer', 'position': [0, 0], 'parameters': {'length': value}}


def descriptor(node_id, value=0):
    return {'id': node_id, 'type': 'Buffer', 'elements': [{'name': 'length', 'value': value}], 'ports': []}


def wire(wire_id, source, target):
    return {'id': wire_id, 'source': {'nodeId': source, 'element': 'data'}, 'target': {'nodeId': target, 'element': 'indata'}}


def snapshot(nodes, wires):
    return {'graph': {'nodes': [node(*item) for item in nodes], 'connections': wires},
            'nodes': [descriptor(*item) for item in nodes]}


class PatchTests(unittest.TestCase):
    def check(self, before, after):
        patch = diff(before, after, 7)
        self.assertEqual(patch['base'], 7)
        self.assertEqual(encode(apply(deepcopy(before), patch)), encode(after))
        return patch

    def test_unchanged_items_stay_out_of_the_patch(self):
        before = snapshot([('a',), ('b',)], [wire('w', 'a', 'b')])
        after = snapshot([('a',), ('b', 4), ('c',)], [wire('w', 'a', 'b')])
        patch = self.check(before, after)
        self.assertEqual([item['id'] for item in patch['nodes']], ['b', 'c'])
        self.assertEqual([item['id'] for item in patch['descriptors']], ['b', 'c'])
        self.assertEqual(patch['connections'], [])

    def test_removals_and_rewired_connections(self):
        before = snapshot([('a',), ('b',), ('c',)], [wire('w1', 'a', 'b'), wire('w2', 'b', 'c')])
        after = snapshot([('a',), ('c',)], [wire('w3', 'a', 'c')])
        patch = self.check(before, after)
        self.assertEqual(patch['nodeOrder'], ['a', 'c'])
        self.assertEqual(patch['connectionOrder'], ['w3'])
        self.assertEqual([item['id'] for item in patch['connections']], ['w3'])

    def test_a_descriptor_change_alone_is_sent(self):
        before = snapshot([('a',)], [])
        after = deepcopy(before)
        after['nodes'][0]['ports'] = [{'name': 'data', 'direction': 'out', 'shape': [4]}]
        patch = self.check(before, after)
        self.assertEqual(patch['nodes'], [])
        self.assertEqual([item['id'] for item in patch['descriptors']], ['a'])

    def test_a_reconnected_wire_moves_to_the_end_as_on_the_server(self):
        before = snapshot([('a',), ('b',)], [wire('w', 'a', 'b'), wire('x', 'b', 'a')])
        after = deepcopy(before)
        moved = after['graph']['connections'].pop(0)
        moved['target']['element'] = 'other'
        after['graph']['connections'].append(moved)
        patch = self.check(before, after)
        self.assertEqual([item['id'] for item in patch['connections']], ['w'])
        self.assertEqual(patch['connectionOrder'], ['x', 'w'])


if __name__ == '__main__':
    unittest.main()
