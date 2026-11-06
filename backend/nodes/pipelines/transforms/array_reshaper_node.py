import numpy as np

from backend.components.elements import AnalysableElement
from backend.components.elements.parameters import Parameter, validate_shape
from backend.overrides.array_input_node import ArrayInputNode
from backend.updatable.updatable import AudioUpdatable


class ArrayReshaperNode(ArrayInputNode, AudioUpdatable):
    """Transform numeric input_data by slicing, reshaping, transposing, then reversing.

    Slice is a start-inclusive, end-exclusive interval along slice_axis; None
    selects the whole array. Reshape is an optional positive dimension list
    whose product must equal the sliced element count. Transpose uses the
    supplied axis permutation, or reverses all axes when transpose_axes is None.
    Reverse flips reverse_axis after transposing. Negative axes are supported.
    Input shape adapts on linking and is editable; output data owns its storage.
    Example: shape [200], slice [0,150], reshape [15,10], transpose True
    produces [10,15]. Disabled operations leave values unchanged.
    """

    nodeName = 'ArrayReshaper'

    def __init__(self, input_data=None, shape=None, slice_interval=None, slice_axis=0,
                 reshape=None, transpose=False, transpose_axes=None, reverse=False,
                 reverse_axis=0, alias=None):
        super().__init__(self.nodeName, {'input_data': {'io': 'in'}, 'data': {'io': 'out'}}, alias=alias)
        self.init_array_input('input_data', input_data, shape, (180,))
        rank = len(self.shape.value)
        extent = self.shape.value[self._axis(slice_axis, rank)]
        self.slice_interval = Parameter(self, 'slice_interval', slice_interval, kind='interval', optional=True,
                                        minimum=-extent, maximum=extent)
        self.slice_axis = Parameter(self, 'slice_axis', slice_axis, integer=True, minimum=-rank, maximum=rank - 1)
        self.reshape = Parameter(self, 'reshape', reshape, integer=True, minimum=1, maximum=65536, optional=True)
        self.transpose = Parameter(self, 'transpose', transpose, kind='boolean')
        self.transpose_axes = Parameter(self, 'transpose_axes', transpose_axes, kind='axis')
        self.reverse = Parameter(self, 'reverse', reverse, kind='boolean')
        self.reverse_axis = Parameter(self, 'reverse_axis', reverse_axis, integer=True, minimum=-16, maximum=15)
        self.validate_parameters({})
        self._transformation = self._plan({})
        self.reverse_axis.minimum = -len(self._transformation[1])
        self.reverse_axis.maximum = len(self._transformation[1]) - 1
        self.data = AnalysableElement(self, 'data', np.zeros(self.output_shape(), dtype=self.input_data.value.dtype))
        self.c_update()

    @staticmethod
    def _axis(value, rank):
        number = np.asarray(value)
        if number.ndim != 0 or number.dtype.kind not in 'iuf' or not np.isfinite(number) or number != np.floor(number) or not -rank <= number < rank:
            raise ValueError(f'Axis must be an integer between {-rank} and {rank - 1}')
        return int(value) % rank

    def _plan(self, changes):
        values = {name: changes.get(name, vars(self)[name].value) for name in
                  ('shape', 'slice_interval', 'slice_axis', 'reshape', 'transpose', 'transpose_axes', 'reverse', 'reverse_axis')}
        shape = list(validate_shape(values['shape']))
        selection = [slice(None)] * len(shape)
        axis = self._axis(values['slice_axis'], len(shape))
        interval = values['slice_interval']
        if interval is not None:
            indices = np.asarray(interval)
            if indices.shape != (2,) or indices.dtype.kind not in 'iuf' or not np.isfinite(indices).all() or np.any(indices != np.floor(indices)):
                raise ValueError('Slice requires two integer indices: start inclusive, end exclusive')
            selection[axis] = slice(int(indices[0]), int(indices[1]))
            shape[axis] = len(range(*selection[axis].indices(shape[axis])))
            if shape[axis] == 0:
                raise ValueError('Slice must select at least one element')
        target = tuple(shape) if values['reshape'] is None else validate_shape(values['reshape'])
        if np.prod(target) != np.prod(shape):
            raise ValueError('Reshape size must match the number of sliced elements')
        axes = tuple(range(len(target)))
        if values['transpose']:
            supplied = values['transpose_axes']
            if supplied is not None and np.asarray(supplied).ndim != 1:
                raise ValueError('Transpose axes must be an array of axis indices')
            axes = tuple(reversed(axes)) if supplied is None else tuple(self._axis(axis, len(target)) for axis in supplied)
            if sorted(axes) != list(range(len(target))):
                raise ValueError('Transpose axes must contain each axis exactly once')
        reverse_axis = self._axis(values['reverse_axis'], len(target))
        return tuple(selection), target, axes, reverse_axis, tuple(target[axis] for axis in axes)

    def validate_parameters(self, changes):
        super().validate_parameters(changes)
        for name in ('transpose', 'reverse'):
            valid, error = vars(self)[name].check_value(changes.get(name, vars(self)[name].value))
            if not valid:
                raise ValueError(error)
        self._plan(changes)

    def output_shape(self):
        return self._plan({})[-1]

    def parameters_changed(self, name):
        self._transformation = self._plan({})
        super().parameters_changed(name)
        self.c_update()

    def c_update(self):
        selection, shape, axes, reverse_axis, _ = self._transformation
        result = self.input_data.value[selection].reshape(shape).transpose(axes)
        if self.reverse.value:
            result = np.flip(result, axis=reverse_axis)
        if self.data.value.shape != result.shape or self.data.value.dtype != result.dtype:
            self.data.value = np.empty_like(result)
        self.data.value[:] = result
