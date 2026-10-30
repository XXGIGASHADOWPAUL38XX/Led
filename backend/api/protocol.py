"""One wire format for commands, settings, and packed NumPy arrays."""
from enum import Enum
from math import prod

import msgpack
import numpy as np

DTYPES = {"|b1", "|u1", "|i1", "<i2", "<u2", "<i4", "<u4", "<i8", "<u8", "<f4", "<f8"}
MAX_BYTES = 64 * 1024 * 1024


def _default(value):
    if isinstance(value, np.ndarray):
        dtype = value.dtype.newbyteorder("<")
        if dtype.str not in DTYPES:
            raise ValueError(f"Unsupported array dtype: {dtype}")
        array = np.ascontiguousarray(value, dtype=dtype)
        return {"__ndarray__": True, "dtype": dtype.str, "shape": list(value.shape), "data": array.tobytes()}
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, Enum):
        return value.name
    raise TypeError(f"Cannot encode {type(value).__name__}")


def _object(value):
    if value.get("__ndarray__") is not True:
        return value
    if value["dtype"] not in DTYPES:
        raise ValueError("Unsupported array dtype")
    shape = value["shape"]
    if len(shape) > 16 or any(type(size) is not int or size < 0 for size in shape):
        raise ValueError("Invalid array shape")
    dtype = np.dtype(value["dtype"])
    size = prod(shape) * dtype.itemsize
    if size > MAX_BYTES or size != len(value["data"]):
        raise ValueError("Array shape and byte length disagree")
    return np.frombuffer(value["data"], dtype=dtype).reshape(shape).copy()


def encode(message):
    return msgpack.packb(message, default=_default, use_bin_type=True)


def decode(data):
    if type(data) is not bytes:
        raise ValueError("Send binary MessagePack messages")
    message = msgpack.unpackb(data, raw=False, object_hook=_object, strict_map_key=True)
    if type(message) is not dict or type(message.get("type")) is not str or type(message.get("payload", {})) is not dict:
        raise ValueError("Expected a message with type and object payload")
    return message


def event(kind, payload, revision, request_id=None):
    return {"type": kind, "requestId": request_id, "revision": revision, "payload": payload}
