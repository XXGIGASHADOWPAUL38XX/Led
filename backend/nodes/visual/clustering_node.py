import numpy as np

from backend.components.elements import AnalysableElement
from backend.components.elements.parameters import DataElement, SequenceElement
from backend.overrides.CNode import CNode
from backend.updatable.updatable import AudioUpdatable


class ClusteringNode(CNode, AudioUpdatable):
    """Display linked scalar parameters on crossing horizontal/vertical axes.

    `inputs` is an ordered list of {source: Element or None, interval: [start,
    end]}. Each source must provide one numeric value in shape (1,). Each
    interval must have distinct finite endpoints; reversed ranges are allowed.
    `add_element` appends a source with interval [0, 1]. Output `data` has
    shape (input count, 2): raw value and normalized position clamped to [0, 1].
    The frontend draws a centered grid with one line and live dot per input,
    alternating horizontal, vertical, horizontal in input order.
    """

    nodeName = 'Clustering'
    ui = {'title': 'Clustering',
     'description': 'Track scalar parameters on crossing horizontal and vertical grid lines, each with its own '
                    'interval.',
     'category': 'visual',
     'fields': [{'name': 'inputs',
                 'control': 'clustering',
                 'label': 'Parameters',
                 'rebuild': True,
                 'addPort': 'add_element'}],
     'views': [{'kind': 'clustering', 'data': 'data', 'label': 'Clustering', 'open': True}]}
    input_shapes = {'add_element': (1,)}

    def __init__(self, inputs=None, alias=None):
        super().__init__(self.nodeName, {'add_element': {'io': 'in', 'variadic': True}, 'data': {'io': 'out'}}, alias=alias)
        self.inputs = SequenceElement(self, 'inputs', list(inputs or []), register_in_node=False)
        self.inputs.input_ports = [f'input_{i}' for i in range(len(self.inputs))]
        self.sources = []
        for name, item in zip(self.inputs.input_ports, self.inputs):
            element = DataElement(self, name, np.zeros(1) if item['source'] is None else item['source'])
            vars(self)[name] = element
            self.sources.append(element)
            self.pending_terminals[name] = {'io': 'in'}
        self.add_element = DataElement(self, 'add_element', None, register_in_node=False)
        self.data = AnalysableElement(self, 'data', np.zeros((len(self.inputs), 2)))
        self.validate_parameters({})
        self.c_update()

    def validate_parameters(self, changes):
        for source, item in zip(self.sources, self.inputs):
            values = np.asarray(source.value)
            if values.shape != (1,) or values.dtype.kind not in 'biuf' or not np.isfinite(values).all():
                raise ValueError('Clustering sources must provide one finite numeric value, shape (1,)')
            interval = np.asarray(item['interval'])
            if interval.shape != (2,) or interval.dtype.kind not in 'iuf' or not np.isfinite(interval).all() or interval[0] == interval[1]:
                raise ValueError('Each interval requires distinct finite start and end values')

    def c_update(self):
        values = np.fromiter((source.value[0] for source in self.sources), dtype=float, count=len(self.sources))
        start, end = np.asarray([item['interval'] for item in self.inputs], dtype=float).reshape(-1, 2).T
        self.data.value[:, 0] = values
        self.data.value[:, 1] = np.clip((values - start) / (end - start), 0, 1)

    def connect_input(self, name, source, parameters):
        inputs = parameters.setdefault('inputs', [])
        if name == 'add_element':
            name = f'input_{len(inputs)}'
            inputs.append({'source': source, 'interval': [0, 1]})
        else:
            inputs[int(name.removeprefix('input_'))]['source'] = source
        return name, {}

    def disconnect_input(self, name, parameters):
        parameters['inputs'][int(name.removeprefix('input_'))]['source'] = None
        return ()

    def configure_graph(self, graph, parameters):
        graph['connections'] = [edge for edge in graph['connections'] if edge['target']['nodeId'] != self.name()]
        for i, item in enumerate(parameters['inputs']):
            if item['source'] is not None:
                name = f'input_{i}'
                graph['connections'].append({'id': f'{self.name()}:{name}', 'source': item['source'],
                                             'target': {'nodeId': self.name(), 'element': name}})
