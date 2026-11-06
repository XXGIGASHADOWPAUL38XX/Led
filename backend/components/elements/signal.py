"""Value notifications on the processing thread, coalesced for audio workers."""
from queue import SimpleQueue, Empty
from threading import Lock, get_ident, main_thread

_pending = SimpleQueue()
_lock = Lock()


def drain_signals():
    while True:
        try:
            signal = _pending.get_nowait()
        except Empty:
            return
        with _lock:
            args, signal._pending_args = signal._pending_args, None
        signal.emit(*args)


class Signal:
    def __init__(self):
        self._listeners = []
        self._pending_args = None

    def connect(self, callback):
        if callback not in self._listeners:
            self._listeners.append(callback)

    def disconnect(self, callback):
        self._listeners.remove(callback)

    def emit(self, *args):
        if get_ident() != main_thread().ident:
            with _lock:
                if self._pending_args is None:
                    _pending.put(self)
                self._pending_args = args
            return
        for callback in tuple(self._listeners):
            callback(*args)
