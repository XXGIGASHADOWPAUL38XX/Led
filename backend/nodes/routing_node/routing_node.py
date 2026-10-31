import numpy as np

from backend.components.elements.parameters import DataElement, SequenceElement
from backend.overrides.CNode import CNode
from backend.updatable.updatable import AudioUpdatable


class RoutingNode(CNode, AudioUpdatable):
    """Route the strongest positive scalar source to a single enabled output.

    `operator_nodes` selects nodes exposing one-value `data` outputs.
    Inputs `input_0`, ... read those values. Output `data` is one-hot;
    `route_0`, ... are one-value enable outputs and `level` is the winning
    source's value. Silence disables all routes; ties choose the first source.
    """

    nodeName = 'Routing'

    def __init__(self, operator_nodes=None, alias: str | None = None):
        super().__init__(self.nodeName, {'data': {'io': 'out'}, 'level': {'io': 'out'}}, alias=alias)
        self.operator_nodes = SequenceElement(self, 'operator_nodes', list(operator_nodes or []))
        self.inputs, self.routes = [], []
        for index, node in enumerate(self.operator_nodes):
            name = f'input_{index}'
            source = DataElement(self, name, node.data if node is not None else np.zeros(1))
            route = DataElement(self, f'route_{index}', np.zeros(1))
            vars(self)[name], vars(self)[route.name] = source, route
            self.pending_terminals[name] = {'io': 'in'}
            self.pending_terminals[route.name] = {'io': 'out'}
            self.inputs.append(source)
            self.routes.append(route)
        self.data = DataElement(self, 'data', np.zeros(len(self.inputs)))
        self.level = DataElement(self, 'level', np.zeros(1))
        self.validate_parameters({})

    def validate_parameters(self, changes):
        if any(np.size(source.value) != 1 for source in self.inputs):
            raise ValueError('Routing sources must each provide one value')

    def connect_input(self, name, source, parameters):
        if name.startswith('input_'):
            if source['element'] != 'data':
                raise ValueError('Routing sources must use their data output')
            parameters['operator_nodes'][int(name.removeprefix('input_'))] = {'nodeId': source['nodeId']}
            return name, {}
        return super().connect_input(name, source, parameters)

    def disconnect_input(self, name, parameters):
        if name.startswith('input_'):
            parameters['operator_nodes'][int(name.removeprefix('input_'))] = None
            return ()
        return super().disconnect_input(name, parameters)

    def c_update(self):
        values = np.array([float(np.asarray(source.value).reshape(-1)[0]) for source in self.inputs])
        self.data.value[:] = 0
        self.level.value[:] = 0
        if values.size:
            winner = int(np.argmax(values))
            if values[winner] > 0:
                self.data.value[winner] = 1
                self.level.value[:] = values[winner]
        for index, route in enumerate(self.routes):
            route.value[:] = self.data.value[index]
