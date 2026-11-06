"""Live feature dashboard for experimenting with snare detection."""
from backend.updatable.updatable import audio_updatable_objects, visual_updatable_objects
from config import DELAY_UPDATE, FREQ_BINS, MAX_FREQUENCY, MIN_FREQUENCY, SAMPLE_RATE
from backend.nodes.buffer import BufferNode
from backend.nodes.features import SpectralCentroidNode
from backend.nodes.pipelines import AmplitudesNode
from backend.nodes.pipelines.auditory.filter import BandFilterPipelineNode
from backend.nodes.pipelines.transforms.clip_node import ClipNode
from backend.nodes.pipelines.transforms.operator_node import OperatorPipelineNode
from backend.nodes.pipelines.transforms.value_transformer import ValueTransformerPipelineNode
from backend.nodes.playlist_player import SCPlaylistPlayer
from backend.nodes.stream import StreamPlayerNode
from backend.nodes.visual import MultiLineChartNode
from backend.nodes.window.window import WindowNode
from backend.overrides.CNode import CNode
from backend.nodes.windows_fcts import AveragedWindowFct

def build_nodes():
    sc_playlist_player_node = SCPlaylistPlayer(cache=True, alias='sc_playlist_player_node')
    analysis_chunk_size = int(SAMPLE_RATE * DELAY_UPDATE / 1000)
    stream_player_node = StreamPlayerNode(audio_in=sc_playlist_player_node.audio, sample_rate_in=sc_playlist_player_node.sample_rate, enqueue_token=sc_playlist_player_node.enqueue_token, chunk_size=analysis_chunk_size, alias='stream_player_node')
    buffer_node = BufferNode(indata=stream_player_node.chunk, chunk_size=stream_player_node.chunk.value.shape[1], length=analysis_chunk_size, alias='buffer_node')
    bandpass = BandFilterPipelineNode(buffer_data=buffer_node.data, lowcut=400.0, highcut=800.0, alias='snare_bandpass')
    bandpass_amplitudes = AmplitudesNode(buffer=bandpass.data, min_frequency=MIN_FREQUENCY, max_frequency=MAX_FREQUENCY, fft_size=buffer_node.length.value, freq_bins=FREQ_BINS, alias='snare_bandpass_amplitudes')
    spectral_centroid = SpectralCentroidNode(amplitudes=bandpass_amplitudes.data, frequencies=bandpass_amplitudes.frequencies, alias='snare_spectral_centroid')
    centroid_clipped = ClipNode(input_value=spectral_centroid.data, min_value=1000.0, max_value=MAX_FREQUENCY, alias='snare_centroid_clipped')
    centroid_window = WindowNode(input_data=centroid_clipped.data, length=150, offset=1, alias='snare_centroid_window')
    average_centroid = AveragedWindowFct(window=centroid_window, alias='snare_average_centroid')
    centroid_difference = OperatorPipelineNode(arguments=[centroid_clipped.data, '-', average_centroid.data], length=1, alias='snare_centroid_difference')
    positive_centroid_difference = ClipNode(input_value=centroid_difference.data, min_value=0.0, max_value=700.0, alias='snare_positive_centroid_difference')
    centroid_difference_normalized = ValueTransformerPipelineNode(input_value=positive_centroid_difference.data, input_value_interval=(0.0, 700.0), output_value_interval=(0.0, 1.0), alias='snare_centroid_difference_normalized')
    chart = MultiLineChartNode(node_selectors=[centroid_difference_normalized.output_value], number_points=400, alias='snare_features_chart')
    return [node for node in locals().values() if isinstance(node, CNode)]
