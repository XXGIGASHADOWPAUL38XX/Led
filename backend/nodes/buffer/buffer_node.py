from backend.components.elements.parameters import DataElement, Parameter, validate_shape
import numpy as np

from backend.updatable.updatable import AudioUpdatable
from config import CHUNK_SIZE, FFT_SIZE
from backend.components.elements import AnalysableElement
from backend.overrides.array_input_node import ArrayInputNode


class BufferNode(ArrayInputNode, AudioUpdatable):
    """Keep a rolling array of samples along the last axis.

    Input `indata` adopts its source's shape on connection; `shape` is also
    editable and must match connected data. Output `data` has shape
    (*shape[:-1], length), oldest to newest. Mono and multichannel arrays
    are supported. Chunks longer than length retain their newest samples.
    Optional `frame_id` appends each source block only once, even when graph
    ticks run faster than the audio callback. Legacy `chunk_size` sets the
    last input dimension when unconnected.
    """

    nodeName = 'Buffer'
    ui = {'title': 'Buffer',
     'description': 'Keep a rolling mono or multichannel audio window; input shape adapts when linked.',
     'category': 'buffer',
     'fields': [{'name': 'frame_id', 'control': 'port', 'label': 'Frame ID'},
                {'name': 'indata', 'control': 'port'},
                {'name': 'shape', 'control': 'shape', 'label': 'Input shape', 'rebuild': True},
                {'name': 'chunk_size', 'control': 'slider', 'rebuild': True, 'hidden': True},
                {'name': 'length', 'control': 'slider', 'rebuild': True}],
     'views': [{'kind': 'bars', 'data': 'data', 'label': 'Data', 'open': True}]}
    input_shapes = {'frame_id': (1,)}

    def __init__(self, indata=None, chunk_size=CHUNK_SIZE, length=FFT_SIZE,
                 alias: str | None = None, shape=None, frame_id=None):
        super().__init__(self.nodeName, {'indata': {'io': 'in'}, 'frame_id': {'io': 'in'}, 'data': {'io': 'out'}}, alias=alias)
        self.frame_id = DataElement(self, 'frame_id', frame_id)
        self._last_frame = None
        self.length = Parameter(self, 'length', length, minimum=1, maximum=65536, integer=True)
        self.init_array_input('indata', indata, shape, (2, chunk_size))
        self.chunk_size = Parameter(self, 'chunk_size', self.shape.value[-1], minimum=1, maximum=65536, integer=True)
        self.validate_parameters({})
        self.data = AnalysableElement(self, 'data', np.zeros(self.output_shape()))
        self.chunk_size.valueChanged.connect(self.on_chunk_size_change)

    def output_shape(self):
        return (*self.shape.value[:-1], int(self.length.value))

    def validate_parameters(self, changes):
        super().validate_parameters(changes)
        shape = validate_shape(changes.get('shape', self.shape.value))
        validate_shape((*shape[:-1], int(changes.get('length', self.length.value))))
        if 'chunk_size' in changes and self.indata._value_source is not None:
            raise ValueError('Chunk size follows the connected audio input')

    def on_chunk_size_change(self, *_args):
        if self.indata._value_source is None and self.shape.value[-1] != self.chunk_size.value:
            self.shape.value = (*self.shape.value[:-1], int(self.chunk_size.value))
            super().parameters_changed('shape')

    def parameters_changed(self, name):
        super().parameters_changed(name)
        if name == 'shape':
            self.chunk_size.value = self.shape.value[-1]
        elif name == 'length':
            self.data.value = np.zeros(self.output_shape())

    def c_update(self):
        if self.frame_id.value is not None:
            current = int(np.asarray(self.frame_id.value).item())
            if current == self._last_frame:
                return
            self._last_frame = current
        self.roll()

    def roll(self):
        size = min(self.indata.value.shape[-1], self.data.value.shape[-1])
        self.data.value[...] = np.roll(self.data.value, -size, axis=-1)
        self.data.value[..., -size:] = self.indata.value[..., -size:]
