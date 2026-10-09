from frontend.components.elements.parameters import DataElement
import numpy as np

from backend.pipelines.pipeline import VisualPipeline
from config import FREQ_BINS
from frontend.components.elements.element_value import ElementValue
from frontend.overrides.CNode import CNode


class RGBAPipelineNode(VisualPipeline, CNode):
    """Combine per-position RGB colors and normalized opacity.

    Inputs `rgb` shaped (FREQ_BINS, 3) in [0, 255] and `alpha` shaped
    (FREQ_BINS,) in [0, 1] produce `rgba` shaped (FREQ_BINS, 4) each visual
    update. Alpha is multiplied by 255; values are not clipped."""

    nodeName = "RGBAPipeline"

    def __init__(
        self,
        rgb: np.ndarray = np.zeros((FREQ_BINS, 3)),
        alpha: np.ndarray = np.zeros(FREQ_BINS),
        render: bool = True,
        alias: str | None = None,
    ) -> None:
        terminals = {
            "rgb": {"io": "in"},
            "alpha": {"io": "in"},
            "rgba": {"io": "out"},
        }
        VisualPipeline.__init__(self)
        CNode.__init__(self, node_name=self.nodeName, terminals=terminals, render=render, alias=alias)

        self.rgb = DataElement(self, 'rgb', ElementValue(rgb))
        self.alpha = DataElement(self, 'alpha', ElementValue(alpha))
        self.rgba = DataElement(self, 'rgba', ElementValue(np.zeros((FREQ_BINS, 4))))

    def c_update(self):
        rgb = self.rgb.value[:FREQ_BINS]

        self.rgba.value[:] = np.concatenate(
            (rgb, self.alpha.value[:, np.newaxis] * 255.), axis=1
        )
