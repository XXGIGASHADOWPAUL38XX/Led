import numpy as np

from config import FFT_SIZE
from frontend.components.elements import AnalysableElement
from frontend.components.elements.element import Element
from frontend.components.elements.element_value import ElementValue
from frontend.nodes.group_node import GroupNode
from frontend.nodes.pipelines import AmplitudesNode
from frontend.nodes.pipelines.transforms.operator_node import OperatorPipelineNode
from frontend.nodes.pipelines.transforms.peakfilter_node import PeakFilterNode
from frontend.nodes.pipelines.transforms.threshold_filter_node import ThresholdFilterNode
from frontend.nodes.window.window import WindowNode
from frontend.nodes.windows_fcts.averaged_window_fct import AveragedWindowFct


class SinglePeakTriggerNode(GroupNode):
    """Isolate the strongest spectral peak above its recent average.

    Input `buffer_data` has shape (2, fft_size). Output `data` is a spectrum
    vector of retained amplitudes, not a boolean trigger. Child nodes compute
    FFT amplitudes, subtract a `window_length` frame mean, keep one local peak,
    and zero it unless it reaches `threshold`."""

    nodeName = "SinglePeakTrigger"

    def __init__(
        self,
        buffer_data: np.ndarray = np.zeros(FFT_SIZE),
        window_length: int = 50,
        threshold: float = 7.0,
        render: bool = True,
        alias: str | None = None,
    ) -> None:
        super().__init__(
            nodes=[],
            terminals={
                "buffer_data": {"io": "in"},
                "data": {"io": "out"},
            },
            title="Single peak trigger",
            hide_node=False,
            render=render,
            alias=alias,
        )

        self.buffer_data = Element(self, "buffer_data", ElementValue(buffer_data))
        self.window_length = Element(self, "window_length", ElementValue(window_length))
        buffer_shape = self.buffer_data.value.shape

        self.amplitudes_node = AmplitudesNode(
            buffer=self.buffer_data,
            fft_size=buffer_shape[-1],
            render=render,
            alias=f"{self.alias}_amplitudes",
        )
        self.window_node = WindowNode(
            input_data=self.amplitudes_node.data,
            length=window_length,
            render=render,
            alias=f"{self.alias}_window",
        )
        self.window_function = AveragedWindowFct(
            window=self.window_node,
            avg_axis=0,
            render=render,
            alias=f"{self.alias}_average",
        )
        self.subtract_node = OperatorPipelineNode(
            arguments=[self.amplitudes_node.data, "-", self.window_function.data],
            length=self.amplitudes_node.data.value.shape[-1],
            render=render,
            alias=f"{self.alias}_subtract_average",
        )
        self.peak_filter_node = PeakFilterNode(
            input_value=self.subtract_node.data,
            peaks_to_keep=1,
            render=render,
            alias=f"{self.alias}_peak_filter",
        )
        self.threshold_filter_node = ThresholdFilterNode(
            input_value=self.peak_filter_node.data,
            threshold=threshold,
            render=render,
            alias=f"{self.alias}_threshold_filter",
        )

        self.data = AnalysableElement(self, "data", ElementValue(self.threshold_filter_node.data))
        self.nodes = [
            self.amplitudes_node,
            self.window_node,
            self.window_function,
            self.subtract_node,
            self.peak_filter_node,
            self.threshold_filter_node,
        ]
