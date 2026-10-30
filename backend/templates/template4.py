import numpy as np
from config import DELAY_UPDATE
from backend.updatable.updatable import audio_updatable_objects, visual_updatable_objects
from backend.nodes.controllers import ESP32Node
from backend.nodes.simple import ConstantArrayNode
from backend.overrides.CNode import CNode
from backend.nodes.pipelines.visual import RollingNode, RGBAPipelineNode
from backend.nodes.rainbow import RainbowNode
from backend.nodes.stream import StreamMicNode
from backend.nodes.visual.bar_graph_chart import BarGraphChartNode

def build_nodes():

    def audio_update(indata, frames, time, status):
        del indata, frames, time, status
        for obj in audio_updatable_objects:
            obj.c_update()
    stream_mic_node = StreamMicNode(user_callback=audio_update)
    rainbow = RainbowNode(alias='rainbow')
    rolling = RollingNode(input_data=rainbow.data, roll_speed=1, alias='rolling')
    constant_array = ConstantArrayNode(input_value=5, length=rainbow.data.value.shape[0], alias='constant_array')
    rgba_pipeline = RGBAPipelineNode(rgb=rolling.data, alpha=constant_array.data, alias='rgba_pipeline')
    spectogram_chart_node = BarGraphChartNode(data=np.ones(constant_array.data.value.shape[0]), number_points=constant_array.data.value.shape[0], brushes=rgba_pipeline.rgba, alias='spectogram_chart_node')
    esp32_node = ESP32Node(rgba=rgba_pipeline.rgba, alias='esp32_node')
    return [node for node in locals().values() if isinstance(node, CNode)]
