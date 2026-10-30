from backend.components.elements.parameters import Parameter, DataElement
import numpy as np

from backend.updatable.updatable import AudioUpdatable
from config import CHUNK_SIZE, FFT_SIZE
from backend.components.elements import AnalysableElement
from backend.components.elements.element_value import ElementValue
from backend.overrides.CNode import CNode

class BufferNode(CNode, AudioUpdatable):
    """Keep a rolling stereo audio window for FFT or other audio analysis.

    Input `indata`: array shaped (2, chunk_size), with channels first.
    Output `data`: array shaped (2, length), ordered oldest to newest.
    Each audio update appends the incoming samples and discards the oldest.
    Chunks longer than `length` retain only their newest samples. The window
    starts filled with zeros; `chunk_size` configures an unconnected input.
    """

    nodeName = "Buffer"

    def __init__(
        self,
        indata: np.ndarray = np.zeros((2, CHUNK_SIZE)),
        chunk_size: int = CHUNK_SIZE,
        length: int = FFT_SIZE,
        alias: str | None = None,
    ) -> None:
        terminals = {
            "indata": {"io": "in"},
            "data": {"io": "out"},
        }
        super().__init__(self.nodeName, terminals, alias=alias)

        self.indata = DataElement(self, 'indata', ElementValue(indata))
        self.chunk_size = Parameter(self, 'chunk_size', chunk_size, minimum=16, maximum=65536, integer=True)
        self.length = Parameter(self, 'length', length, minimum=1, maximum=4096, integer=True)
        self.data = AnalysableElement(self, "data", ElementValue(np.zeros((2, self.length.value))))

        self.chunk_size.valueChanged.connect(self.on_chunk_size_change)
        self.should_process = True

    def on_chunk_size_change(self, *_args):
        if self.indata._value_source is not None:
            return
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

    def validate_parameters(self, changes):
        if self.indata.value.ndim != 2 or self.indata.value.shape[0] != 2:
            raise ValueError("Buffer input must have two channels")
        if "chunk_size" in changes and self.indata._value_source is not None:
            raise ValueError("Chunk size follows the connected audio input")

    def parameters_changed(self, name):
        if name == "length":
            self.data.value = np.zeros((2, self.length.value))

    def c_update(self):
        self.roll()

    def roll(self):
        if not self.should_process:
            return

        chunk_size = min(self.indata.value.shape[1], self.data.value.shape[1])
        if chunk_size:
            self.data.value[:] = np.roll(self.data.value, -chunk_size, axis=1)
            self.data.value[:, -chunk_size:] = self.indata.value[:, -chunk_size:]
