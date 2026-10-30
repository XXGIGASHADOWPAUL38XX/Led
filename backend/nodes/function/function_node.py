from backend.components.elements.parameters import Parameter, ArrayElement, DataElement
import numpy as np

from config import FREQ_BINS
from backend.components.elements.analysable_element import AnalysableElement
from backend.components.elements.element_value import ElementValue
from backend.overrides.CNode import CNode

def normalized_points(points) -> np.ndarray:
    points = np.asarray(points if points is not None else (), dtype=float).reshape(-1, 2)
    points = np.vstack((points, [[0.0, 0.0], [1.0, 1.0]]))
    points = np.clip(points, 0.0, 1.0)
    points = points[np.argsort(points[:, 0])]
    _, indices = np.unique(points[:, 0], return_index=True)
    return points[np.sort(indices)]

class FunctionNode(CNode):
    """Generate an editable piecewise-linear spatial curve.

    Inputs `input_data` and `number_points` determine the output `data` shape;
    input_data values are not transformed. Configure normalized (x, y)
    `points`. With an array input, the curve spans its first axis and repeats
    across trailing dimensions; otherwise it is a number_points vector.
    Regenerates on input changes or accepted curve edits."""

    nodeName = "Function"

    def __init__(
        self,
        input_data: np.ndarray | None = None,
        number_points: int = FREQ_BINS,
        points: list[tuple[float, float]] | np.ndarray | None = None,
        alias: str | None = None,
    ) -> None:
        super().__init__(
            self.nodeName,
            {"input_data": {"io": "in"}, "number_points": {"io": "in"}, "data": {"io": "out"}},

            alias=alias,
        )
        self.input_data = DataElement(self, 'input_data', ElementValue(input_data))
        self.number_points = Parameter(self, 'number_points', number_points, minimum=1, maximum=4096, integer=True)
        self.points = ArrayElement(self, 'points', ElementValue(normalized_points(points)), min_value=0, max_value=1)
        self.data = AnalysableElement(self, "data", ElementValue(np.zeros(self._data_shape())))

        self.points.valueChanged.connect(self._refresh_data)
        self.number_points.valueChanged.connect(self._refresh_data)
        self.input_data.valueChanged.connect(self._refresh_data)
        self._refresh_data()

    def _refresh_data(self, *_args) -> None:
        shape = self._data_shape()
        size = shape[0] if shape else 0
        points = normalized_points(self.points.value)
        data = np.interp(np.linspace(0.0, 1.0, size), points[:, 0], points[:, 1])
        self.data.value = np.broadcast_to(data.reshape(-1, *([1] * (len(shape) - 1))), shape).copy()

    def _data_shape(self) -> tuple[int, ...]:
        input_data = self.input_data.value
        if isinstance(input_data, np.ndarray):
            return input_data.shape
        return (max(0, int(self.number_points.value)),)
