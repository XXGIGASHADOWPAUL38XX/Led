import unittest

import msgpack
import numpy as np

from backend.api.protocol import encode, decode, event


class ProtocolTests(unittest.TestCase):
    def test_arrays_and_commands_share_one_format(self):
        for dtype in ('float32', 'float64', 'int16', 'uint8', 'int64', 'bool'):
            original = np.arange(240).reshape(12, 20)[:, ::2].astype(dtype)
            packet = encode(event('frame', {'value': original, 'scalar': np.float32(0.5)}, 3))
            restored = decode(packet)
            np.testing.assert_array_equal(restored['payload']['value'], original)
            self.assertEqual(restored['payload']['value'].dtype, original.dtype)
            self.assertEqual(restored['revision'], 3)
        command = event('element.set', {'nodeId': 'a', 'element': 'powering', 'value': 0.75}, 0, 9)
        self.assertEqual(decode(encode(command)), command)

    def test_rejects_unsafe_array_metadata_and_text_frames(self):
        for descriptor in (
            {'dtype': '|O', 'shape': [1], 'data': b'12345678'},
            {'dtype': '<f4', 'shape': [-1], 'data': b''},
            {'dtype': '<f4', 'shape': [100], 'data': b'1234'},
        ):
            raw = msgpack.packb({'type': 'set', 'payload': {'value': {'__ndarray__': True, **descriptor}}}, use_bin_type=True)
            with self.assertRaises(ValueError):
                decode(raw)
        with self.assertRaises(ValueError):
            decode('{"type":"set"}')

    def test_scalar_empty_and_non_contiguous_arrays(self):
        for array in (np.zeros((0, 2)), np.array(42), np.ones((2, 8))[:, ::2]):
            result = decode(encode(event('frame', {'value': array}, 0)))['payload']['value']
            np.testing.assert_array_equal(result, array)
            self.assertEqual(result.shape, array.shape)
