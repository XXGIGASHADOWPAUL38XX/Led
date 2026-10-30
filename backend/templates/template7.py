from backend.updatable.updatable import audio_updatable_objects, visual_updatable_objects
from config import DELAY_UPDATE, FREQ_BINS, SAMPLE_RATE
from backend.enums.cut_side.cut_side_mode import CutSideMode
from backend.enums.gradiant.gradiant_mode import GradiantMode
from backend.group_nodes import KickDecayNode
from backend.nodes.buffer import BufferNode
from backend.nodes.function.outbounds_fct import OutboundsFctNode
from backend.nodes.pipelines import AmplitudesNode
from backend.nodes.pipelines.amplitudes.linear_amplitude_transformer_node import LinearAmplitudesTransformerNode
from backend.nodes.pipelines.auditory.filter.low_filter import LowFilterPipelineNode
from backend.nodes.pipelines.auditory.rms import RMSPipelineNode
from backend.nodes.pipelines.transforms.operator_node import OperatorPipelineNode
from backend.nodes.pipelines.transforms.value_transformer import ValueTransformerPipelineNode
from backend.nodes.pipelines.visual import RGBAPipelineNode, RollingNode
from backend.nodes.playlist_player import SCPlaylistPlayer
from backend.nodes.rainbow import RainbowNode, GradiantNode
from backend.nodes.simple import ConstantArrayNode, SinArrayNode
from backend.nodes.stream.stream_player_node import StreamPlayerNode
from backend.nodes.visual import BarGraphChartNode
from backend.nodes.window.window import WindowNode
from backend.nodes.windows_fcts import CeilWindowFct
from backend.overrides.CNode import CNode

def build_nodes():
    sc_playlist_player_node = SCPlaylistPlayer(cache=True, prefetch_seconds=18, alias='soundcloud_playlist')
    analysis_chunk_size = int(SAMPLE_RATE * DELAY_UPDATE / 1000)
    stream_player_node = StreamPlayerNode(audio_in=sc_playlist_player_node.audio, sample_rate_in=sc_playlist_player_node.sample_rate, enqueue_token=sc_playlist_player_node.enqueue_token, chunk_size=analysis_chunk_size, alias='stream_player')
    buffer_node = BufferNode(indata=stream_player_node.chunk, chunk_size=stream_player_node.chunk.value.shape[1], length=analysis_chunk_size, alias='analysis_buffer')
    amplitudes_node = AmplitudesNode(buffer=buffer_node.data, fft_size=analysis_chunk_size, normalisation=True, alias='amplitudes')
    transformed_amplitudes_node = LinearAmplitudesTransformerNode(input_data=amplitudes_node.data, correlation_offset=0.1, correlation_step=0.04, log=0.3)
    standardized_amplitudes_node = ValueTransformerPipelineNode(input_value=transformed_amplitudes_node.data, input_value_interval=[0, 4], output_value_interval=[0, 1])
    kick_decay_node = KickDecayNode(buffer_data=buffer_node.data, lowpass_freq=300, threshold=0.3, decay_length=30, alias='kick_decay_node')
    window_node = WindowNode(input_data=kick_decay_node.data, length=FREQ_BINS // kick_decay_node.window_node.length.value, alias='window_node')
    ceil_window_function = CeilWindowFct(window=window_node, alias='ceil_window_function')
    y_offset_value = ValueTransformerPipelineNode(input_value=kick_decay_node.data, input_value_interval=[0, 1], output_value_interval=[-0.6, 0.6], alias='y_offset_value')
    tide_spike_fct = OutboundsFctNode(y_outbound=-2, y_center=ceil_window_function.data, y_offset=y_offset_value.output_value, cute_side_mode=CutSideMode.LEFT, alias='tide_spike_fct')
    alpha_with_tide = OperatorPipelineNode(arguments=['(', standardized_amplitudes_node.output_value, '*', 0.5, ')', '+', '(', tide_spike_fct.data, '*', 0.3, ')'], length=FREQ_BINS, alias='alpha_with_tide')
    tide_gradient_node = GradiantNode(color_in=(18, 235, 198), color_out=(238, 74, 146), alias='tide_gradient')
    rgba_pipeline_node = RGBAPipelineNode(rgb=tide_gradient_node.data, alpha=alpha_with_tide.data, alias='tide_rgba')
    constant_array_one_node = ConstantArrayNode(input_value=1, length=FREQ_BINS, alias='constant_array_one')
    tide_chart_node = BarGraphChartNode(data=constant_array_one_node.data, number_points=FREQ_BINS, brushes=rgba_pipeline_node.rgba, alias='tide_chart')
    return [node for node in locals().values() if isinstance(node, CNode)]
