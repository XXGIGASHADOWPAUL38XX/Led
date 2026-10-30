from backend.components.elements.parameters import Parameter, DataElement
import numpy as np

from config import FREQ_BINS, SKIP_LED_NUMBERS
from backend.updatable.updatable import VisualUpdatable
from backend.components.elements.element_value import ElementValue
from backend.overrides.CNode import CNode

class ControllerNode(CNode, VisualUpdatable):
    """Base RGBA-to-LED controller with brightness shaping.

    Input `rgba` has shape (FREQ_BINS, 4), channels in [0, 255]; there is no
    output terminal. `process_rgba()` modifies alpha in place using
    `power_log`, `min_alpha`, and `remove_alpha`, then fills internal `rgb`
    with black prefix LEDs. Use ESP32Node for transmission."""

    def __init__(
        self,
        rgba: np.ndarray = np.zeros((FREQ_BINS, 4)),
        power_log: float = 4.0,
        min_alpha: float = 0.4,
        remove_alpha: float = 4. / 255.,
        alias: str | None = None,
    ) -> None:
        terminals = {
            "rgba": {"io": "in"},
        }
        CNode.__init__(self, self.nodeName, terminals, alias=alias)

        self.power_log = Parameter(self, 'power_log', power_log, minimum=0, maximum=10)
        self.min_alpha = Parameter(self, 'min_alpha', min_alpha, minimum=0, maximum=1)
        self.remove_alpha = Parameter(self, 'remove_alpha', remove_alpha, minimum=0, maximum=1)
        self.rgba = DataElement(self, 'rgba', ElementValue(rgba))
        self.rgb = DataElement(self, 'rgb', ElementValue(np.zeros((FREQ_BINS + SKIP_LED_NUMBERS, 3))))

    def process_rgba(self):
        self.humanize_alpha()
        self.set_minimal_alpha()
        self.remove_alpha_min()
        self.rgba_to_rbg()

    def humanize_alpha(self):
        self.rgba.value[:, 3] = np.power(
            self.rgba.value[:, 3] / 255., self.power_log.value
        ) * 255

    def set_minimal_alpha(self):
        self.rgba.value[:, 3] = np.maximum(
            self.rgba.value[:, 3],
            self.min_alpha.value * 255,
        )

    def remove_alpha_min(self):
        threshold = self.remove_alpha.value * 255
        self.rgba.value[:, 3] = np.where(
            self.rgba.value[:, 3] < threshold,
            0,
            self.rgba.value[:, 3],
        )

    def rgba_to_rbg(self):
        self.rgb.value.fill(0)
        self.rgb.value[SKIP_LED_NUMBERS:SKIP_LED_NUMBERS + FREQ_BINS] = (
            self.rgba.value[:, :3]
            * (self.rgba.value[:, 3, None] / 255.0)
        )
