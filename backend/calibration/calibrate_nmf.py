"""Fit a template's NMF from downloaded playlist audio without playback.

python -m backend.calibration.calibrate_nmf --playlist-json /tmp/led2-playlist.json \
    --audio-dir /tmp/led2-nmf-audio --output backend/calibration/led2_nmf.npz
"""
import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
from math import ceil
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory

import networkx as nx
import numpy as np
import soundfile as sf
from threadpoolctl import threadpool_limits

from backend.api.protocol import decode, encode
from backend.api.runtime import Runtime
from backend.nodes.pipelines.transforms.dimensional_flattening_node import DimensionalFlatteningNode


def calibrate(template, playlist_json, audio_dir, output, max_iter=5000):
    graph = decode(template.read_bytes())['payload']['graph']
    target = next(node for node in graph['nodes'] if node['type'] == 'DimensionalFlattening')
    dimensions = target['parameters'].get('dimensions', 2)
    feature_id = target['parameters']['input_data']['nodeId']
    feature_element = target['parameters']['input_data']['element']
    dependencies = nx.DiGraph()
    for node in graph['nodes']:
        dependencies.add_node(node['id'])
        dependencies.add_edges_from((source, node['id']) for source in Runtime._references(node['parameters']))
    dependencies.add_edges_from((edge['source']['nodeId'], edge['target']['nodeId']) for edge in graph['connections'])
    keep = nx.ancestors(dependencies, feature_id) | {feature_id}
    feature_graph = {'nodes': [node for node in graph['nodes'] if node['id'] in keep],
                     'connections': [edge for edge in graph['connections'] if edge['source']['nodeId'] in keep and edge['target']['nodeId'] in keep]}
    playlist = json.loads(playlist_json.read_text())
    runtime = Runtime(preview=True)
    tracks, batches, tick_seconds = [], [], .005
    try:
        for index, entry in enumerate(playlist['entries']):
            track_id = str(entry['id'])
            files = [path for path in audio_dir.glob(f'{track_id}.*') if path.suffix in {'.m4a', '.mp3', '.wav', '.flac', '.ogg', '.opus', '.aac'}]
            if len(files) != 1:
                raise ValueError(f'Expected one downloaded audio file for {track_id}, found {len(files)}')
            info = json.loads((audio_dir / f'{track_id}.info.json').read_text())
            runtime.load(feature_graph, replace=True)
            stream = next(node for node in runtime.nodes.values() if node.nodeName == 'StreamPlayer')
            player = next(node for node in runtime.nodes.values() if node.nodeName == 'SCPlaylistPlayer')
            updates = [node for node in runtime.updates if node is not stream and node is not player]
            feature = vars(runtime.nodes[feature_id])[feature_element]
            with TemporaryDirectory() as directory:
                wav = Path(directory) / 'track.wav'
                subprocess.run(['ffmpeg', '-v', 'error', '-nostdin', '-i', str(files[0]), '-vn', '-c:a', 'pcm_s16le', str(wav)], check=True)
                audio, rate = sf.read(wav, dtype='float32', always_2d=True)
            if audio.shape[1] == 1:
                audio = np.repeat(audio, 2, axis=1)
            stream.enqueue(audio, rate)
            del audio
            frames, rate = int(stream.chunk_size.value), int(stream.sample_rate.value)
            block = np.empty((frames, 2), dtype=np.float32)
            samples, previous, ticks = [], None, 0
            duration = len(stream._audio) / rate
            for start in range(0, len(stream._audio), frames):
                stream._callback(block, frames, None, None)
                end_tick = ceil((start + frames) / rate / tick_seconds)
                for _ in range(ticks, end_tick):
                    for node in updates:
                        node.c_update()
                    vector = np.asarray(feature.value, dtype=float).reshape(-1)
                    if not np.isfinite(vector).all():
                        raise ValueError(f'Nonfinite features in track {track_id}, sample {start}')
                    if previous is None or not np.array_equal(vector, previous):
                        previous = vector.copy()
                        samples.append(previous)
                ticks = end_tick
            batches.append(np.asarray(samples))
            tracks.append({'id': track_id, 'title': info['title'], 'url': info['webpage_url'],
                           'duration_seconds': duration, 'processing_frames': ticks, 'training_vectors': len(samples),
                           'audio_sha256': sha256(files[0].read_bytes()).hexdigest()})
            print(f'[{index + 1}/{len(playlist["entries"])}] {info["title"]}: {duration:.1f}s, {len(samples)} feature vectors', flush=True)
    finally:
        runtime.close()
    samples = np.concatenate(batches)
    print(f'Fitting NMF on {len(samples)} vectors × {samples.shape[1]} features…', flush=True)
    with threadpool_limits(limits=2):
        minimum, scale, components = DimensionalFlatteningNode.fit(samples, max_iter=max_iter, dimensions=dimensions)
    output.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(output, minimum=minimum, scale=scale, components=components)
    metadata = {'version': 1, 'created_at': datetime.now(timezone.utc).isoformat(),
                'playlist_url': playlist['webpage_url'], 'template': str(template),
                'feature_graph': feature_graph, 'feature_graph_sha256': sha256(encode({'type': 'graph', 'payload': feature_graph})).hexdigest(),
                'sample_rate': rate, 'chunk_size': frames, 'processing_tick_seconds': tick_seconds,
                'training_vectors': len(samples), 'feature_count': samples.shape[1], 'tracks': tracks,
                'nmf': {'components': dimensions, 'init': 'nndsvda', 'random_state': 0, 'max_iter': max_iter},
                'model_sha256': sha256(output.read_bytes()).hexdigest()}
    output.with_suffix('.json').write_text(json.dumps(metadata, indent=2) + '\n')
    print(f'Saved {output} ({output.stat().st_size} bytes)', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--template', type=Path, default=Path('backend/templates/template_clustering.led'))
    parser.add_argument('--playlist-json', type=Path, required=True)
    parser.add_argument('--audio-dir', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--max-iter', type=int, default=5000)
    args = parser.parse_args()
    calibrate(args.template, args.playlist_json, args.audio_dir, args.output, args.max_iter)
