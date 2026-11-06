from config import DELAY_UPDATE, SAMPLE_RATE
from backend.enums.gradiant.gradiant_mode import GradiantMode
from backend.nodes.controllers import ESP32Node
from backend.nodes.pipelines.auditory.filter.low_filter import LowFilterPipelineNode
from backend.nodes.pipelines.auditory.rms import RMSPipelineNode
from backend.nodes.pipelines.transforms.operator_node import OperatorPipelineNode
from backend.nodes.pipelines.transforms.value_transformer import ValueTransformerPipelineNode
from backend.nodes.pipelines.visual import RGBAPipelineNode, RollingNode
from backend.nodes.broadcast.broadcast_addition import BroadcastAdditionNode
from backend.updatable.updatable import audio_updatable_objects, visual_updatable_objects
from backend.nodes.buffer import BufferNode
from backend.overrides.CNode import CNode
from backend.nodes.pipelines import AmplitudesNode
from backend.nodes.playlist_player import SCPlaylistPlayer
from backend.nodes.rainbow import GradiantNode, RainbowNode
from backend.nodes.simple import ConstantArrayNode
from backend.nodes.stream.stream_player_node import StreamPlayerNode
from backend.nodes.visual import BarGraphChartNode, SingleLineChartNode

def build_nodes():
    sc_playlist_player_node = SCPlaylistPlayer(cache=True, alias='sc_playlist_player_node')
    analysis_chunk_size = int(SAMPLE_RATE * DELAY_UPDATE / 1000)
    stream_player_node = StreamPlayerNode(audio_in=sc_playlist_player_node.audio, sample_rate_in=sc_playlist_player_node.sample_rate, enqueue_token=sc_playlist_player_node.enqueue_token, chunk_size=analysis_chunk_size, alias='stream_player_node')
    buffer_node = BufferNode(indata=stream_player_node.chunk, chunk_size=stream_player_node.chunk.value.shape[1], length=analysis_chunk_size, alias='buffer_node')
    amplitudes_node = AmplitudesNode(buffer=buffer_node.data, fft_size=analysis_chunk_size, alias='amplitudes_node')
    low_filter_node = LowFilterPipelineNode(buffer_data=buffer_node.data, alias='low_filter_node')
    rms_node = RMSPipelineNode(buffer_data=low_filter_node.data, alias='rms_node')
    rms_chart_node = SingleLineChartNode(input_data=rms_node.data, number_points=100, alias='rms_chart_node')
    rms_transformed = ValueTransformerPipelineNode(input_value=rms_node.data, input_value_interval=[0, 0.6], output_value_interval=[0, 1.5], alias='rms_transformed')
    rms_lowpass_node = RMSPipelineNode(buffer_data=low_filter_node.data, alias='rms_lowpass_node')
    rms_lowpass_chart_node = SingleLineChartNode(input_data=rms_lowpass_node.data, number_points=100, alias='rms_lowpass_chart_node')
    rms_lowpass_transformed = ValueTransformerPipelineNode(input_value=rms_lowpass_node.data, input_value_interval=[0.2, 0.8], output_value_interval=[0, 0.5], alias='rms_lowpass_transformed')
    amplitudes_node_normalized = ValueTransformerPipelineNode(input_value=amplitudes_node.data, input_value_interval=[0, 1], output_value_interval=[0, 0.8], alias='amplitudes_node_normalized')
    amplitudes_with_rms = OperatorPipelineNode(arguments=[amplitudes_node_normalized.output_value, '*', rms_transformed.output_value], length=amplitudes_node_normalized.output_value.value.shape[-1], alias='amplitudes_with_rms')
    gradiant = GradiantNode(cycle=1, alias='gradiant')
    gradient_rainbow = RainbowNode(gradiant=gradiant.data, alias='gradient_rainbow', mode=GradiantMode.MIRROR)
    rolling_rainbow = RollingNode(input_data=gradient_rainbow.data, alias='rolling_rainbow')
    colorize_pipeline = BroadcastAdditionNode(input_data=rolling_rainbow.data, secondary_data=(255, 255, 255), level=rms_lowpass_transformed.output_value, alias='colorize_pipeline')
    rgba_pipeline = RGBAPipelineNode(rgb=colorize_pipeline.data, alpha=amplitudes_with_rms.data, alias='rgba_pipeline')
    esp32_node = ESP32Node(rgba=rgba_pipeline.rgba, alias='esp32_node')
    constant_array_one = ConstantArrayNode(input_value=1, alias='constant_array_one')
    spectogram_chart_node = BarGraphChartNode(data=constant_array_one.data, number_points=amplitudes_node.data.value.shape[0], brushes=rgba_pipeline.rgba)
    return [node for node in locals().values() if isinstance(node, CNode)]
