from backend.components.elements.parameters import Parameter, DataElement
import numpy as np

from config import FREQ_BINS

from backend.components.elements import AnalysableElement
from backend.components.elements.element_value import ElementValue
from backend.overrides.CNode import CNode
from backend.nodes.pipelines.amplitudes.amplitude_transformer import AmplitudesTransformer

class FreqScaledAmplitudesTransformerNode(CNode, AmplitudesTransformer):
    """Aggregate spectrum neighborhoods with index-dependent widths.

    Input `input_data` and output `data` are FREQ_BINS vectors. Configure
    `correlation_weight_min` to widen neighborhoods toward higher indices;
    each audio update sums values divided by normalized ramp weights, then
    applies the constructor `log` exponent. `powering` is currently unused."""

    nodeName = "FreqScaledAmplitudesTransformer"

    def __init__(
        self,
        input_data: np.ndarray = np.zeros(FREQ_BINS),
        powering: float = 1.,
        log: float = 1.,
        correlation_weight_min: int | float = 50,
        alias: str | None = None,
    ) -> None:
        terminals = {
            "input_data": {"io": "in"},
            "data": {"io": "out"},
        }

        CNode.__init__(self, self.nodeName, terminals, alias=alias, powering=powering, log=log)

        self.input_data = DataElement(self, 'input_data', ElementValue(input_data))
        self.powering = Parameter(self, 'powering', powering, minimum=0, maximum=10)
        self.log = Parameter(self, 'log', log, minimum=0.01, maximum=10)
        self.log.valueChanged.connect(self._log_changed)
        self.correlation_weight_min = Parameter(self, 'correlation_weight_min', correlation_weight_min, minimum=0.001, maximum=300)
        self.data = AnalysableElement(self, "data", ElementValue(np.zeros(FREQ_BINS)))

    def c_update(self):
        self.transform_amplitudes(self.input_data.value)

    def transform_amplitudes(self, data):
        updated_amplitudes =data

        n = updated_amplitudes.size
        radius = np.maximum(1, (np.linspace(1, self.correlation_weight_min.value, n) / 10).astype(int))

        windows = [updated_amplitudes[max(0, i - r):min(n, i + r + 1)] for i, r in enumerate(radius)]
        sizes = [x.size for x in windows]
        groups_weights_repartition = [1 + (2 * np.linspace(0, 1, s) - 1) / 2 for s in sizes]
        norm_gwr = [g / np.sum(g) for g in groups_weights_repartition]
        updated_amplitudes = np.array([np.sum(w/(g+1e-12)) for w, g in zip(windows, norm_gwr)])

        self.data.value[:] = super().transform_amplitudes(updated_amplitudes)
