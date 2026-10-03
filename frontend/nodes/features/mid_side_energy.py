import numpy as np

from backend.pipelines.pipeline import AudioPipeline
from config import FFT_SIZE
from frontend.components.elements import AnalysableElement
from frontend.components.elements.element import Element
from frontend.components.elements.element_value import ElementValue
from frontend.components.elements.textedit import TextEdit
from frontend.overrides.CNode import CNode


class MidSideEnergyNode(CNode, AudioPipeline):
    """nodeName labels the graph node; this node outputs mid/side stereo energy metrics."""

    nodeName = "MidSideEnergy"

    def __init__(self, buffer_data=np.zeros((2, FFT_SIZE)), length=FFT_SIZE, render: bool = True, alias: str | None = None) -> None:
        terminals = {
            "buffer_data": {"io": "in"},
            "mid_energy": {"io": "out"},
            "side_energy": {"io": "out"},
            "mid_ratio": {"io": "out"},
            "data": {"io": "out"},
        }
        super().__init__(self.nodeName, terminals, render=render, alias=alias)
        self.length = TextEdit(self, "length", ElementValue(length))
        self.buffer_data = Element(self, "buffer_data", ElementValue(buffer_data))
        self.mid_energy = Element(self, "mid_energy", ElementValue(np.zeros(1)))
        self.side_energy = Element(self, "side_energy", ElementValue(np.zeros(1)))
        self.mid_ratio = Element(self, "mid_ratio", ElementValue(np.zeros(1)))
        self.data = AnalysableElement(self, "data", ElementValue(np.zeros(2)))

        self.length.valueChanged.connect(self.on_length_change)
        self.should_process = True

    def on_length_change(self):
        self.should_process = False

        try:
            int_length = int(self.length.value)
            self.buffer_data.value = np.hstack((
                self.buffer_data.value[:, :int_length],
                np.zeros((2, max(0, int_length - self.buffer_data.value.shape[1]))),
            ))
            self.data.value = np.zeros(2)
        except (TypeError, ValueError):
            return
        finally:
            self.should_process = True

    def c_update(self):
        if not self.should_process:
            return

        data = np.asarray(self.buffer_data.value, dtype=float)
        left = data[0]
        right = data[1]

        mid = (left + right) * 0.5
        side = (left - right) * 0.5
        self.mid_energy.value[...] = np.mean(mid ** 2) if mid.size else 0.0
        self.side_energy.value[...] = np.mean(side ** 2) if side.size else 0.0
        self.mid_ratio.value[...] = 0. if (t:=(self.mid_energy.value + self.side_energy.value)) == 0 else self.mid_energy.value / t
        self.data.value[:] = [self.mid_energy.value[0], self.side_energy.value[0]]
