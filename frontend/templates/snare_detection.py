"""Live feature dashboard for experimenting with snare detection."""

import sys

from PyQt5 import QtCore, QtWidgets

from backend.updatable.updatable import audio_updatable_objects, visual_updatable_objects
from config import DELAY_UPDATE, FREQ_BINS, MAX_FREQUENCY, MIN_FREQUENCY, SAMPLE_RATE
from frontend.nodes.buffer import BufferNode
from frontend.nodes.features import SpectralCentroidNode
from frontend.nodes.pipelines import AmplitudesNode
from frontend.nodes.pipelines.auditory.filter import BandFilterPipelineNode
from frontend.nodes.pipelines.transforms.clip_node import ClipNode
from frontend.nodes.pipelines.transforms.operator_node import OperatorPipelineNode
from frontend.nodes.pipelines.transforms.value_transformer import ValueTransformerPipelineNode
from frontend.nodes.playlist_player import SCPlaylistPlayer
from frontend.nodes.stream import StreamPlayerNode
from frontend.nodes.visual import MultiLineChartNode
from frontend.nodes.window.window import WindowNode
from frontend.overrides.CFlowchart import CFlowchart
from frontend.overrides.CNode import CNode
from frontend.registry.registry import register_nodes
from frontend.nodes.windows_fcts import AveragedWindowFct


register_nodes()


def main():
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv)

    sc_playlist_player_node = SCPlaylistPlayer(
        cache=True,
        alias="sc_playlist_player_node"
    )

    analysis_chunk_size = int(SAMPLE_RATE * DELAY_UPDATE / 1000)

    stream_player_node = StreamPlayerNode(
        audio_in=sc_playlist_player_node.audio,
        sample_rate_in=sc_playlist_player_node.sample_rate,
        enqueue_token=sc_playlist_player_node.enqueue_token,
        chunk_size=analysis_chunk_size,
        alias="stream_player_node",
    )

    buffer_node = BufferNode(
        indata=stream_player_node.chunk,
        chunk_size=stream_player_node.chunk.value.shape[1],
        length=analysis_chunk_size,
        alias="buffer_node",
    )


    bandpass = BandFilterPipelineNode(
        buffer_data=buffer_node.data,
        lowcut=400.0,
        highcut=800.0,
        alias="snare_bandpass",
    )

    bandpass_amplitudes = AmplitudesNode(
        buffer=bandpass.data,
        min_frequency=MIN_FREQUENCY,
        max_frequency=MAX_FREQUENCY,
        fft_size=buffer_node.length.value,
        freq_bins=FREQ_BINS,
        alias="snare_bandpass_amplitudes",
    )

    spectral_centroid = SpectralCentroidNode(
        amplitudes=bandpass_amplitudes.data,
        frequencies=bandpass_amplitudes.frequencies,
        alias="snare_spectral_centroid",
    )
    centroid_clipped = ClipNode(
        input_value=spectral_centroid.data,
        min_value=1000.0,
        max_value=MAX_FREQUENCY,
        alias="snare_centroid_clipped",
    )
    centroid_window = WindowNode(
        input_data=centroid_clipped.data,
        length=150,
        offset=1,
        alias="snare_centroid_window",
    )
    average_centroid = AveragedWindowFct(window=centroid_window, alias="snare_average_centroid")
    centroid_difference = OperatorPipelineNode(
        arguments=[centroid_clipped.data, "-", average_centroid.data],
        length=1,
        alias="snare_centroid_difference",
    )
    positive_centroid_difference = ClipNode(
        input_value=centroid_difference.data,
        min_value=0.0,
        max_value=700.0,
        alias="snare_positive_centroid_difference",
    )
    centroid_difference_normalized = ValueTransformerPipelineNode(
        input_value=positive_centroid_difference.data,
        input_value_interval=(0.0, 700.0),
        output_value_interval=(0.0, 1.0),
        alias="snare_centroid_difference_normalized",
    )

    chart = MultiLineChartNode(
        node_selectors=[
            centroid_difference_normalized.output_value,
        ],
        number_points=400,
        title="Snare detection — normalized features",
        left_label="Normalized value",
        bottom_label="Time",
        y_min=0.0,
        y_max=0.1,
        alias="snare_features_chart",
    )

    flowchart = CFlowchart(
        terminals={
            "amplitudes": {"io": "out"},
        },
        nodes=list(filter(lambda x: isinstance(x, CNode) and x.render, list(locals().values())))
    )

    window = QtWidgets.QMainWindow()
    window.setWindowTitle("Snare detection")
    window.setCentralWidget(flowchart.widget())
    window.resize(1400, 850)
    window.show()

    def update():
        for node in audio_updatable_objects:
            node.c_update()
        for node in visual_updatable_objects:
            node.c_update()

    stream_player_node.start()
    app.aboutToQuit.connect(stream_player_node.stop)
    timer = QtCore.QTimer()
    timer.timeout.connect(update)
    timer.start(DELAY_UPDATE)
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
