import numpy as np

from backend.pipelines.pipeline import AudioPipeline
from frontend.components.elements import AnalysableElement
from frontend.components.elements.element import Element
from frontend.components.elements.element_value import ElementValue
from frontend.overrides.CNode import CNode


class RMSPipelineNode(CNode, AudioPipeline):
    """Measure overall audio level with root mean square amplitude.

    Input `buffer_data` is audio, typically shaped (channels, samples).
    Output `data` is a one-element array of sqrt(mean(audio ** 2)) across
    channels and samples each audio update. Chart settings do not alter RMS."""

    nodeName = "RMS"

    def __init__(
        self,
        buffer_data: np.ndarray = np.zeros((2, 0)),
        title: str = "RMS",
        number_points: int = 100,
        left_label: str = "Level",
        bottom_label: str = "Time",
        y_min: float = 0.0,
        y_max: float = 1.0,
        render: bool = True,
        alias: str | None = None,
    ) -> None:
        terminals = {
            "buffer_data": {"io": "in"},
            "data": {"io": "out"},
        }
        super().__init__(self.nodeName, terminals, render=render, alias=alias)

        self.buffer_data = Element(self, "buffer_data", ElementValue(buffer_data))
        self.data = AnalysableElement(self, "data", ElementValue(np.zeros(1)))
        self.title = ElementValue(title)  # kept for backward-compat signature/state
        self.number_points = Element(self, "number_points", ElementValue(number_points))
        self.left_label = Element(self, "left_label", ElementValue(left_label))
        self.bottom_label = Element(self, "bottom_label", ElementValue(bottom_label))
        self.y_min = Element(self, "y_min", ElementValue(y_min))
        self.y_max = Element(self, "y_max", ElementValue(y_max))

    def c_update(self):
        self.data.value[...] = np.sqrt(np.mean(self.buffer_data.value ** 2))
