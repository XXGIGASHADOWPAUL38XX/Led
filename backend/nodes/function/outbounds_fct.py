from backend.components.elements.parameters import Parameter
import numpy as np

from config import FFT_SIZE, FREQ_BINS
from backend.updatable.updatable import AudioUpdatable
from backend.components.elements import AnalysableElement
from backend.components.elements.element_value import ElementValue
from backend.enums.cut_side.cut_side_mode import CutSideMode
from backend.overrides.CNode import CNode

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
        alias: str | None = None,
    ) -> None:
        terminals = {
            "y_outbound": {"io": "in"},
            "y_center": {"io": "in"},
            "y_offset": {"io": "in"},
            "data": {"io": "out"},
        }
        super().__init__(self.nodeName, terminals, alias=alias)

        self.y_outbound = Parameter(self, 'y_outbound', y_outbound, minimum=-4, maximum=4, optional=True)
        self.y_center = Parameter(self, 'y_center', y_center, minimum=-4, maximum=4, optional=True)
        self.y_offset = Parameter(self, 'y_offset', y_offset, minimum=0, maximum=1, optional=True)
        self.cute_side_mode = Parameter(self, 'cute_side_mode', cute_side_mode, kind='enum')
        self.length = Parameter(self, 'length', length, minimum=1, maximum=4096, integer=True)
        self.data = AnalysableElement(self, "data", ElementValue(np.zeros(self.length.value)))

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

