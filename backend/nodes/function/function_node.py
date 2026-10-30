from backend.components.elements.parameters import Parameter, ArrayElement, DataElement, SequenceElement, ReferenceElement
import numpy as np

from config import FREQ_BINS
from backend.components.elements.analysable_element import AnalysableElement
from backend.components.elements.element_value import ElementValue
from backend.overrides.CNode import CNode


def normalized_points(points) -> np.ndarray:
    points = np.asarray(points if points is not None else (), dtype=float).reshape(-1, 2)
    points = np.vstack((points, [[0.0, 0.0], [1.0, 1.0]]))
    points = np.clip(points, 0.0, 1.0)
    points = points[np.argsort(points[:, 0], kind='stable')]
    _, indices = np.unique(points[:, 0], return_index=True)
    return points[np.sort(indices)]


class FunctionNode(CNode):
    """Generate a spatial curve with connectable coordinates and segment bends.

    `points` contains normalized (x, y) pairs, `slopes` one bend per segment
    in [-1, 1] (0 = linear, bounded quadratic easing), and `point_ids` stable point identifiers. Inputs
    `point_<id>_x`, `point_<id>_y`, and `point_<id>_slope` accept one-element
    arrays; linked coordinates are clamped to [0, 1] and remain ordered.
    `controls` persists those source references. Input `input_data` supplies
    the output shape, not its values; otherwise `number_points` sets length.
    Output `data` regenerates when controls or linked values change."""

    nodeName = 'Function'

    def __init__(self, input_data: np.ndarray | None = None, number_points: int = FREQ_BINS,
                 points=None, slopes=None, point_ids=None, controls=None, alias: str | None = None):
        super().__init__(self.nodeName, {'input_data': {'io': 'in'}, 'number_points': {'io': 'in'}, 'data': {'io': 'out'}}, alias=alias)
        points = normalized_points(points) if point_ids is None else np.asarray(points, dtype=float)
        if points.ndim != 2 or points.shape[1] != 2 or len(points) < 2 or not np.isfinite(points).all() or np.any((points < 0) | (points > 1)) or np.any(np.diff(points[:, 0]) <= 0):
            raise ValueError('Provide ordered points in [0, 1] with distinct x coordinates')
        count = len(points)
        ids = list(point_ids) if point_ids is not None else [f'p{i}' for i in range(count)]
        slopes = np.zeros(count - 1) if slopes is None else np.asarray(slopes, dtype=float)
        if len(ids) != count or len(set(ids)) != count or any(type(id) is not str or not id for id in ids):
            raise ValueError('Provide a unique ID for each point')
        if slopes.shape != (count - 1,) or not np.isfinite(slopes).all() or np.any(np.abs(slopes) > 1):
            raise ValueError('Provide one slope in [-1, 1] per segment')
        self.input_data = DataElement(self, 'input_data', ElementValue(input_data))
        self.number_points = Parameter(self, 'number_points', number_points, minimum=1, maximum=4096, integer=True)
        self.points = ArrayElement(self, 'points', points, min_value=0, max_value=1)
        self.slopes = ArrayElement(self, 'slopes', slopes, min_value=-1, max_value=1)
        self.point_ids = SequenceElement(self, 'point_ids', ids)
        self.controls = ReferenceElement(self, 'controls', controls or {})
        self.data = AnalysableElement(self, 'data', np.zeros(self._data_shape()))
        for i, id in enumerate(ids):
            values = {'x': points[i, 0], 'y': points[i, 1]}
            if i < count - 1:
                values['slope'] = slopes[i]
            for axis, value in values.items():
                name = f'point_{id}_{axis}'
                element = DataElement(self, name, self.controls.value.get(name, np.array([value], dtype=float)))
                if np.shape(element.value) != (1,) or not np.isfinite(element.value).all():
                    raise ValueError('Curve controls require one finite value')
                vars(self)[name] = element
                self.pending_terminals[name] = {'io': 'in'}
                element.valueChanged.connect(self._refresh_data)
        if self.controls.value.keys() - self.pending_terminals.keys():
            raise ValueError('Unknown curve control')
        self.number_points.valueChanged.connect(self._refresh_data)
        self.input_data.valueChanged.connect(self._refresh_data)
        self.points.valueChanged.connect(self._refresh_data)
        self.slopes.valueChanged.connect(self._refresh_data)
        self._refresh_data()

    def connect_input(self, name, source, parameters):
        if name.startswith('point_'):
            parameters.setdefault('controls', {})[name] = source
            return name, {}
        return super().connect_input(name, source, parameters)

    def disconnect_input(self, name, parameters):
        if name.startswith('point_'):
            parameters.setdefault('controls', {}).pop(name, None)
            return ()
        return super().disconnect_input(name, parameters)

    def _refresh_data(self, *_args):
        points = np.array(self.points.value)
        slopes = np.array(self.slopes.value)
        count = len(points)
        epsilon = 1e-6
        for i, id in enumerate(self.point_ids):
            x = self._control(f'point_{id}_x', points[i, 0])
            y = self._control(f'point_{id}_y', points[i, 1])
            low = points[i - 1, 0] + epsilon if i else 0
            high = 1 - (count - 1 - i) * epsilon
            points[i] = [np.clip(x, low, high), np.clip(y, 0, 1)]
            if i < count - 1:
                slopes[i] = np.clip(self._control(f'point_{id}_slope', slopes[i]), -1, 1)
        shape = self._data_shape()
        x = np.linspace(0, 1, shape[0])
        segment = np.clip(np.searchsorted(points[:, 0], x, side='right') - 1, 0, count - 2)
        start, end = points[segment], points[segment + 1]
        t = np.clip((x - start[:, 0]) / (end[:, 0] - start[:, 0]), 0, 1)
        t = t - slopes[segment] * t * (1 - t)
        data = start[:, 1] + (end[:, 1] - start[:, 1]) * t
        self.data.value = np.broadcast_to(data.reshape(-1, *([1] * (len(shape) - 1))), shape).copy()

    def _control(self, name, fallback):
        element = vars(self)[name]
        return float(element.value[0]) if element._value_source is not None else fallback

    def _data_shape(self):
        data = self.input_data.value
        return data.shape if isinstance(data, np.ndarray) else (int(self.number_points.value),)
