from frontend.components.elements.parameters import DataElement, IntegerDial
import numpy as np

from backend.updatable.updatable import AudioUpdatable
from config import CHUNK_SIZE, FFT_SIZE
from frontend.components.elements import AnalysableElement
from frontend.components.elements.element_value import ElementValue
from frontend.overrides.CNode import CNode


class BufferNode(CNode, AudioUpdatable):
    """Keep a rolling stereo audio window for FFT or other audio analysis.

    Input `indata`: array shaped (2, chunk_size), with channels first.
    Output `data`: array shaped (2, length), ordered oldest to newest.
    Each audio update appends `chunk_size` samples and discards the oldest;
    the window starts filled with zeros. Configure `chunk_size` and `length`
    in samples, with chunk_size <= length.
    """

    nodeName = "Buffer"

    def __init__(
        self,
        indata: np.ndarray = np.zeros((2, CHUNK_SIZE)),
        chunk_size: int = CHUNK_SIZE,
        length: int = FFT_SIZE,
        render: bool = True,
        alias: str | None = None,
    ) -> None:
        terminals = {
            "indata": {"io": "in"},
            "data": {"io": "out"},
        }
        super().__init__(self.nodeName, terminals, render=render, alias=alias)

        self.indata = DataElement(self, 'indata', ElementValue(indata))
        self.chunk_size = IntegerDial(self, 'chunk_size', 16, 65536, ElementValue(chunk_size))
        self.length = IntegerDial(self, 'length', 1, 4096, ElementValue(length))
        self.data = AnalysableElement(self, "data", ElementValue(np.zeros((2, self.length.value))), chart_open=False, y_min=-1.0)

        self.chunk_size.valueChanged.connect(self.on_chunk_size_change)
        self.should_process = True

    def on_chunk_size_change(self):
        self.should_process = False

        try:
            int_chunk_size = int(self.chunk_size.value)
            self.indata.value = np.hstack((
                self.indata.value[:, :int_chunk_size],
                np.zeros((2, max(0, int_chunk_size - self.indata.value.shape[1]))),
            ))
            self.data.value = np.zeros((2, self.length.value))
        except (TypeError, ValueError):
            return
        finally:
            self.should_process = True

    def c_update(self):
        self.roll()

    def roll(self):
        if not self.should_process:
            return

        chunk_size = int(self.chunk_size.value)
        self.data.value[:] = np.roll(self.data.value, -chunk_size, axis=1)
        self.data.value[:, -chunk_size:] = self.indata.value
