from backend.components.elements.parameters import Parameter, DataElement
import numpy as np
from backend.components.elements.element_value import ElementValue
from backend.components.elements.node_selector.chart_line_from_node import ChartLineNodeSelector
from backend.nodes.visual.line_chart import LineChartNode

class SingleLineChartNode(LineChartNode):
    """Plot a selected Element's latest scalar value over time.

    Configure `node_selector` or initial `input_data` to select an Element;
    its last flattened value is sampled each visual update, or zero if absent.
    `number_points` sets history length. Output `data` contains the
    numerical history for subscribers."""
    nodeName = 'SingleLineChart'

    def __init__(self, node_selector=None, input_data=None, number_points=100, alias=None):
        super().__init__(self.nodeName, terminals={'data': {'io': 'out'}}, alias=alias)
        self.node_selector = node_selector or ChartLineNodeSelector(self, 'node_selector', ElementValue(input_data), selection_nodes=self.get_nodes)
        if self.node_selector not in self.elements:
            self.elements.append(self.node_selector)
        self.number_points = Parameter(self, 'number_points', number_points, minimum=1, maximum=4096, integer=True)
        self.input_data = self.node_selector
        self.data = DataElement(self, 'data', np.zeros(int(number_points)))

    def parameters_changed(self, name):
        if name == 'number_points':
            self.data.value = np.zeros(int(self.number_points.value))

    def c_update(self):
        selected = self.node_selector.selected_element
        value = np.asarray(selected.value).reshape(-1) if selected is not None else np.zeros(0)
        self.data.value[:] = np.roll(self.data.value, -1)
        self.data.value[-1] = float(value[-1]) if value.size else 0.0
        return self.data
