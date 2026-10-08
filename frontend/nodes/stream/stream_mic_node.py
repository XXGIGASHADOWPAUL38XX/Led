from typing import Callable

from backend.updatable.updatable import AudioUpdatable
from frontend.components.elements.element import Element
from frontend.components.elements.element_value import ElementValue
from frontend.overrides.CNode import CNode
from frontend.components.elements.dials.linear_dial import LinearDial

import numpy as np
import sounddevice as sd

from config import SAMPLE_RATE, CHUNK_SIZE


class StreamMicNode(CNode, AudioUpdatable):
    """Capture mono microphone blocks for audio processing.

    Output `chunk` is a 1D array of chunk_size samples, written by the device
    callback. Configure `sample_rate`, `chunk_size`, and optional
    `user_callback`; call `start()` to capture and `stop()` to release the
    device. Changing chunk size restarts an active stream."""

    nodeName = "StreamMic"

    def __init__(
        self,
        user_callback: Callable[[np.ndarray, int, object, object], None] | None = None,
        sample_rate: int = SAMPLE_RATE,
        chunk_size: int = CHUNK_SIZE,
        render: bool = True,
    ) -> None:
        terminals = {"chunk": {"io": "out"}}
        super().__init__(self.nodeName, terminals, render=render)

        self.user_callback = user_callback
        self.sample_rate = Element(self, "Sample rate", ElementValue(sample_rate))
        self.chunk_size = LinearDial(self, "Chunk size", 30, 70, value=chunk_size)
        self.chunk_size.dial.valueChanged.connect(self.on_chunk_size_changed)
        self.chunk = Element(self, "Chunk", ElementValue(np.zeros(chunk_size)))
        self.sd_stream_mic = None
        self._chunk_size_proxy = None
        self._chunk_size_proxy_pending = False

    def callback(self, indata, frames, time, status):
        self.chunk.value[:] = indata.flatten()
        if self.user_callback is not None:
            self.user_callback(indata, frames, time, status)

    def start(self):
        self.sd_stream_mic = sd.InputStream(
            callback=self.callback,
            channels=1,
            samplerate=self.sample_rate.value,
            blocksize=int(self.chunk_size.value)
        )

        self.sd_stream_mic.start()

    def stop(self):
        if self.sd_stream_mic is not None:
            self.sd_stream_mic.stop()
            self.sd_stream_mic.close()
            self.sd_stream_mic = None

    def on_chunk_size_changed(self):
        new_chunk_size = int(self.chunk_size.value)
        if self.chunk.value.shape[0] != new_chunk_size:
            self.chunk.value = np.zeros(new_chunk_size)

        if self.sd_stream_mic is not None:
            self.stop()
            self.start()


    def ctrlWidget(self):
        return None
