from backend.updatable.updatable import audio_updatable_objects, visual_updatable_objects
from config import DELAY_UPDATE, SAMPLE_RATE
from backend.group_nodes import KickDecayNode, SnareDecayNode
from backend.nodes.buffer import BufferNode
from backend.nodes.playlist_player import SCPlaylistPlayer
from backend.nodes.stream.stream_player_node import StreamPlayerNode
from backend.overrides.CNode import CNode

def build_nodes():
    playlist_node = SCPlaylistPlayer(cache=True, alias='sc_playlist_player')
    analysis_chunk_size = int(SAMPLE_RATE * DELAY_UPDATE / 1000)
    stream_node = StreamPlayerNode(audio_in=playlist_node.audio, sample_rate_in=playlist_node.sample_rate, enqueue_token=playlist_node.enqueue_token, chunk_size=analysis_chunk_size, alias='stream_player')
    buffer_node = BufferNode(indata=stream_node.chunk, chunk_size=stream_node.chunk.value.shape[1], length=analysis_chunk_size, alias='buffer')
    kick_decay_node = KickDecayNode(buffer_data=buffer_node.data, alias='kick_decay')
    snare_decay_node = SnareDecayNode(buffer_data=buffer_node.data, alias='snare_decay')
    return [node for node in locals().values() if isinstance(node, CNode)]
