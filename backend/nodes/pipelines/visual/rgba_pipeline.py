from backend.components.elements.parameters import DataElement
import numpy as np

from backend.pipelines.pipeline import VisualPipeline
from backend.components.elements.element_value import ElementValue
from backend.overrides.CNode import CNode
from backend.overrides.point_count_node import PointCountNode

class RGBAPipelineNode(VisualPipeline, PointCountNode):
    """Combine per-position RGB colors and normalized opacity.

    Inputs `rgb` shaped (number_points, 3) in [0, 255] and `alpha` shaped
    (number_points,) in [0, 1] produce `rgba` shaped (number_points, 4) each visual
    update. Alpha is multiplied by 255; values are not clipped."""

    nodeName = "RGBAPipeline"
    ui = {'title': 'RGBAPipeline',
     'description': 'Combine per-position RGB colors and normalized opacity.',
     'category': 'visual',
     'fields': [{'name': 'number_points', 'control': 'slider', 'label': 'Points', 'rebuild': True},
                {'name': 'rgb', 'control': 'port'},
                {'name': 'alpha', 'control': 'port'}],
     'views': [{'kind': 'color', 'data': 'rgba', 'label': 'Rgba', 'open': True}]}

    def __init__(
        self,
        rgb: np.ndarray | None = None,
        alpha: np.ndarray | None = None,
        alias: str | None = None,
        number_points: int | None = None,
    ) -> None:
        terminals = {
            "rgb": {"io": "in"},
            "alpha": {"io": "in"},
            "rgba": {"io": "out"},
        }
        VisualPipeline.__init__(self)
        CNode.__init__(self, node_name=self.nodeName, terminals=terminals, alias=alias)

        self.init_points(number_points, rgb=(rgb, (3,)), alpha=(alpha, ()))
        self.rgba = DataElement(self, 'rgba', ElementValue(np.zeros((int(self.number_points.value), 4))))

    def resize_points(self):
        self.rgba.value = np.zeros((int(self.number_points.value), 4))

    def c_update(self):
        rgb = self.rgb.value

        self.rgba.value[:] = np.concatenate(
            (rgb, self.alpha.value[:, np.newaxis] * 255.), axis=1
        )
