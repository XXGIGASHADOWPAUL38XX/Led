from frontend.components.elements.parameters import EnumElement, IntegerDial, OptionalDial
import numpy as np

from config import FFT_SIZE, FREQ_BINS
from backend.updatable.updatable import AudioUpdatable
from frontend.components.elements import AnalysableElement
from frontend.components.elements.element_value import ElementValue
from frontend.enums.cut_side.cut_side_mode import CutSideMode
from frontend.overrides.CNode import CNode


class OutboundsFctNode(CNode, AudioUpdatable):
    """Generate a nonnegative mirrored edge-to-center intensity profile.

    Inputs `y_outbound`, `y_center`, and `y_offset` set edge level, center
    level, and cyclic shift fraction. Output `data` has shape (length,) each
    audio update. Configure `length` and optional `cute_side_mode`; negative
    levels clip to zero and the offset times length must be an integer shift."""

    nodeName = "OutboundsFct"

    def __init__(
        self,
        y_outbound: float = 1,
        y_center: float = -2,
        y_offset: float = 0,
        cute_side_mode: CutSideMode = CutSideMode.NONE,
        length: int = FREQ_BINS,
        render: bool = True,
        alias: str | None = None,
    ) -> None:
        terminals = {
            "y_outbound": {"io": "in"},
            "y_center": {"io": "in"},
            "y_offset": {"io": "in"},
            "data": {"io": "out"},
        }
        super().__init__(self.nodeName, terminals, render=render, alias=alias)

        self.y_outbound = OptionalDial(self, 'y_outbound', -4, 4, ElementValue(y_outbound))
        self.y_center = OptionalDial(self, 'y_center', -4, 4, ElementValue(y_center))
        self.y_offset = OptionalDial(self, 'y_offset', 0, 1, ElementValue(y_offset))
        self.cute_side_mode = EnumElement(self, 'cute_side_mode', ElementValue(cute_side_mode))
        self.length = IntegerDial(self, 'length', 1, 4096, ElementValue(length))
        self.data = AnalysableElement(self, "data", ElementValue(np.zeros(self.length.value)), y_max=max(1.0, float(np.max(self.y_outbound.value)), float(np.max(self.y_center.value))))

    def c_update(self):
        half_length = (self.length.value + 1) // 2
        half_part = np.linspace(
            self.y_outbound.value,
            self.y_center.value,
            half_length,
        ).flatten()
        mirrored = np.maximum(
            np.concatenate((half_part, half_part[::-1] if self.length.value % 2 == 0 else half_part[-2::-1])),
            0,
        )
        offsetted = np.roll(mirrored, int(float(np.asarray(self.y_offset.value).reshape(-1)[0]) * self.length.value))

        if self.cute_side_mode.value != CutSideMode.NONE:
            tray_edge_index = np.argsort(offsetted)[0 if self.cute_side_mode.value == CutSideMode.LEFT else 1]
            tray_edge_value = offsetted[tray_edge_index]
            fixed_array = np.hstack((
                np.repeat(tray_edge_value, tray_edge_index + 1 if self.cute_side_mode.value == CutSideMode.LEFT else 0),
                offsetted[tray_edge_index + 1:],
                np.repeat(tray_edge_value, 0 if self.cute_side_mode.value == CutSideMode.LEFT else tray_edge_index + 1)
            ))
            self.data.value[:] = fixed_array
            return

        self.data.value[:] = offsetted

