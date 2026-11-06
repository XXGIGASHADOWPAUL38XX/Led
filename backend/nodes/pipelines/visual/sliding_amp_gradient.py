from backend.components.elements.parameters import Parameter, DataElement, ReferenceElement
import numpy as np

from backend.pipelines.pipeline import VisualPipeline
from config import FREQ_BINS

from backend.components.elements import AnalysableElement
from backend.components.elements.element_value import ElementValue
from backend.overrides.CNode import CNode
from backend.nodes.rainbow import RainbowNode

class SlidingAmpGradientNode(VisualPipeline, CNode):
    """Move an RGB gradient window according to spectral center frequency.

    Inputs `input_frequencies` (Hz) and `input_amplitudes` are matching
    vectors. Output `data` is an RGB array shaped (number_points, 3) each visual
    update. Configure `slide_window_fraction` and distinct `slide_min_avg_amp`
    / `slide_max_avg_amp` bounds, which represent weighted frequency in Hz.
    `number_points` controls the output length independently of spectrum size."""

    nodeName = "SlidingAmpGradientNode"
    input_shapes = {"input_frequencies": (0,), "input_amplitudes": (0,)}

    def __init__(
        self,
        input_frequencies: np.ndarray = np.zeros(FREQ_BINS),
        input_amplitudes: np.ndarray = np.zeros(FREQ_BINS),
        slide_window_fraction: float = 0.1,
        slide_min_avg_amp: int | float = 500,
        slide_max_avg_amp: int | float = 2500,
        alias: str | None = None,
        number_points: int | None = None,
    ) -> None:
        terminals = {
            "input_frequencies": {"io": "in"},
            "input_amplitudes": {"io": "in"},
            "data": {"io": "out"},
        }
        VisualPipeline.__init__(self)
        CNode.__init__(self, node_name=self.nodeName, terminals=terminals, alias=alias)

        self.input_frequencies = DataElement(self, 'input_frequencies', ElementValue(input_frequencies))
        self.input_amplitudes = DataElement(self, 'input_amplitudes', ElementValue(input_amplitudes))
        self.number_points = Parameter(self, 'number_points', self.input_amplitudes.value.shape[0] if number_points is None else number_points, minimum=1, maximum=4096, integer=True)
        self.n_points_output = DataElement(self, 'n_points_output', int(self.number_points.value))
        self.n_points_gradiant = DataElement(self, 'n_points_gradiant', ElementValue(int(self.n_points_output.value / slide_window_fraction)))
        self.slide_window_fraction = Parameter(self, 'slide_window_fraction', slide_window_fraction, minimum=0.01, maximum=1)
        self.slide_min_avg_amp = Parameter(self, 'slide_min_avg_amp', slide_min_avg_amp, minimum=500, maximum=3000)
        self.slide_max_avg_amp = Parameter(self, 'slide_max_avg_amp', slide_max_avg_amp, minimum=2000, maximum=5000)
        self.gradiant_rainbow = ReferenceElement(self, 'gradiant_rainbow', ElementValue(RainbowNode(n_points=self.n_points_gradiant.value, parent=self, inv_fraction=0.4)))
        self.data = AnalysableElement(self, "data", ElementValue(np.zeros((int(self.number_points.value), 3))))
        self.avg_amplitudes = DataElement(self, 'avg_amplitudes', ElementValue(0.0))

    def validate_parameters(self, changes):
        if self.input_frequencies.value.shape != self.input_amplitudes.value.shape:
            raise ValueError('Frequencies and amplitudes must have matching shapes')
        if changes.get('slide_min_avg_amp', self.slide_min_avg_amp.value) >= changes.get('slide_max_avg_amp', self.slide_max_avg_amp.value):
            raise ValueError('Minimum frequency must be below maximum frequency')

    def parameters_changed(self, name):
        if name in ('number_points', 'slide_window_fraction'):
            self.n_points_output.value = int(self.number_points.value)
            self.n_points_gradiant.value = int(self.number_points.value / self.slide_window_fraction.value)
            self.gradiant_rainbow.value.n_points.value = self.n_points_gradiant.value
            self.gradiant_rainbow.value.parameters_changed('n_points')
            self.data.value = np.zeros((int(self.number_points.value), 3))

    def c_update(self):
        self.avg_amplitudes.value = np.sum((self.input_amplitudes.value * self.input_frequencies.value) / np.sum(self.input_amplitudes.value+1e-12))
        avg_scale_position = np.clip(
            (self.avg_amplitudes.value - self.slide_min_avg_amp.value) / (self.slide_max_avg_amp.value - self.slide_min_avg_amp.value),
            0,
            1
        )

        c = int(((1 - self.slide_window_fraction.value) * self.n_points_output.value / self.slide_window_fraction.value) * avg_scale_position)
        self.data.value[:] = self.gradiant_rainbow.value.data.value[c:c+self.n_points_output.value]
