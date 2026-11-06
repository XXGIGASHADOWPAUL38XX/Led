from backend.overrides.CNode import CNode
from backend.updatable.updatable import audio_updatable_objects, visual_updatable_objects
from config import DELAY_UPDATE, SAMPLE_RATE
from backend.nodes.offline.stems_recognition import StemsRecognitionNode
from backend.nodes.playlist_player import SCPlaylistPlayer
from backend.nodes.stream.stream_player_node import StreamPlayerNode

def build_nodes():
    sc_playlist_player_node = SCPlaylistPlayer(cache=True, alias='sc_playlist_player_node')
    stream_player_node = StreamPlayerNode(audio_in=sc_playlist_player_node.audio, sample_rate_in=sc_playlist_player_node.sample_rate, enqueue_token=sc_playlist_player_node.enqueue_token, chunk_size=int(SAMPLE_RATE * DELAY_UPDATE / 1000), alias='stream_player_node')
    stems_recognition_node = StemsRecognitionNode(alias='stems_recognition_node')
    return [node for node in locals().values() if isinstance(node, CNode)]
