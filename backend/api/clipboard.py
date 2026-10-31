"""Independent graph copies with remapped IDs and dynamic terminal names."""
from copy import deepcopy
import inspect
import re

import numpy as np

from backend.components.elements.parameters import DataElement, ReferenceElement, SequenceElement
from backend.components.elements.node_selector.node_selector import NodeSelector


def copy_nodes(runtime, node_ids):
    selected = set(node_ids)
    if not selected or selected - runtime.nodes.keys():
        raise ValueError('Select existing nodes to copy')
    specs = {node['id']: node for node in runtime.graph['nodes']}
    settings = {}
    for node_id, spec in specs.items():
        parameters = dict(spec['parameters'])
        defaults = inspect.signature(type(runtime.nodes[node_id])).parameters
        for name, element in runtime._parameters(runtime.nodes[node_id]):
            if isinstance(element, ReferenceElement):
                continue
            if element._value_source is not None:
                parameters[name] = runtime._describe_value(element._value_source)
            elif isinstance(element, DataElement) and defaults[name].default is None and spec['parameters'].get(name) is None:
                parameters[name] = None
            else:
                parameters[name] = runtime._describe_value(element.value)
        settings[node_id] = parameters
    # Object references need independent dependencies; signal inputs can be frozen.
    pending = list(selected)
    while pending:
        node_id = pending.pop()
        parameters = settings[node_id]
        for name, element in runtime._parameters(runtime.nodes[node_id]):
            if isinstance(element, (ReferenceElement, SequenceElement, NodeSelector)):
                for source in runtime._references(parameters.get(name)):
                    if source not in selected:
                        selected.add(source)
                        pending.append(source)

    def detach(value):
        if type(value) is dict:
            if set(value) == {'nodeId', 'element'} and value['nodeId'] not in selected:
                return detach(runtime.element(value['nodeId'], value['element']).value)
            return {key: detach(item) for key, item in value.items()}
        if type(value) in (list, tuple):
            return [detach(item) for item in value]
        return np.array(value, copy=True) if isinstance(value, np.ndarray) else deepcopy(value)

    nodes = []
    for spec in runtime.graph['nodes']:
        if spec['id'] not in selected:
            continue
        node = {**spec, 'position': spec['position'][:], 'parameters': detach(settings[spec['id']])}
        fields = dict(runtime._parameters(runtime.nodes[spec['id']]))
        for edge in runtime.graph['connections']:
            target, source = edge['target'], edge['source']
            if target['nodeId'] == spec['id'] and source['nodeId'] not in selected:
                if target['element'] in fields:
                    node['parameters'][target['element']] = detach(runtime.element(source['nodeId'], source['element']).value)
        nodes.append(node)
    return {'nodes': nodes, 'connections': deepcopy([edge for edge in runtime.graph['connections']
            if edge['source']['nodeId'] in selected and edge['target']['nodeId'] in selected])}


def paste_nodes(graph, existing_ids, position):
    graph = deepcopy(graph)
    if not graph['nodes']:
        raise ValueError('Clipboard has no nodes')
    names, occupied = {}, set(existing_ids)
    for node in graph['nodes']:
        base, suffix = f"{node['id']} copy", 2
        name = base
        while name in occupied:
            name = f'{base} {suffix}'
            suffix += 1
        occupied.add(name)
        names[node['id']] = name
    lower = {old.lower(): new.lower() for old, new in names.items()}
    pattern = re.compile(r'(?:^|(?<=:))(' + '|'.join(re.escape(name) for name in sorted(lower, key=len, reverse=True)) + r'):')

    def port(name):
        return pattern.sub(lambda match: lower[match[1]] + ':', name)

    def remap(value):
        if type(value) is dict:
            if set(value) in ({'nodeId'}, {'nodeId', 'element'}):
                return {'nodeId': names[value['nodeId']], **({'element': port(value['element'])} if 'element' in value else {})}
            return {key: remap(item) for key, item in value.items()}
        if type(value) in (list, tuple):
            return [remap(item) for item in value]
        return value

    origin = [min(node['position'][axis] for node in graph['nodes']) for axis in (0, 1)]
    for node in graph['nodes']:
        node['id'] = names[node['id']]
        node['position'] = [node['position'][axis] - origin[axis] + position[axis] for axis in (0, 1)]
        node['parameters'] = remap(node['parameters'])
    for edge in graph['connections']:
        edge['id'] = f"{edge['id']}:{next(iter(names.values()))}"
        for end in ('source', 'target'):
            edge[end] = remap(edge[end])
    return graph, names
