from backend.components.elements.parameters import Parameter
import numpy as np

from backend.components.elements import AnalysableElement
from backend.components.elements.element_value import ElementValue
from backend.overrides.CNode import CNode
from backend.overrides.point_count_node import PointCountNode
from backend.nodes.pipelines.amplitudes.amplitude_transformer import AmplitudesTransformer

class LinearAmplitudesTransformerNode(PointCountNode, AmplitudesTransformer):
    """Exponentiate a spectrum without modifying its source.

    `input_data` and output `data` have shape (number_points,). The editable
    point count adopts newly connected spectra. `log` is the exponent;
    `powering` is unused. Use Correlate before this node to spread values.
    """

    # Point count follows newly connected spectra and remains editable.
    nodeName = "LinearAmplitudesTransformer"
    ui = {'title': 'Linear Amplitudes Transformer',
     'description': 'Apply an exponent to a spectrum without changing its source.',
     'category': 'amplitudes',
     'fields': [{'name': 'number_points', 'control': 'slider', 'label': 'Points', 'rebuild': True},
                {'name': 'input_data', 'control': 'port'},
                {'name': 'powering', 'control': 'slider', 'label': 'Weighting'},
                {'name': 'log', 'control': 'slider'}],
     'views': [{'kind': 'bars', 'data': 'data', 'label': 'Data', 'open': True}]}

    def __init__(
            self,
            input_data: np.ndarray | None = None,
            powering: float = 1.,
            log: float = 1.,
            alias: str | None = None,
            number_points: int | None = None,
    ) -> None:
        terminals = {
            "input_data": {"io": "in"},
            "data": {"io": "out"},
        }

        CNode.__init__(self, self.nodeName, terminals, alias=alias, powering=powering, log=log)

        self.init_points(number_points, input_data=(input_data, ()))
        self.powering = Parameter(self, 'powering', powering, minimum=0, maximum=10)
        self.log = Parameter(self, 'log', log, minimum=0.01, maximum=10)
        self.log.valueChanged.connect(self._log_changed)
        self.data = AnalysableElement(self, "data", ElementValue(np.zeros(int(self.number_points.value))))

    @staticmethod
    def migrate_graph(node, graph):
        parameters = node.setdefault('parameters', {})
        controls = {'correlation_offset', 'correlation_step'}
        incoming = [edge for edge in graph['connections'] if edge['target']['nodeId'] == node['id']]
        if not controls.intersection(parameters) and not any(edge['target']['element'] in controls for edge in incoming):
            return
        values = {name: parameters.pop(name, default) for name, default in
                  (('correlation_offset', 1.), ('correlation_step', 0.))}
        if any(value is None for value in values.values()):
            values = {'correlation_offset': 1., 'correlation_step': 0.}
        ids = {item['id'] for item in graph['nodes']}
        name = f"{node['id']} correlation"
        while name in ids:
            name += '_'
        if parameters.get('input_data') is not None:
            values['input_data'] = parameters['input_data']
        else:
            from config import FREQ_BINS
            values['shape'] = [parameters.get('number_points') or FREQ_BINS]
        for edge in incoming:
            target = edge['target']
            if target['element'] in controls | {'input_data'}:
                target['nodeId'] = name
                if target['element'] == 'input_data':
                    values['input_data'] = edge['source']
                    values.pop('shape', None)
        x, y = node.get('position', [0, 0])
        graph['nodes'].append({'id': name, 'type': 'Correlate',
                               'position': [x - 430, y + 500], 'parameters': values})
        parameters['input_data'] = {'nodeId': name, 'element': 'data'}
        edge_ids = {edge['id'] for edge in graph['connections']}
        edge_id = f'{name}:data'
        while edge_id in edge_ids:
            edge_id += '_'
        graph['connections'].append({'id': edge_id, 'source': parameters['input_data'],
                                     'target': {'nodeId': node['id'], 'element': 'input_data'}})

    def c_update(self):
        self.transform_amplitudes(self.input_data.value)

    def transform_amplitudes(self, data):
        np.power(data, self.log.value, out=self.data.value)
