import numpy as np
from backend.updatable.updatable import visual_updatable_objects
from config import DELAY_UPDATE, FREQ_BINS
from backend.nodes.controllers import ESP32Node
from backend.nodes.pipelines.visual import RGBAPipelineNode, SingleColorNode
from backend.nodes.simple import ConstantArrayNode
from backend.nodes.visual import BarGraphChartNode
from backend.overrides.CNode import CNode

def build_nodes():
    white = SingleColorNode(color=(255, 255, 255), number_points=FREQ_BINS, alias='white')
    alpha = ConstantArrayNode(input_value=10 / 255.0, length=FREQ_BINS, alias='alpha')
    rgba = RGBAPipelineNode(rgb=white.data, alpha=alpha.data, alias='rgba')
    chart = BarGraphChartNode(data=alpha.data, number_points=FREQ_BINS, brushes=rgba.rgba, alias='chart')
    esp32 = ESP32Node(rgba=rgba.rgba)
    return [node for node in locals().values() if isinstance(node, CNode)]
