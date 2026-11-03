import numpy as np

from backend.pipelines.pipeline import AudioPipeline
from backend.components.elements import AnalysableElement
from backend.components.elements.parameters import DataElement
from backend.overrides.CNode import CNode

class RMSPipelineNode(CNode, AudioPipeline):
    """Measure root mean square amplitude across all audio channels and samples.

    Input `buffer_data` is channels-first audio. Output `data` is a
    one-element level array; an empty input produces zero.
    """
    nodeName = 'RMS'
    ui = {
        "title": "RMS",
        "description": "Measure overall audio level with root mean square amplitude.",
        "category": "auditory",
        "fields": [{"name": "buffer_data", "control": "port"}],
        "views": [{"kind": "meter", "data": "data", "label": "RMS", "open": True}],
    }

    def __init__(self, buffer_data=np.zeros((2, 0)), alias=None):
        super().__init__(self.nodeName, {'buffer_data': {'io': 'in'}, 'data': {'io': 'out'}}, alias=alias)
        self.buffer_data = DataElement(self, 'buffer_data', buffer_data)
        self.data = AnalysableElement(self, 'data', np.zeros(1))

    def c_update(self):
        self.data.value[...] = np.sqrt(np.mean(self.buffer_data.value ** 2)) if self.buffer_data.value.size else 0.0
