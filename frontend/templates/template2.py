import sys

from PyQt5 import QtCore, QtWidgets

from config import DELAY_UPDATE, SAMPLE_RATE
from frontend.enums.gradiant.gradiant_mode import GradiantMode
from frontend.nodes.controllers import ESP32Node
from frontend.nodes.pipelines.auditory.filter.low_filter import LowFilterPipelineNode
from frontend.nodes.pipelines.auditory.rms import RMSPipelineNode
from frontend.nodes.pipelines.transforms.operator_node import OperatorPipelineNode
from frontend.nodes.pipelines.transforms.value_transformer import ValueTransformerPipelineNode
from frontend.nodes.pipelines.visual import RGBAPipelineNode, RollingNode
from frontend.nodes.broadcast.broadcast_addition import BroadcastAdditionNode
from backend.updatable.updatable import audio_updatable_objects, visual_updatable_objects
from frontend.nodes.buffer import BufferNode
from frontend.overrides.CNode import CNode
from frontend.nodes.pipelines import AmplitudesNode
from frontend.nodes.playlist_player import SCPlaylistPlayer
from frontend.nodes.rainbow import GradiantNode, RainbowNode
from frontend.nodes.simple import ConstantArrayNode
from frontend.nodes.stream.stream_player_node import StreamPlayerNode
from frontend.nodes.visual import BarGraphChartNode, LineChartNode
from frontend.overrides.CFlowchart import CFlowchart
from frontend.registry.registry import register_nodes

register_nodes()

def main():
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv)

    sc_playlist_player_node = SCPlaylistPlayer(cache=True, alias="sc_playlist_player_node")
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

    amplitudes_node = AmplitudesNode(
        buffer=buffer_node.data,
        fft_size=analysis_chunk_size,
        # powering=0.5,
        alias="amplitudes_node",
    )

    low_filter_node = LowFilterPipelineNode(
        buffer_data=buffer_node.data,
        alias="low_filter_node",
    )

    rms_node = RMSPipelineNode(
        buffer_data=low_filter_node.data,
        alias="rms_node",
    )

    rms_chart_node = LineChartNode(
        input_data=rms_node.data,
        title="RMS",
        number_points=100,
        left_label="Level",
        bottom_label="Time",
        render=True,
        alias="rms_chart_node",
    )

    rms_transformed = ValueTransformerPipelineNode(
        input_value=rms_node.data,
        input_value_interval=[0, 0.6],
        output_value_interval=[0, 1.5],
        alias="rms_transformed",
    )
    rms_lowpass_node = RMSPipelineNode(
        buffer_data=low_filter_node.data,
        alias="rms_lowpass_node",
    )

    rms_lowpass_chart_node = LineChartNode(
        input_data=rms_lowpass_node.data,
        title="RMS Lowpass",
        number_points=100,
        left_label="Level",
        bottom_label="Time",
        render=True,
        alias="rms_lowpass_chart_node",
    )

    rms_lowpass_transformed = ValueTransformerPipelineNode(
        input_value=rms_lowpass_node.data,
        input_value_interval=[0.2, 0.8],
        output_value_interval=[0, 0.5],
        alias="rms_lowpass_transformed",
    )

    # amplitudes_transformer_node = LinearAmplitudesTransformerNode(
    #     input_data=amplitudes_node.data,
    #     correlation_offset=0.01,
    #     correlation_step=0.005,
    #     alias="amplitudes_transformer_node",
    # )

    amplitudes_node_normalized = ValueTransformerPipelineNode(
        input_value=amplitudes_node.data,
        input_value_interval=[0, 1],
        output_value_interval=[0, 0.8],
        alias="amplitudes_node_normalized",
    )

    amplitudes_with_rms = OperatorPipelineNode(
        arguments=[
            amplitudes_node_normalized.output_value,
            "*",
            rms_transformed.output_value,
        ],
        length=amplitudes_node_normalized.output_value.value.shape[-1],
        alias="amplitudes_with_rms",
    )

    gradiant = GradiantNode(cycle=1, alias="gradiant")

    gradient_rainbow = RainbowNode(
        gradiant=gradiant.data,
        alias="gradient_rainbow",
        mode=GradiantMode.MIRROR
    )

    rolling_rainbow = RollingNode(
        input_data=gradient_rainbow.data,
        alias="rolling_rainbow",
    )

    colorize_pipeline = BroadcastAdditionNode(
        input_data=rolling_rainbow.data,
        secondary_data=(255, 255, 255),
        level=rms_lowpass_transformed.output_value,
        alias="colorize_pipeline",
    )

    rgba_pipeline = RGBAPipelineNode(
        rgb=colorize_pipeline.data,
        alpha=amplitudes_with_rms.data,
        alias="rgba_pipeline",
    )

    esp32_node = ESP32Node(
        rgba=rgba_pipeline.rgba,
        alias="esp32_node",
    )

    constant_array_one = ConstantArrayNode(
        input_value=1,
        alias="constant_array_one",
    )

    spectogram_chart_node = BarGraphChartNode(
        data=constant_array_one.data,
        title="Amplitudes",
        number_points=amplitudes_node.data.value.shape[0],
        left_label="Frequency",
        bottom_label="Amplitude",
        brushes=rgba_pipeline.rgba,
        y_min=0,
        y_max=1,
    )

    chart_window = spectogram_chart_node.draw()

    # ------------------------ ADD FLOWCHART NODES ------------------------
    # ---------------------------------------------------------------------

    flowchart = CFlowchart(
        terminals={
            "amplitudes": {"io": "out"},
        },
        nodes=list(filter(lambda x: isinstance(x, CNode) and x.render, list(locals().values())))
    )



    # -------------------------- DRAW FLOWCHART ---------------------------
    # ---------------------------------------------------------------------

    graph_window = QtWidgets.QMainWindow()
    graph_window.setWindowTitle("LED Node Graph")
    graph_window.setCentralWidget(flowchart.widget())
    graph_window.resize(1100, 700)
    graph_window.show()

    def visual_update():
        for obj in audio_updatable_objects:
            obj.c_update()
        for obj in visual_updatable_objects:
            obj.c_update()

    sc_playlist_player_node.start()

    timer = QtCore.QTimer()
    timer.timeout.connect(visual_update)
    timer.start(DELAY_UPDATE)

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
