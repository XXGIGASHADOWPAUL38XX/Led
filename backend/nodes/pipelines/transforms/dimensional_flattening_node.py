from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
from scipy.optimize import nnls
from sklearn.decomposition import NMF

from backend.components.elements import AnalysableElement
from backend.components.elements.parameters import DataElement, Parameter, validate_shape
from backend.overrides.array_input_node import ArrayInputNode
from backend.updatable.updatable import AudioUpdatable


class DimensionalFlatteningNode(ArrayInputNode, AudioUpdatable):
    """Represent a live feature array by a configurable NMF coordinate vector.

    `input_data` adopts its source shape and is flattened to one feature vector
    per update. At least two features are required. Collect `calibration_samples`
    distinct consecutive finite vectors, then fit `dimensions` NMF components in a
    background worker. Calibration minima/ranges normalize feature units;
    values below those minima are clamped to zero, so signed inputs are valid.
    Components have unit length and remain fixed until recalibration or an
    input/configuration change. Each update solves nonnegative least squares
    against that fixed basis. `data` is (1, dimensions); scalar outputs are
    `x`, `y`, `z` (when present), then `dimension_4`, etc. `xy` always contains
    the first two coordinates, for stable 2D consumers. Outputs start at zero;
    `calibration` is [progress 0..1, ready 0/1]. Constant features use scale 1. Deterministic
    initialization keeps repeated calibration reproducible.
    Optional `model_path` loads saved minimum/scale/components arrays from an
    NPZ file at real initialization, skipping live calibration. Relative paths
    resolve from the project root. Saved models must match features and dimensions.
    Changing dimensions clears the old model path and recalibrates. The frontend
    uses an XY plot, a rotatable XYZ plot, or the shared axis grid for 4+ dimensions.
    """

    nodeName = 'DimensionalFlattening'

    def __init__(self, input_data=None, calibration_samples=200, shape=None, alias=None, model_path='', dimensions=2):
        super().__init__(self.nodeName, {'input_data': {'io': 'in'}, 'data': {'io': 'out'},
                                       'xy': {'io': 'out'},
                                       'calibration': {'io': 'out'}}, alias=alias)
        self.init_array_input('input_data', input_data, shape, (12,))
        self.calibration_samples = Parameter(self, 'calibration_samples', calibration_samples,
                                             minimum=4, maximum=4096, integer=True)
        self.model_path = Parameter(self, 'model_path', model_path, kind='text')
        self.dimensions = Parameter(self, 'dimensions', dimensions, minimum=2,
                                    maximum=min(int(np.prod(self.shape.value)), calibration_samples), integer=True)
        self.validate_parameters({})
        self.data = AnalysableElement(self, 'data', np.zeros(self.output_shape()))
        self.xy = DataElement(self, 'xy', self.data.value[:, :2])
        self.coordinates = []
        self._resize_outputs()
        self.data.valueChanged.connect(self._publish_coordinates)
        self.calibration = AnalysableElement(self, 'calibration', np.zeros(2))
        self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix='NMF')
        self.future = None
        self.recalibrate()

    def validate_parameters(self, changes):
        super().validate_parameters(changes)
        size = np.prod(validate_shape(changes.get('shape', self.shape.value)), dtype=object)
        count = changes.get('calibration_samples', self.calibration_samples.value)
        dimensions = changes.get('dimensions', self.dimensions.value)
        if size < 2 or size * count > 4_194_304:
            raise ValueError('NMF requires at least two features and at most 4,194,304 calibration values')
        if dimensions != int(dimensions) or not 2 <= dimensions <= min(size, count):
            raise ValueError('Dimensions must be an integer between 2 and the smaller of feature count and calibration samples')

    def output_shape(self):
        return (1, int(self.dimensions.value))

    @staticmethod
    def coordinate_name(index):
        return ('x', 'y', 'z')[index] if index < 3 else f'dimension_{index + 1}'

    def _resize_outputs(self):
        if self.data.value.shape != self.output_shape():
            self.data.value = np.zeros(self.output_shape())
        self.xy.value = self.data.value[:, :2]
        count = int(self.dimensions.value)
        for element in self.coordinates[count:]:
            element.close()
            self.elements.remove(element)
            del self.pending_terminals[element.name], vars(self)[element.name]
        self.coordinates = self.coordinates[:count]
        for i in range(count):
            if i < len(self.coordinates):
                self.coordinates[i].value = self.data.value[:, i]
            else:
                name = self.coordinate_name(i)
                element = DataElement(self, name, self.data.value[:, i])
                vars(self)[name] = element
                self.coordinates.append(element)
                self.pending_terminals[name] = {'io': 'out'}

    def _publish_coordinates(self, _value):
        for element in (self.xy, *self.coordinates):
            element.valueChanged.emit(element.value)

    def configure_graph(self, graph, parameters):
        dimensions = parameters.get('dimensions', 2)
        if dimensions != self.dimensions.value:
            removed = {element.name for element in self.coordinates[int(dimensions):]}
            if any(edge['source']['nodeId'] == self.name() and edge['source']['element'] in removed for edge in graph['connections']):
                raise ValueError('Disconnect removed coordinate outputs before reducing dimensions')
            if parameters.get('model_path', '') == self.model_path.value:
                parameters['model_path'] = ''

    def initialize(self):
        if self.model_path.value:
            path = Path(self.model_path.value).expanduser()
            if not path.is_absolute():
                path = Path(__file__).resolve().parents[4] / path
            with np.load(path, allow_pickle=False) as saved:
                minimum, scale, components = (np.array(saved[key], dtype=float) for key in ('minimum', 'scale', 'components'))
            size = np.prod(self.shape.value)
            if (minimum.shape != (size,) or scale.shape != (size,) or components.shape != (self.dimensions.value, size)
                    or not all(np.isfinite(value).all() for value in (minimum, scale, components))
                    or np.any(scale <= 0) or np.any(components < 0)):
                raise ValueError('Saved NMF model must contain finite, compatible minimum/scale/components arrays')
            self.recalibrate()
            self.model = minimum, scale, components
            self.calibration.value[:] = 1

    def parameters_changed(self, name):
        if name == 'shape' and self._placeholder and self.input_data._value_source is None:
            self.input_data.value = np.zeros(self.shape.value)
        if name in {'shape', 'calibration_samples'}:
            self.dimensions.maximum = min(int(np.prod(self.shape.value)), int(self.calibration_samples.value))
        if name == 'dimensions':
            self.model_path.value = ''
            self._resize_outputs()
        if name in {'shape', 'calibration_samples', 'model_path', 'dimensions'}:
            self.recalibrate()
        if name in {'shape', 'model_path'}:
            self.initialize()

    def recalibrate(self):
        if self.future is not None:
            self.future.cancel()
        self.samples, self.previous, self.model = [], None, None
        self.future = None
        self.data.value[:] = 0
        self.calibration.value[:] = 0

    @staticmethod
    def fit(samples, max_iter=1000, dimensions=2):
        minimum, scale = samples.min(axis=0), np.ptp(samples, axis=0)
        scale = np.where(scale > 1e-12, scale, 1.)
        model = NMF(n_components=dimensions, init='nndsvda', random_state=0, max_iter=max_iter)
        model.fit((samples - minimum) / scale)
        components = model.components_
        components /= np.maximum(np.linalg.norm(components, axis=1, keepdims=True), 1e-12)
        return minimum, scale, components

    def c_update(self):
        vector = np.asarray(self.input_data.value, dtype=float).reshape(-1)
        if not np.isfinite(vector).all():
            return
        if self.future is not None:
            if not self.future.done():
                return
            self.model = self.future.result()
            self.future = None
            self.samples.clear()
            self.calibration.value[:] = 1
        if self.model is None:
            if self.previous is not None and np.array_equal(vector, self.previous):
                return
            self.previous = vector.copy()
            self.samples.append(self.previous)
            self.calibration.value[0] = len(self.samples) / self.calibration_samples.value
            if len(self.samples) == self.calibration_samples.value:
                self.future = self.executor.submit(self.fit, np.asarray(self.samples), dimensions=int(self.dimensions.value))
            return
        minimum, scale, components = self.model
        self.data.value[0] = nnls(components.T, np.maximum((vector - minimum) / scale, 0))[0]

    def close(self):
        self.executor.shutdown(wait=False, cancel_futures=True)
        super().close()
