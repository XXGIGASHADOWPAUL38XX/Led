from backend.components.elements.parameters import DataElement
import numpy as np
from config import FFT_SIZE
from backend.components.elements import AnalysableElement
from backend.components.elements.element_value import ElementValue
from backend.nodes.group_node import GroupNode
from backend.nodes.pipelines import AmplitudesNode
from backend.nodes.pipelines.transforms.operator_node import OperatorPipelineNode
from backend.nodes.pipelines.transforms.peakfilter_node import PeakFilterNode
from backend.nodes.pipelines.transforms.threshold_filter_node import ThresholdFilterNode
from backend.nodes.window.window import WindowNode
from backend.nodes.windows_fcts.averaged_window_fct import AveragedWindowFct

class SinglePeakTriggerNode(GroupNode):
    """Isolate the strongest spectral peak above its recent average.

    Input `buffer_data` has shape (2, fft_size). Output `data` is a spectrum
    vector of retained amplitudes, not a boolean trigger. Child nodes compute
    FFT amplitudes, subtract a `window_length` frame mean, keep one local peak,
    and zero it unless it reaches `threshold`."""
    nodeName = 'SinglePeakTrigger'

    def __init__(self, buffer_data: np.ndarray=np.zeros((2, FFT_SIZE)), window_length: int=50, threshold: float=7.0, alias: str | None=None) -> None:
        super().__init__(nodes=[], terminals={'buffer_data': {'io': 'in'}, 'data': {'io': 'out'}}, alias=alias)
        self.buffer_data = DataElement(self, 'buffer_data', ElementValue(buffer_data))
        buffer_shape = self.buffer_data.value.shape
        self.amplitudes_node = AmplitudesNode(buffer=self.buffer_data, fft_size=buffer_shape[-1], alias=f'{self.alias}_amplitudes')
        self.window_node = WindowNode(input_data=self.amplitudes_node.data, length=window_length, alias=f'{self.alias}_window')
        self.window_function = AveragedWindowFct(window=self.window_node, avg_axis=0, alias=f'{self.alias}_average')
        self.subtract_node = OperatorPipelineNode(arguments=[self.amplitudes_node.data, '-', self.window_function.data], length=self.amplitudes_node.data.value.shape[-1], alias=f'{self.alias}_subtract_average')
        self.peak_filter_node = PeakFilterNode(input_value=self.subtract_node.data, peaks_to_keep=1, alias=f'{self.alias}_peak_filter')
        self.threshold_filter_node = ThresholdFilterNode(input_value=self.peak_filter_node.data, threshold=threshold, alias=f'{self.alias}_threshold_filter')
        self.threshold = self.threshold_filter_node.threshold
        self.window_length = self.window_node.length
        self.data = AnalysableElement(self, 'data', ElementValue(self.threshold_filter_node.data))
        self.set_nodes([self.amplitudes_node, self.window_node, self.window_function, self.subtract_node, self.peak_filter_node, self.threshold_filter_node])
