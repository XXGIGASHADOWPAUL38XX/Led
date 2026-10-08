import sys

from PyQt5 import QtCore, QtWidgets

from backend.updatable.updatable import audio_updatable_objects, visual_updatable_objects
from config import DELAY_UPDATE, SAMPLE_RATE
from frontend.group_nodes import KickDecayNode, SnareDecayNode
from frontend.nodes.buffer import BufferNode
from frontend.nodes.playlist_player import SCPlaylistPlayer
from frontend.nodes.stream.stream_player_node import StreamPlayerNode
from frontend.overrides.CFlowchart import CFlowchart
from frontend.overrides.CNode import CNode
from frontend.registry.registry import register_nodes


register_nodes()


def main():
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv)

    playlist_node = SCPlaylistPlayer(cache=True, alias="sc_playlist_player")
    analysis_chunk_size = int(SAMPLE_RATE * DELAY_UPDATE / 1000)
    stream_node = StreamPlayerNode(
        audio_in=playlist_node.audio,
        sample_rate_in=playlist_node.sample_rate,
        enqueue_token=playlist_node.enqueue_token,
        chunk_size=analysis_chunk_size,
        alias="stream_player",
    )
    buffer_node = BufferNode(
        indata=stream_node.chunk,
        chunk_size=stream_node.chunk.value.shape[1],
        length=analysis_chunk_size,
        alias="buffer",
    )

    kick_decay_node = KickDecayNode(
        buffer_data=buffer_node.data,
        alias="kick_decay",
    )
    snare_decay_node = SnareDecayNode(
        buffer_data=buffer_node.data,
        alias="snare_decay",
    )

    flowchart = CFlowchart(
        terminals={
            "kick_trigger": {"io": "out"},
            "snare_trigger": {"io": "out"},
        },
        nodes=[
            node
            for node in locals().values()
            if isinstance(node, CNode) and node.render
        ],
    )

    window = QtWidgets.QMainWindow()
    window.setWindowTitle("Stems")
    window.setCentralWidget(flowchart.widget())
    window.resize(1100, 700)
    window.show()

    def update():
        for obj in audio_updatable_objects:
            obj.c_update()
        for obj in visual_updatable_objects:
            obj.c_update()

    playlist_node.start()
    timer = QtCore.QTimer()
    timer.timeout.connect(update)
    timer.start(DELAY_UPDATE)
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
