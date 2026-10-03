import numpy as np
from pyparsing import LineEnd

from config import CHUNK_SIZE, FFT_SIZE
from backend.updatable.updatable import AudioUpdatable
from frontend.components.elements import AnalysableElement
from frontend.components.elements.element import Element
from frontend.components.elements.element_value import ElementValue
from frontend.components.elements.textedit import TextEdit
from frontend.overrides.CNode import CNode


class BufferNode(CNode, AudioUpdatable):
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

        self.indata = Element(self, "indata", ElementValue(indata))
        self.chunk_size = TextEdit(self, "chunk_size", ElementValue(chunk_size))
        self.length = Element(self, "length", ElementValue(length))
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
