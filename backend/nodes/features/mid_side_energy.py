from backend.components.elements.parameters import DataElement
import numpy as np

from backend.pipelines.pipeline import AudioPipeline
from backend.components.elements import AnalysableElement
from backend.components.elements.element_value import ElementValue
from backend.overrides.CNode import CNode

class MidSideEnergyNode(CNode, AudioPipeline):
    """Measure stereo center energy and stereo width.

    Input `buffer_data` has shape (2, samples), channels first. Outputs
    `mid_energy`, `side_energy`, and `mid_ratio` are one-element arrays;
    `data` is [mid_energy, side_energy]. Each audio update averages squared
    (L + R) / 2 and (L - R) / 2 across the full incoming buffer."""

    nodeName = "MidSideEnergy"
    input_shapes = {"buffer_data": (2, 0)}

    def __init__(self, buffer_data=np.zeros((2, 0)), alias: str | None = None) -> None:
        terminals = {
            "buffer_data": {"io": "in"},
            "mid_energy": {"io": "out"},
            "side_energy": {"io": "out"},
            "mid_ratio": {"io": "out"},
            "data": {"io": "out"},
        }
        super().__init__(self.nodeName, terminals, alias=alias)
        self.buffer_data = DataElement(self, 'buffer_data', ElementValue(buffer_data))
        self.mid_energy = DataElement(self, 'mid_energy', ElementValue(np.zeros(1)))
        self.side_energy = DataElement(self, 'side_energy', ElementValue(np.zeros(1)))
        self.mid_ratio = DataElement(self, 'mid_ratio', ElementValue(np.zeros(1)))
        self.data = AnalysableElement(self, "data", ElementValue(np.zeros(2)))

    @staticmethod
    def migrate_parameters(parameters):
        return {name: value for name, value in parameters.items() if name != "length"}

    def validate_parameters(self, changes):
        data = np.asarray(changes.get("buffer_data", self.buffer_data.value))
        if data.ndim != 2 or data.shape[0] != 2:
            raise ValueError("Mid/Side Energy requires a stereo buffer shaped (2, samples)")

    def c_update(self):
        data = np.asarray(self.buffer_data.value, dtype=float)
        left = data[0]
        right = data[1]

        mid = (left + right) * 0.5
        side = (left - right) * 0.5
        self.mid_energy.value[...] = np.mean(mid ** 2) if mid.size else 0.0
        self.side_energy.value[...] = np.mean(side ** 2) if side.size else 0.0
        self.mid_ratio.value[...] = 0. if (t:=(self.mid_energy.value + self.side_energy.value)) == 0 else self.mid_energy.value / t
        self.data.value[:] = [self.mid_energy.value[0], self.side_energy.value[0]]
