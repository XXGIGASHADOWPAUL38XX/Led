from backend.components.elements.parameters import Parameter, DataElement
import numpy as np
from config import FFT_SIZE
from backend.components.elements import AnalysableElement
from backend.components.elements.element_value import ElementValue
from backend.nodes.group_node import GroupNode
from backend.nodes.pipelines import AmplitudesNode
from backend.nodes.pipelines.amplitudes.avg_frequencies import AvgFrequenciesNode
from backend.nodes.pipelines.auditory.filter.band_filter import BandFilterPipelineNode
from backend.nodes.pipelines.auditory.rms import RMSPipelineNode
from backend.nodes.pipelines.transforms.clip_node import ClipNode
from backend.nodes.pipelines.transforms.operator_node import OperatorPipelineNode
from backend.nodes.trigger.trigger import TriggerNode
from backend.nodes.window.window import WindowNode
from backend.nodes.windows_fcts.max_window_fct import MaxWindowFct

class SnareDecayNode(GroupNode):
    """Combine band energy and spectral change into a trigger pipeline.

    Input `buffer_data` is channels-first audio. Output `data` is a
    one-element TriggerNode pulse array. Configure `min_frequency` and
    `max_frequency` (Hz) and RMS `threshold`; child nodes compare new spectral
    energy with delayed history and require weighted frequency above 500 Hz.
    The final trigger currently uses EQUAL against 0.5 on a boolean condition."""
    nodeName = 'SnareDecay'

    def __init__(self, buffer_data: np.ndarray=np.zeros((2, FFT_SIZE)), min_frequency: float=300, max_frequency: float=1000, threshold: float=0.35, alias: str | None=None) -> None:
        super().__init__(nodes=[], terminals={'buffer_data': {'io': 'in'}, 'data': {'io': 'out'}}, alias=alias)
        self.buffer_data = DataElement(self, 'buffer_data', ElementValue(buffer_data))
        self.band_filter_node = BandFilterPipelineNode(buffer_data=self.buffer_data, lowcut=min_frequency, highcut=max_frequency, alias=f'{self.alias}_band_filter')
        self.amplitudes_node = AmplitudesNode(buffer=self.band_filter_node.data, fft_size=self.buffer_data.value.shape[-1], alias=f'{self.alias}_amplitudes')
        self.amplitude_history_window = WindowNode(input_data=self.amplitudes_node.data, length=5, offset=1, alias=f'{self.alias}_amplitude_history')
        self.previous_amplitude_max = MaxWindowFct(window=self.amplitude_history_window, avg_axis=0, alias=f'{self.alias}_previous_amplitude_max')
        self.amplitude_difference = OperatorPipelineNode(arguments=[self.amplitudes_node.data, '-', self.previous_amplitude_max.data], length=self.amplitudes_node.data.value.shape[-1], alias=f'{self.alias}_amplitude_difference')
        self.positive_amplitude_difference = ClipNode(input_value=self.amplitude_difference.data, min_value=0, max_value=10000, alias=f'{self.alias}_positive_amplitude_difference')
        self.rms_node = RMSPipelineNode(buffer_data=self.band_filter_node.data, alias=f'{self.alias}_rms')
        self.avg_frequencies_node = AvgFrequenciesNode(input_frequencies=self.amplitudes_node.frequencies, input_amplitudes=self.positive_amplitude_difference.data, alias=f'{self.alias}_avg_frequencies')
        self.threshold = Parameter(self, 'threshold', threshold, minimum=0, maximum=1)
        self.condition_node = OperatorPipelineNode(arguments=['(', self.rms_node.data, '>', self.threshold, ')', '&', '(', self.avg_frequencies_node.data, '>', 500, ')'], length=1, alias=f'{self.alias}_condition')
        self.trigger_node = TriggerNode(input_data=self.condition_node.data, threshold=0.5, alias=f'{self.alias}_trigger')
        self.min_frequency = self.band_filter_node.lowcut
        self.max_frequency = self.band_filter_node.highcut
        self.data = AnalysableElement(self, 'data', ElementValue(self.trigger_node.data))
        self.set_nodes([self.band_filter_node, self.amplitudes_node, self.amplitude_history_window, self.previous_amplitude_max, self.amplitude_difference, self.positive_amplitude_difference, self.rms_node, self.avg_frequencies_node, self.condition_node, self.trigger_node])
