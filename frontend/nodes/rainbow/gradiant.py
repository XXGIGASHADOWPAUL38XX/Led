import colorsys
import numpy as np

from config import FREQ_BINS
from frontend.components.elements.color_picker import ColorPicker
from frontend.components.elements.dials import LinearDial
from frontend.components.elements import AnalysableElement
from frontend.components.elements.element import Element
from frontend.components.elements.element_value import ElementValue
from frontend.components.elements.textedit import TextEdit
from frontend.overrides.CNode import CNode


class GradiantNode(CNode):
    """Generate a spatial RGB gradient by interpolating in HSV color space.

    Output `data` has shape (n_points, 3), integer channels in [0, 255].
    Configure `n_points`, RGB `color_in`/`color_out`, and extra hue `cycle`;
    changes regenerate the gradient. No input terminals are declared."""

    nodeName = "Gradiant"

    def __init__(
        self,
        n_points: int = FREQ_BINS,
        color_in=(255, 0, 0),
        color_out=(0, 0, 255),
        cycle=1,
        render: bool = True,
        parent: CNode | None = None,
        alias: str | None = None,
    ) -> None:
        terminals = {
            "data": {"io": "out"},
        }
        super().__init__(self.nodeName, terminals=terminals, render=render, parent=parent, alias=alias)

        self.n_points = TextEdit(self, "n_points", ElementValue(n_points))
        self.color_in = ColorPicker(self, "color_in", ElementValue(color_in))
        self.color_out = ColorPicker(self, "color_out", ElementValue(color_out))
        self.cycle = LinearDial(self, "cycle", 0, 10, ElementValue(cycle))
        self.data = Element(self, "data", ElementValue(np.zeros((int(self.n_points.value), 3), dtype=int)))

        self.n_points.valueChanged.connect(self.refresh_gradiant)
        self.color_in.valueChanged.connect(self.refresh_gradiant)
        self.color_out.valueChanged.connect(self.refresh_gradiant)
        self.cycle.valueChanged.connect(self.refresh_gradiant)
        self.refresh_gradiant()

    def refresh_gradiant(self):
        try:
            n_points = int(self.n_points.value)
        except (TypeError, ValueError):
            return

        if self.data.value.shape != (n_points, 3):
            self.data.value = np.zeros((n_points, 3), dtype=int)

        self.data.value[:] = self.build_rgb(n_points, self.color_in.value, self.color_out.value, self.cycle.value)

    @staticmethod
    def build_rgb(n_points, color_in, color_out, cycle=1):
        hsv_in = np.array(colorsys.rgb_to_hsv(*(np.asarray(color_in, dtype=float) / 255.0)))
        hsv_out = np.array(colorsys.rgb_to_hsv(*(np.asarray(color_out, dtype=float) / 255.0)))
        offsets = np.linspace(0, 1, n_points)[:, None]
        hsv = hsv_in + (hsv_out - hsv_in) * offsets
        hsv[:, 0] = (hsv_in[0] + offsets[:, 0] * ((hsv_out[0] - hsv_in[0]) + cycle)) % 1.0
        rgb = np.array([colorsys.hsv_to_rgb(*point) for point in hsv]) * 255
        return np.clip(np.rint(rgb), 0, 255).astype(int)
