from backend.components.elements.parameters import Parameter, DataElement, RGBParameter
import colorsys
import numpy as np

from config import FREQ_BINS

from backend.components.elements.element_value import ElementValue
from backend.overrides.CNode import CNode

class GradiantNode(CNode):
    """Generate a spatial RGB gradient by interpolating in HSV color space.

    Output `data` has shape (n_points, 3), integer channels in [0, 255].
    Configure `n_points`, RGB `color_in`/`color_out`, and `cycle`, which scales
    the HSV transition: 0 stays at `color_in`, 1 reaches `color_out`;
    `color_in`/`color_out` accept RGB vectors; their `_red`, `_green`, `_blue`
    inputs accept one-element arrays that override individual channels.
    Changes regenerate the gradient."""

    nodeName = "Gradiant"

    def __init__(
        self,
        n_points: int = FREQ_BINS,
        color_in=(255, 0, 0),
        color_out=(0, 0, 255),
        cycle=1,
        parent: CNode | None = None,
        alias: str | None = None,
        color_in_red=None,
        color_in_green=None,
        color_in_blue=None,
        color_out_red=None,
        color_out_green=None,
        color_out_blue=None,
    ) -> None:
        terminals = {
            "color_in": {"io": "in"},
            "color_out": {"io": "in"},
            "data": {"io": "out"},
        }
        super().__init__(self.nodeName, terminals=terminals, parent=parent, alias=alias)

        self.n_points = Parameter(self, 'n_points', n_points, minimum=1, maximum=500, integer=True)
        self.color_in = RGBParameter(self, 'color_in', color_in, (color_in_red, color_in_green, color_in_blue))
        self.color_out = RGBParameter(self, 'color_out', color_out, (color_out_red, color_out_green, color_out_blue))
        self.cycle = Parameter(self, 'cycle', cycle, minimum=-10, maximum=10)
        self.data = DataElement(self, 'data', ElementValue(np.zeros((int(self.n_points.value), 3), dtype=int)))

        self.n_points.valueChanged.connect(self.refresh_gradiant)
        self.color_in.connect(self.refresh_gradiant)
        self.color_out.connect(self.refresh_gradiant)
        self.cycle.valueChanged.connect(self.refresh_gradiant)
        self.refresh_gradiant()

    def refresh_gradiant(self, *_args):
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
        hsv = hsv_in + (hsv_out - hsv_in) * offsets * cycle
        hsv[:, 0] %= 1.0
        hsv[:, 1:] = np.clip(hsv[:, 1:], 0, 1)
        rgb = np.array([colorsys.hsv_to_rgb(*point) for point in hsv]) * 255
        return np.clip(np.rint(rgb), 0, 255).astype(int)
