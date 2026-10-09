from frontend.components.elements.parameters import DataElement, IntegerDial, ReferenceElement
import threading
from typing import Callable

import numpy as np
import sounddevice as sd

from config import CHUNK_SIZE, SAMPLE_RATE
from backend.updatable.updatable import AudioUpdatable
from frontend.components.elements.element_value import ElementValue
from frontend.overrides.CNode import CNode


class StreamPlayerNode(CNode, AudioUpdatable):
    """Play stereo audio and expose channels-first blocks for analysis.

    Inputs `audio_in` shaped (samples, 2), `sample_rate_in` (Hz), and
    `enqueue_token` replace playback when the token changes. Output `chunk`
    has shape (2, chunk_size). Empty audio stops playback. Configure
    `chunk_size`; direct `enqueue()` appends tracks with matching sample rates."""

    nodeName = "StreamPlayer"

    def __init__(
        self,
        audio_in: np.ndarray = np.zeros((0, 2), dtype=np.float32),
        sample_rate_in: int = SAMPLE_RATE,
        enqueue_token: int = 0,
        sample_rate: int = SAMPLE_RATE,
        chunk_size: int = CHUNK_SIZE,
        render: bool = True,
        alias: str | None = None,
        user_callback: Callable[[np.ndarray, int, object, object], None] | None = None
    ) -> None:
        terminals = {
            "audio_in": {"io": "in"},
            "sample_rate_in": {"io": "in"},
            "enqueue_token": {"io": "in"},
            "chunk": {"io": "out"},
        }
        super().__init__(self.nodeName, terminals=terminals, render=render, alias=alias)
        self.audio_in = DataElement(self, 'audio_in', ElementValue(audio_in))
        self.sample_rate_in = DataElement(self, 'sample_rate_in', ElementValue(sample_rate_in))
        self.enqueue_token = DataElement(self, 'enqueue_token', ElementValue(enqueue_token))
        self.sample_rate = IntegerDial(self, 'sample_rate', 8000, 192000, ElementValue(sample_rate))
        self.chunk_size = IntegerDial(self, 'chunk_size', 16, 65536, ElementValue(chunk_size))
        self.chunk = DataElement(self, 'chunk', ElementValue(np.zeros((2, chunk_size), dtype=np.float32)))
        self.user_callback = ReferenceElement(self, "user_callback", user_callback, link_terminal=False)
        self._last_enqueue_token = int(self.enqueue_token.value)

        self._lock = threading.Lock()
        self._audio = np.zeros((0, 2), dtype=np.float32)
        self._song_ends = []
        self._cursor = 0
        self._stream = None
        self._running = False

    def enqueue(self, audio, sr):
        arr = np.asarray(audio, dtype=np.float32)
        with self._lock:
            if self._audio.shape[0] == 0:
                self.sample_rate.value = int(sr)
            elif int(sr) != int(self.sample_rate.value):
                raise ValueError("sample rate mismatch")
            self._audio = np.vstack((self._audio, arr))
            self._song_ends.append(self._audio.shape[0])

    def remaining_seconds_to_song_end(self):
        with self._lock:
            for end in self._song_ends:
                if self._cursor < end:
                    return (end - self._cursor) / float(self.sample_rate.value)
        return None

    def _callback(self, outdata, frames, time, status):
        with self._lock:
            end = min(self._cursor + frames, self._audio.shape[0])
            take = max(0, end - self._cursor)
            outdata[:] = 0
            if take > 0:
                outdata[:take] = self._audio[self._cursor:end]
                block = outdata[:take].T
                chunk_len = self.chunk.value.shape[1]
                if block.shape[1] < chunk_len:
                    block = np.pad(block, ((0, 0), (0, chunk_len - block.shape[1])))
                elif block.shape[1] > chunk_len:
                    block = block[:, :chunk_len]
                self.chunk.value[:] = block
            self._cursor = end

        if self.user_callback.value:
            self.user_callback.value(outdata, frames, time, status)

    def start(self):
        if self._running:
            return
        self._stream = sd.OutputStream(
            callback=self._callback,
            samplerate=int(self.sample_rate.value),
            channels=2,
            dtype="float32",
            blocksize=int(self.chunk.value.shape[1]),
        )
        self._stream.start()
        self._running = True

    def stop(self):
        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
            self._stream = None
        self._running = False

    def c_update(self):
        token = int(self.enqueue_token.value)
        if token != self._last_enqueue_token:
            self.stop()
            arr = np.asarray(self.audio_in.value, dtype=np.float32)
            with self._lock:
                self._audio = np.zeros((0, 2), dtype=np.float32)
                self._song_ends = []
                self._cursor = 0
            if arr.shape[0] > 0:
                self.enqueue(arr, self.sample_rate_in.value)
                self.start()
            else:
                self.chunk.value[:] = 0
            self._last_enqueue_token = token
        return self.chunk
