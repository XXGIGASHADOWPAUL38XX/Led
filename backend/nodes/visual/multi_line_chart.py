from backend.components.elements.parameters import Parameter, SequenceElement, DataElement
import numpy as np
from backend.components.elements.element_value import ElementValue
from backend.components.elements.node_selector.chart_line_from_node import ChartLineNodeSelector
from backend.nodes.visual.line_chart import LineChartNode

class MultiLineChartNode(LineChartNode):
    """Plot several selected Elements as separate scalar histories.

    Configure source references in `node_selectors` and `number_points`.
    Each visual update samples the last flattened value from each selected
    Element, or zero if absent. Output `data` is shaped (lines, number_points)
    and contains numerical histories for frontend subscribers."""
    nodeName = 'MultiLineChart'

    def __init__(self, node_selectors=None, number_points=100, alias=None):
        super().__init__(self.nodeName, terminals={'data': {'io': 'out'}}, alias=alias)
        selector_values = node_selectors or [None]
        self.node_selectors = SequenceElement(self, 'node_selectors', [ChartLineNodeSelector(self, f'node_selector_{index}', ElementValue(value), selection_nodes=self.get_nodes) for index, value in enumerate(selector_values)], register_in_node=False)
        self.number_points = Parameter(self, 'number_points', number_points, minimum=1, maximum=4096, integer=True)
        self.data = DataElement(self, 'data', np.zeros((len(self.node_selectors), int(number_points))))

    def parameters_changed(self, name):
        if name == 'number_points':
            self.data.value = np.zeros((len(self.node_selectors), int(self.number_points.value)))

    def c_update(self):
        values = [float(np.asarray(selector.selected_element.value).reshape(-1)[-1]) if selector.selected_element is not None and np.asarray(selector.selected_element.value).size else 0.0 for selector in self.node_selectors]
        self.data.value[:] = np.roll(self.data.value, -1, axis=1)
        self.data.value[:, -1] = values
        return self.data
