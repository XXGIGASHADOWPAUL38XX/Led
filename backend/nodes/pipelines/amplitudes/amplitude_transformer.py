import numpy as np

from backend.updatable.updatable import AudioUpdatable

class AmplitudesTransformer(AudioUpdatable):
    def __init__(
            self,
            powering: float = 1.,
            log: float = 1.,
    ) -> None:
        super().__init__()
        self._powering = powering
        self._log = log

    def _log_changed(self, value):
        self._log = value

    def transform_amplitudes(self, data):
        updated_amplitudes = data
        updated_amplitudes = np.power(updated_amplitudes, self._log)
        data[:] = updated_amplitudes
        return data
