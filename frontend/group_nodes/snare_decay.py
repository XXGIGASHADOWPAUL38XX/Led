import numpy as np

from config import FFT_SIZE
from frontend.components.elements import AnalysableElement
from frontend.components.elements.element import Element
from frontend.components.elements.element_value import ElementValue
from frontend.nodes.group_node import GroupNode
from frontend.nodes.pipelines import AmplitudesNode
from frontend.nodes.pipelines.amplitudes.avg_frequencies import AvgFrequenciesNode
from frontend.nodes.pipelines.auditory.filter.band_filter import BandFilterPipelineNode
from frontend.nodes.pipelines.auditory.rms import RMSPipelineNode
from frontend.nodes.pipelines.transforms.clip_node import ClipNode
from frontend.nodes.pipelines.transforms.operator_node import OperatorPipelineNode
from frontend.nodes.trigger.trigger import TriggerNode
from frontend.nodes.window.window import WindowNode
from frontend.nodes.windows_fcts.max_window_fct import MaxWindowFct


class SnareDecayNode(GroupNode):
    nodeName = "SnareDecay"

    def __init__(
        self,
        buffer_data: np.ndarray = np.zeros(FFT_SIZE),
        min_frequency: float = 300,
        max_frequency: float = 1000,
        threshold: float = 0.35,
        render: bool = True,
        alias: str | None = None,
    ) -> None:
        super().__init__(
            nodes=[],
            terminals={
                "buffer_data": {"io": "in"},
                "data": {"io": "out"},
            },
            title="Snare decay",
            hide_node=False,
            render=render,
            alias=alias,
        )

        self.buffer_data = Element(self, "buffer_data", ElementValue(buffer_data))
        self.band_filter_node = BandFilterPipelineNode(
            buffer_data=self.buffer_data,
            lowcut=min_frequency,
            highcut=max_frequency,
            render=render,
            alias=f"{self.alias}_band_filter",
        )
        self.amplitudes_node = AmplitudesNode(
            buffer=self.band_filter_node.data,
            fft_size=self.buffer_data.value.shape[-1],
            render=render,
            alias=f"{self.alias}_amplitudes",
        )
        self.amplitude_history_window = WindowNode(
            input_data=self.amplitudes_node.data,
            length=5,
            offset=1,
            render=render,
            alias=f"{self.alias}_amplitude_history",
        )
        self.previous_amplitude_max = MaxWindowFct(
            window=self.amplitude_history_window,
            avg_axis=0,
            render=render,
            alias=f"{self.alias}_previous_amplitude_max",
        )
        self.amplitude_difference = OperatorPipelineNode(
            arguments=[self.amplitudes_node.data, "-", self.previous_amplitude_max.data],
            length=self.amplitudes_node.data.value.shape[-1],
            render=render,
            alias=f"{self.alias}_amplitude_difference",
        )
        self.positive_amplitude_difference = ClipNode(
            input_value=self.amplitude_difference.data,
            min_value=0,
            max_value=10000,
            render=render,
            alias=f"{self.alias}_positive_amplitude_difference",
        )
        self.rms_node = RMSPipelineNode(
            buffer_data=self.band_filter_node.data,
            render=render,
            alias=f"{self.alias}_rms",
        )
        self.avg_frequencies_node = AvgFrequenciesNode(
            input_frequencies=self.amplitudes_node.frequencies,
            input_amplitudes=self.positive_amplitude_difference.data,
            render=render,
            alias=f"{self.alias}_avg_frequencies",
        )
        self.condition_node = OperatorPipelineNode(
            arguments=[
                "(", self.rms_node.data, ">", threshold, ")",
                "&",
                "(", self.avg_frequencies_node.data, ">", 500, ")",
            ],
            length=1,
            render=render,
            alias=f"{self.alias}_condition",
        )
        self.trigger_node = TriggerNode(
            input_data=self.condition_node.data,
            threshold=0.5,
            render=render,
            alias=f"{self.alias}_trigger",
        )
        self.data = AnalysableElement(self, "data", ElementValue(self.trigger_node.data))
        self.nodes = [
            self.band_filter_node,
            self.amplitudes_node,
            self.amplitude_history_window,
            self.previous_amplitude_max,
            self.amplitude_difference,
            self.positive_amplitude_difference,
            self.rms_node,
            self.avg_frequencies_node,
            self.condition_node,
            self.trigger_node,
        ]
