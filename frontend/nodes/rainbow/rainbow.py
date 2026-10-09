from frontend.components.elements.parameters import DataElement, EnumElement, IntegerDial
import numpy as np

from config import FREQ_BINS
from backend.rainbow.config import RAINBOW_INV_FRACTION
from frontend.components.elements.element import Element
from frontend.components.elements.element_value import ElementValue
from frontend.components.elements.dials import LinearDial
from frontend.enums.gradiant.gradiant_mode import GradiantMode
from frontend.nodes.rainbow.gradiant import GradiantNode
from frontend.overrides.CNode import CNode


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
            render: bool = True,
            parent: CNode | None = None,
            alias: str | None = None,
    ) -> None:
        terminals = {
            "gradiant": {"io": "in"},
            "data": {"io": "out"},
        }

        CNode.__init__(self, self.nodeName, terminals=terminals, render=render, parent=parent, alias=alias)

        self.n_points = IntegerDial(self, "n_points", 1, 4096, n_points)
        self.inv_fraction = LinearDial(self, "inv_fraction", 0, 1, ElementValue(inv_fraction))
        self.gradiant = DataElement(self, 'gradiant', ElementValue(gradiant or GradiantNode(n_points, render=False, parent=self).data))
        self.mode = EnumElement(self, 'mode', ElementValue(mode))
        self.data = DataElement(self, 'data', ElementValue(np.zeros_like(self.gradiant.value)))
        self.gradiant.valueChanged.connect(self.refresh_rainbow)
        self.mode.valueChanged.connect(self.refresh_rainbow)
        self.refresh_rainbow()


    def c_update(self):
        self.refresh_rainbow()

    def refresh_rainbow(self):
        rainbow_rgb = np.asarray(self.gradiant.value, dtype=int)

        if self.mode.value == GradiantMode.MIRROR:
            rainbow_rgb = np.concatenate(((x := rainbow_rgb[::2]), x[::-1]))
        if self.data.value.shape != rainbow_rgb.shape:
            self.data.value = np.zeros_like(rainbow_rgb)
        self.data.value[:] = rainbow_rgb


GradiantRainbowNode = RainbowNode
