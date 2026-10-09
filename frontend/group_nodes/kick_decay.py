from frontend.components.elements.parameters import DataElement
import numpy as np

from config import FFT_SIZE
from frontend.components.elements import AnalysableElement
from frontend.components.elements.element_value import ElementValue
from frontend.enums.gradiant.trigger_mode import TriggerMode
from frontend.nodes.group_node import GroupNode
from frontend.nodes.pipelines.auditory.filter.low_filter import LowFilterPipelineNode
from frontend.nodes.pipelines.auditory.rms import RMSPipelineNode
from frontend.nodes.trigger.trigger import TriggerNode
from frontend.nodes.window.window import WindowNode
from frontend.nodes.windows_fcts.decreasing_avg_window_fct import DecreasingAvgWindowFct


class KickDecayNode(GroupNode):
    """Detect low-frequency attacks and produce a decaying intensity signal.

    Input `buffer_data` is channels-first audio. Output `data` is a
    one-element array from low-pass filtering, RMS threshold onset pulses,
    and weighted-max history. Configure `lowpass_freq` in Hz, `threshold`
    in RMS units, and `decay_length` in audio updates."""

    nodeName = "KickDecay"

    def __init__(
        self,
        buffer_data: np.ndarray = np.zeros(FFT_SIZE),
        lowpass_freq: float = 300,
        threshold: float = 0.35,
        decay_length: int = 5,
        render: bool = True,
        alias: str | None = None,
    ) -> None:
        super().__init__(
            nodes=[],
            terminals={
                "buffer_data": {"io": "in"},
                "data": {"io": "out"},
            },
            title="Kick decay",
            hide_node=False,
            render=render,
            alias=alias,
        )

        self.buffer_data = DataElement(self, 'buffer_data', ElementValue(buffer_data))

        self.low_filter_node = LowFilterPipelineNode(
            buffer_data=buffer_data,
            lowpass_freq=lowpass_freq,
            render=render,
            alias=f"{self.alias}_low_filter",
        )
        self.rms_node = RMSPipelineNode(
            buffer_data=self.low_filter_node.data,
            render=render,
            alias=f"{self.alias}_rms",
        )
        self.trigger_node = TriggerNode(
            input_data=self.rms_node.data,
            trigger_mode=TriggerMode.GREATER,
            threshold=threshold,
            render=render,
            alias=f"{self.alias}_trigger",
        )
        self.window_node = WindowNode(
            input_data=self.trigger_node.data,
            length=decay_length,
            render=render,
            alias=f"{self.alias}_window",
        )
        self.window_function = DecreasingAvgWindowFct(
            window=self.window_node,
            avg_axis=0,
            render=render,
            alias=f"{self.alias}_window_function",
        )

        self.lowpass_freq = self.low_filter_node.lowpass_freq
        self.threshold = self.trigger_node.threshold
        self.decay_length = self.window_node.length
        self.data = AnalysableElement(self, "data", ElementValue(self.window_function.data))
        self.nodes.value = [
            self.low_filter_node,
            self.rms_node,
            self.trigger_node,
            self.window_node,
            self.window_function,
        ]
