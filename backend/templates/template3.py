import numpy as np
from config import DELAY_UPDATE
from backend.nodes.pipelines.amplitudes.linear_amplitude_transformer_node import LinearAmplitudesTransformerNode
from backend.nodes.pipelines.visual.rgba_pipeline import RGBAPipelineNode
from backend.updatable.updatable import audio_updatable_objects, visual_updatable_objects
from backend.nodes.buffer import BufferNode
from backend.overrides.CNode import CNode
from backend.nodes.pipelines import AmplitudesNode
from backend.nodes.rainbow import RainbowNode
from backend.nodes.stream import StreamMicNode
from backend.nodes.visual.bar_graph_chart import BarGraphChartNode

def build_nodes():

    def audio_update(indata, frames, time, status):
        del indata, frames, time, status
        for obj in audio_updatable_objects:
            obj.c_update()
    stream_mic_node = StreamMicNode(user_callback=audio_update)
    buffer_node = BufferNode(indata=stream_mic_node.chunk)
    amplitudes_node = AmplitudesNode(buffer=buffer_node.data, powering=-0.2, normalisation=True)
    gradient_rainbow = RainbowNode()
    rgba_pipeline = RGBAPipelineNode(rgb=gradient_rainbow.data, alpha=lambda: np.ones(amplitudes_node.data.value.shape[0]) * 255)
    spectogram_chart_node = BarGraphChartNode(data=amplitudes_node.data, number_points=amplitudes_node.data.value.shape[0], brushes=rgba_pipeline.rgba)
    return [node for node in locals().values() if isinstance(node, CNode)]
