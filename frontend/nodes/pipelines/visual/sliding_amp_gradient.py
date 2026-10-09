from frontend.components.elements.parameters import DataElement, ReferenceElement
import numpy as np

from backend.pipelines.pipeline import VisualPipeline
from config import FREQ_BINS
from frontend.components.elements.dials import LinearDial
from frontend.components.elements import AnalysableElement
from frontend.components.elements.element_value import ElementValue
from frontend.overrides.CNode import CNode
from frontend.nodes.rainbow import RainbowNode


class SlidingAmpGradientNode(VisualPipeline, CNode):
    """Move an RGB gradient window according to spectral center frequency.

    Inputs `input_frequencies` (Hz) and `input_amplitudes` are matching
    vectors. Output `data` is an RGB array shaped (FREQ_BINS, 3) each visual
    update. Configure `slide_window_fraction` and distinct `slide_min_avg_amp`
    / `slide_max_avg_amp` bounds, which represent weighted frequency in Hz.
    Construction expects input_amplitudes to expose its array through `.value`."""

    nodeName = "SlidingAmpGradientNode"

    def __init__(
        self,
        input_frequencies: np.ndarray = np.zeros(FREQ_BINS),
        input_amplitudes: np.ndarray = np.zeros(FREQ_BINS),
        slide_window_fraction: float = 0.1,
        slide_min_avg_amp: int | float = 500,
        slide_max_avg_amp: int | float = 2500,
        render: bool = True,
        alias: str | None = None,
    ) -> None:
        terminals = {
            "input_frequencies": {"io": "in"},
            "input_amplitudes": {"io": "in"},
            "data": {"io": "out"},
        }
        VisualPipeline.__init__(self)
        CNode.__init__(self, node_name=self.nodeName, terminals=terminals, render=render, alias=alias)

        self.n_points_output = DataElement(self, 'n_points_output', input_amplitudes.value.shape[0])
        self.n_points_gradiant = DataElement(self, 'n_points_gradiant', ElementValue(int(self.n_points_output.value / slide_window_fraction)))
        self.input_frequencies = DataElement(self, 'input_frequencies', ElementValue(input_frequencies))
        self.input_amplitudes = DataElement(self, 'input_amplitudes', ElementValue(input_amplitudes))
        self.slide_window_fraction = DataElement(self, 'slide_window_fraction', ElementValue(slide_window_fraction))
        self.slide_min_avg_amp = LinearDial(self, "slide_min_avg_amp", 500, 3000, ElementValue(slide_min_avg_amp))
        self.slide_max_avg_amp = LinearDial(self, "slide_max_avg_amp", 2000, 5000, ElementValue(slide_max_avg_amp))
        self.gradiant_rainbow = ReferenceElement(self, 'gradiant_rainbow', ElementValue(RainbowNode(n_points=self.n_points_gradiant.value, parent=self, inv_fraction=0.4)))
        self.data = AnalysableElement(self, "data", ElementValue(np.zeros((FREQ_BINS, 3))), y_max=255.0)
        self.avg_amplitudes = DataElement(self, 'avg_amplitudes', ElementValue(0.0))

    def c_update(self):
        self.avg_amplitudes = np.sum((self.input_amplitudes.value * self.input_frequencies.value) / np.sum(self.input_amplitudes.value+1e-12))
        avg_scale_position = np.clip(
            (self.avg_amplitudes - self.slide_min_avg_amp.value) / (self.slide_max_avg_amp.value - self.slide_min_avg_amp.value),
            0,
            1
        )

        c = int(((1 - self.slide_window_fraction.value) * self.n_points_output.value / self.slide_window_fraction.value) * avg_scale_position)
        self.data.value[:] = self.gradiant_rainbow.value.data.value[c:c+self.n_points_output.value]
