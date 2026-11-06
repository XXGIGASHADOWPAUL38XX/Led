from backend.components.elements.parameters import Parameter, NodeReferenceElement
import numpy as np

from backend.components.elements import AnalysableElement
from backend.components.elements.element_value import ElementValue
from backend.overrides.CNode import CNode
from backend.overrides.point_count_node import PointCountNode
from backend.nodes.pipelines.amplitudes.amplitude_transformer import AmplitudesTransformer

class FctAmplitudesTransformerNode(PointCountNode, AmplitudesTransformer):
    """Shape a spectrum with a supplied amplitude-level function.

    Input `input_data` is a number_points vector; configure `amplitudes_level_fct`
    with an object exposing `fct(data)`. Output `data` applies that function
    then the constructor `log` exponent each audio update. The inherited
    transform mutates the function result; `powering` is currently unused."""

    # Point count follows newly connected spectra and remains editable.
    nodeName = "FctAmplitudesTransformer"
    ui = {'title': 'Fct Amplitudes Transformer',
     'description': 'Shape a spectrum with a supplied amplitude-level function.',
     'category': 'amplitudes',
     'fields': [{'name': 'number_points', 'control': 'slider', 'label': 'Points', 'rebuild': True},
                {'name': 'input_data', 'control': 'port'},
                {'name': 'powering', 'control': 'slider', 'label': 'Weighting'},
                {'name': 'log', 'control': 'slider'},
                {'name': 'amplitudes_level_fct',
                 'control': 'node-reference',
                 'matchInput': 'input_data',
                 'nodeTypes': ['AmplitudeLevelFunction']}],
     'views': [{'kind': 'bars', 'data': 'data', 'label': 'Data', 'open': True}]}

    def __init__(
        self,
        input_data: np.ndarray | None = None,
        powering: float = 1.,
        log: float = 1.,
        amplitudes_level_fct: object = None,
        number_points: int | None = None,

    ) -> None:
        terminals = {
            "input_data": {"io": "in"},
            "data": {"io": "out"},
        }
        CNode.__init__(self, self.nodeName, terminals, powering=powering, log=log)

        self.init_points(number_points, input_data=(input_data, ()))
        self.powering = Parameter(self, 'powering', powering, minimum=0, maximum=10)
        self.log = Parameter(self, 'log', log, minimum=0.01, maximum=10)
        self.log.valueChanged.connect(self._log_changed)
        self.amplitudes_level_fct = NodeReferenceElement(self, 'amplitudes_level_fct', amplitudes_level_fct)
        self.data = AnalysableElement(self, "data", ElementValue(np.zeros(int(self.number_points.value))))

    def c_update(self):
        if self.amplitudes_level_fct.value is None:
            return self.data
        self.transform_amplitudes(self.input_data.value)

    def validate_parameters(self, changes):
        super().validate_parameters(changes)
        function = self.amplitudes_level_fct.value
        if function is not None and function.data.value.shape != self.input_data.value.shape:
            raise ValueError("The amplitude function and input must have matching lengths")

    def transform_amplitudes(self, data):
        updated_amplitudes = data

        updated_amplitudes = self.amplitudes_level_fct.value.fct(updated_amplitudes)

        self.data.value[:] = super().transform_amplitudes(updated_amplitudes)
