import numpy as np

from config import FREQ_BINS
from frontend.components.elements import AnalysableElement
from frontend.components.elements.element import Element
from frontend.components.elements.element_value import ElementValue
from frontend.nodes.function.outbounds_fct import OutboundsFctNode
from frontend.nodes.group_node import GroupNode
from frontend.nodes.pipelines.transforms.operator_node import OperatorPipelineNode
from frontend.nodes.pipelines.transforms.value_transformer import ValueTransformerPipelineNode
from frontend.nodes.window.window import WindowNode
from frontend.nodes.windows_fcts.decreasing_avg_window_fct import DecreasingAvgWindowFct


class EdgeToCenterTriggerNode(GroupNode):
    nodeName = "EdgeToCenterTrigger"

    def __init__(self, input_trigger=np.zeros(1), length=FREQ_BINS, decay_length=5, render=True, alias=None):
        super().__init__(
            nodes=[],
            terminals={"input_trigger": {"io": "in"}, "data": {"io": "out"}},
            title="Edge to center trigger",
            hide_node=False,
            render=render,
            alias=alias,
        )
        self.input_trigger = Element(self, "input_trigger", ElementValue(input_trigger))
        self.length = Element(self, "length", ElementValue(length))
        self.window_node = WindowNode(
            input_data=self.input_trigger,
            length=decay_length,
            render=render,
            parent=self,
            alias=f"{self.alias}_window",
        )
        self.decay_node = DecreasingAvgWindowFct(
            window=self.window_node,
            avg_axis=0,
            render=render,
            parent=self,
            alias=f"{self.alias}_decay",
        )
        self.center_value_node = ValueTransformerPipelineNode(
            input_value=self.decay_node.data,
            input_value_interval=[0, 1],
            output_value_interval=[1, -1],
            render=render,
            alias=f"{self.alias}_center_value",
        )
        self.outbounds_node = OutboundsFctNode(
            y_outbound=1,
            y_center=self.center_value_node.output_value,
            length=length,
            render=render,
            alias=f"{self.alias}_outbounds",
        )
        self.intensity_node = OperatorPipelineNode(
            arguments=[self.outbounds_node.data, "*", self.decay_node.data],
            length=length,
            render=render,
            alias=f"{self.alias}_intensity",
        )
        self.data = AnalysableElement(self, "data", ElementValue(self.intensity_node.data))
        self.nodes = [
            self.window_node,
            self.decay_node,
            self.center_value_node,
            self.outbounds_node,
            self.intensity_node,
        ]
