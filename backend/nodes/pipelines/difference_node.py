import numpy as np

from config import FREQ_BINS
from backend.components.elements.parameters import DataElement
from backend.components.elements.analysable_element import AnalysableElement
from backend.overrides.CNode import CNode
from backend.updatable.updatable import AudioUpdatable

class DifferenceNode(CNode, AudioUpdatable):
    """Subtract matching vectors and clip their difference to [0, 1].

    Inputs `a` and `b` default to zero vectors. Output `diff` retains the
    original clipped subtraction on every audio update.
    """
    nodeName = 'Difference'

    def __init__(self, a=np.zeros(FREQ_BINS), b=np.zeros(FREQ_BINS), alias=None):
        CNode.__init__(self, self.nodeName, {'a': {'io': 'in'}, 'b': {'io': 'in'}, 'diff': {'io': 'out'}}, alias=alias)
        self.a = DataElement(self, 'a', a)
        self.b = DataElement(self, 'b', b)
        self.diff = AnalysableElement(self, 'diff', np.zeros_like(self.a.value))

    def c_update(self):
        self.diff.value[:] = np.clip(self.a.value - self.b.value, 0, 1)
        return self.diff
