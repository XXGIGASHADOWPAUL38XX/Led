from backend.components.elements.parameters import Parameter, DataElement
import numpy as np

from config import FREQ_BINS
from backend.rainbow.config import RAINBOW_INV_FRACTION
from backend.components.elements.element import Element
from backend.components.elements.element_value import ElementValue

from backend.enums.gradiant.gradiant_mode import GradiantMode
from backend.nodes.rainbow.gradiant import GradiantNode
from backend.overrides.CNode import CNode

class RainbowNode(CNode):
    """Pass through or mirror an RGB gradient for a color strip.

    Input `gradiant` and output `data` are RGB arrays in [0, 255]. Configure
    `n_points` for the default embedded GradiantNode and `mode` for LINEAR
    or MIRROR; MIRROR joins every other source row with its reverse.
    Refreshes on visual updates; `inv_fraction` currently has no effect."""

    nodeName = "Rainbow"

    def __init__(
            self,
            n_points: int = FREQ_BINS,
            inv_fraction: int | float = RAINBOW_INV_FRACTION,
            gradiant: Element | None = None,
            mode: GradiantMode = GradiantMode.LINEAR,
            parent: CNode | None = None,
            alias: str | None = None,
    ) -> None:
        terminals = {
            "gradiant": {"io": "in"},
            "data": {"io": "out"},
        }

        CNode.__init__(self, self.nodeName, terminals=terminals, parent=parent, alias=alias)

        self.n_points = Parameter(self, 'n_points', n_points, minimum=1, maximum=4096, integer=True)
        self.inv_fraction = Parameter(self, 'inv_fraction', inv_fraction, minimum=0, maximum=1)
        self.gradiant = DataElement(self, 'gradiant', ElementValue(gradiant or GradiantNode(n_points, parent=self).data))
        self.mode = Parameter(self, 'mode', mode, kind='enum')
        self.data = DataElement(self, 'data', ElementValue(np.zeros_like(self.gradiant.value)))
        self.gradiant.valueChanged.connect(self.refresh_rainbow)
        self.mode.valueChanged.connect(self.refresh_rainbow)
        self.refresh_rainbow()

    def c_update(self):
        self.refresh_rainbow()

    def refresh_rainbow(self, *_args):
        rainbow_rgb = np.asarray(self.gradiant.value, dtype=int)

        if self.mode.value == GradiantMode.MIRROR:
            rainbow_rgb = np.concatenate(((x := rainbow_rgb[::2]), x[::-1]))
        if self.data.value.shape != rainbow_rgb.shape:
            self.data.value = np.zeros_like(rainbow_rgb)
        self.data.value[:] = rainbow_rgb

GradiantRainbowNode = RainbowNode
