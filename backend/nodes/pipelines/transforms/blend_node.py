import numpy as np

from backend.components.elements import AnalysableElement
from backend.components.elements.parameters import DataElement, SequenceElement
from backend.overrides.CNode import CNode
from backend.updatable.updatable import AudioUpdatable


class BlendNode(CNode, AudioUpdatable):
    """Blend numeric values or arrays using a normalized weighted average.

    `inputs` contains {source: value, array or Element reference, weight: number}.
    Drop outputs onto add_element to append inputs with weight 1. Shapes must
    be NumPy-broadcast compatible; scalars can blend with arrays. Weights must
    be finite and nonnegative. Output data is sum(source * weight) / sum(weights).
    No inputs or all-zero weights produce zeros. Input storage is never changed.
    """

    nodeName = 'Blend'
    ui = {'title': 'Blend',
     'description': 'Blend values or broadcast-compatible arrays: sum(value × weight) / sum(weights). Drop wires '
                    'to add inputs. Zero total weight outputs zero.',
     'category': 'transforms',
     'fields': [{'name': 'inputs',
                 'control': 'blend',
                 'label': 'Inputs',
                 'rebuild': True,
                 'addPort': 'add_element'}],
     'views': [{'kind': 'bars', 'data': 'data', 'label': 'Blend', 'open': True}]}

    def __init__(self, inputs=None, alias=None):
        super().__init__(self.nodeName, {'add_element': {'io': 'in', 'variadic': True}, 'data': {'io': 'out'}}, alias=alias)
        self.inputs = SequenceElement(self, 'inputs', list(inputs or []), register_in_node=False)
        self.inputs.input_ports = [f'input_{i}' for i in range(len(self.inputs))]
        self.sources = []
        for name, item in zip(self.inputs.input_ports, self.inputs):
            source = DataElement(self, name, np.zeros(1) if item['source'] is None else item['source'])
            vars(self)[name] = source
            self.sources.append(source)
            self.pending_terminals[name] = {'io': 'in'}
        self.add_element = DataElement(self, 'add_element', None, register_in_node=False)
        self.weights = np.asarray([item['weight'] for item in self.inputs], dtype=float)
        self.validate_parameters({})
        total = self.weights.sum()
        self.weights = self.weights / total if total else np.zeros_like(self.weights)
        self.data = AnalysableElement(self, 'data', np.zeros(self.output_shape()))
        self.c_update()

    def output_shape(self):
        return np.broadcast_shapes(*(np.shape(source.value) for source in self.sources)) if self.sources else (1,)

    def validate_parameters(self, changes):
        if self.weights.shape != (len(self.sources),) or not np.isfinite(self.weights).all() or np.any(self.weights < 0) or not np.isfinite(self.weights.sum()):
            raise ValueError('Blend weights must be finite nonnegative numbers with a finite sum')
        for source in self.sources:
            if np.asarray(source.value).dtype.kind not in 'biuf':
                raise ValueError('Blend inputs must be numeric values or arrays')
        self.output_shape()

    def c_update(self):
        self.data.value[...] = 0
        for source, weight in zip(self.sources, self.weights):
            if weight:
                self.data.value[...] += np.asarray(source.value) * weight

    def connect_input(self, name, source, parameters):
        inputs = parameters.setdefault('inputs', [])
        if name == 'add_element':
            name = f'input_{len(inputs)}'
            inputs.append({'source': source, 'weight': 1})
        else:
            inputs[int(name.removeprefix('input_'))]['source'] = source
        return name, {}

    def disconnect_input(self, name, parameters):
        parameters['inputs'][int(name.removeprefix('input_'))]['source'] = None
        return ()

    def configure_graph(self, graph, parameters):
        graph['connections'] = [edge for edge in graph['connections'] if edge['target']['nodeId'] != self.name()]
        for index, item in enumerate(parameters['inputs']):
            source = item['source']
            if type(source) is dict and 'nodeId' in source:
                name = f'input_{index}'
                graph['connections'].append({'id': f'{self.name()}:{name}', 'source': source,
                                             'target': {'nodeId': self.name(), 'element': name}})
