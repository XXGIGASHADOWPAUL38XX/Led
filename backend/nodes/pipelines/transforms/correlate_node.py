import numpy as np
from scipy.ndimage import convolve1d

from config import FREQ_BINS
from backend.components.elements import AnalysableElement
from backend.components.elements.parameters import Parameter
from backend.overrides.array_input_node import ArrayInputNode
from backend.updatable.updatable import AudioUpdatable


class CorrelateNode(ArrayInputNode, AudioUpdatable):
    """Combine neighboring rows using triangular weights.

    `input_data` adopts its source shape; editable `shape` must match connected
    data. Output `data` preserves every dimension. `correlation_step` is the
    total span as a fraction of the first axis: 0.1 over 180 rows spans 18
    positions, 9 per side. `correlation_offset` scales neighboring weights
    from 0 to 1. `mode` selects maximum spreading (preserving original peaks)
    or average (normalized weighted blending, including at array boundaries).
    RGB/RGBA channels are processed independently along the first axis.
    Zero step or strength preserves the input.
    """

    nodeName = 'Correlate'

    def __init__(self, input_data=None, correlation_offset=1., correlation_step=0., shape=None, alias=None, mode='maximum'):
        super().__init__(self.nodeName, {'input_data': {'io': 'in'}, 'data': {'io': 'out'},
                                       'correlation_offset': {'io': 'in'}, 'correlation_step': {'io': 'in'}}, alias=alias)
        self.init_array_input('input_data', input_data, shape, (FREQ_BINS,))
        self.correlation_offset = Parameter(self, 'correlation_offset', correlation_offset, minimum=0, maximum=1)
        self.correlation_step = Parameter(self, 'correlation_step', correlation_step, minimum=0, maximum=1)
        self.mode = Parameter(self, 'mode', mode, kind='choice', choices=('maximum', 'average'))
        self.data = AnalysableElement(self, 'data', np.zeros(self.shape.value))

    def c_update(self):
        source = self.input_data.value
        strength = float(np.asarray(self.correlation_offset.value).reshape(-1)[0])
        span = float(np.asarray(self.correlation_step.value).reshape(-1)[0]) * source.shape[0] / 2
        radius = min(int(np.ceil(span)) - 1, source.shape[0] - 1)
        self.data.value[:] = source
        if strength == 0 or radius < 1:
            return
        if self.mode.value == 'average':
            weights = strength * np.maximum(1 - np.abs(np.arange(-radius, radius + 1)) / span, 0)
            weights[radius] = 1
            totals = convolve1d(np.ones(source.shape[0]), weights, mode='constant')
            convolve1d(source, weights, axis=0, mode='constant', output=self.data.value)
            self.data.value[:] /= totals.reshape((-1,) + (1,) * (source.ndim - 1))
            return
        for distance in range(1, radius + 1):
            weight = strength * max(1 - distance / max(span, 1), 0)
            np.maximum(self.data.value[distance:], source[:-distance] * weight, out=self.data.value[distance:])
            np.maximum(self.data.value[:-distance], source[distance:] * weight, out=self.data.value[:-distance])
