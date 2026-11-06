import numpy as np

from backend.components.elements import AnalysableElement
from backend.overrides.array_input_node import ArrayInputNode
from backend.updatable.updatable import AudioUpdatable


class CosineAngleNode(ArrayInputNode, AudioUpdatable):
    """Convert rows of XY coordinates into direction angles on a unit circle.

    `input_data` must have shape (N, 2); its editable `shape` adapts on linking.
    Output `data` has shape (N,), in radians [-pi, pi], computed with atan2(y, x).
    Zero radians points right; positive angles turn counterclockwise. Magnitude
    has no effect. The origin uses angle 0 by convention. The frontend plots
    every angle at (cos(angle), sin(angle)), always one unit from the center.
    Connect DimensionalFlattening.data directly to analyze its 2D direction.
    """

    nodeName = 'CosineAngle'
    ui = {'title': 'Cosine Angle',
     'description': 'Convert (N, 2) XY coordinates to angles in radians. Display each direction on a circle of '
                    'radius 1; the origin uses angle 0.',
     'category': 'transforms',
     'fields': [{'name': 'input_data', 'control': 'port', 'label': 'XY coordinates'},
                {'name': 'shape', 'control': 'shape', 'label': 'Input shape', 'rebuild': True}],
     'views': [{'kind': 'angle', 'data': 'data', 'label': 'Direction', 'unit': 'rad', 'open': True}]}
    input_shapes = {'input_data': (0, 2)}

    def __init__(self, input_data=None, shape=None, alias=None):
        super().__init__(self.nodeName, {'input_data': {'io': 'in'}, 'data': {'io': 'out'}}, alias=alias)
        self.init_array_input('input_data', input_data, shape, (1, 2))
        self.validate_parameters({})
        self.data = AnalysableElement(self, 'data', np.zeros(self.output_shape()))
        self.c_update()

    def validate_parameters(self, changes):
        super().validate_parameters(changes)
        shape = changes.get('shape', self.shape.value)
        if len(shape) != 2 or shape[1] != 2:
            raise ValueError('Cosine Angle requires an (N, 2) array of XY coordinates')

    def output_shape(self):
        return (self.shape.value[0],)

    def c_update(self):
        x, y = self.input_data.value.T
        np.arctan2(y, x, out=self.data.value)
        self.data.value[(x == 0) & (y == 0)] = 0
