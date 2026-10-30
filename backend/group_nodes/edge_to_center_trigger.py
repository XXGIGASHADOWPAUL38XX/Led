from backend.components.elements.parameters import Parameter, DataElement
import numpy as np
from config import FREQ_BINS
from backend.components.elements import AnalysableElement
from backend.components.elements.element_value import ElementValue
from backend.nodes.function.outbounds_fct import OutboundsFctNode
from backend.nodes.group_node import GroupNode
from backend.nodes.pipelines.transforms.operator_node import OperatorPipelineNode
from backend.nodes.pipelines.transforms.value_transformer import ValueTransformerPipelineNode
from backend.nodes.window.window import WindowNode
from backend.nodes.windows_fcts.decreasing_avg_window_fct import DecreasingAvgWindowFct

class EdgeToCenterTriggerNode(GroupNode):
    """Turn a trigger pulse into a fading edge-to-center intensity profile.

    Input `input_trigger` is a one-element pulse array. Output `data` has
    shape (length,). Child nodes retain a weighted-max `decay_length` history,
    vary the center level against fixed edges, and multiply by decay strength."""
    nodeName = 'EdgeToCenterTrigger'

    def __init__(self, input_trigger=np.zeros(1), length=FREQ_BINS, decay_length=5, alias=None):
        super().__init__(nodes=[], terminals={'input_trigger': {'io': 'in'}, 'data': {'io': 'out'}}, alias=alias)
        self.input_trigger = DataElement(self, 'input_trigger', ElementValue(input_trigger))
        self.length = Parameter(self, 'length', length, minimum=1, maximum=4096, integer=True)
        self.window_node = WindowNode(input_data=self.input_trigger, length=decay_length, parent=self, alias=f'{self.alias}_window')
        self.decay_node = DecreasingAvgWindowFct(window=self.window_node, avg_axis=0, parent=self, alias=f'{self.alias}_decay')
        self.center_value_node = ValueTransformerPipelineNode(input_value=self.decay_node.data, input_value_interval=[0, 1], output_value_interval=[1, -1], alias=f'{self.alias}_center_value')
        self.outbounds_node = OutboundsFctNode(y_outbound=1, y_center=self.center_value_node.output_value, length=length, alias=f'{self.alias}_outbounds')
        self.intensity_node = OperatorPipelineNode(arguments=[self.outbounds_node.data, '*', self.decay_node.data], length=length, alias=f'{self.alias}_intensity')
        self.decay_length = self.window_node.length
        self.data = AnalysableElement(self, 'data', ElementValue(self.intensity_node.data))
        self.set_nodes([self.window_node, self.decay_node, self.center_value_node, self.outbounds_node, self.intensity_node])
