"""Processing node identity, ports, lifecycle, and saved value serialization."""
import inspect
from enum import Enum
from importlib import import_module
import numpy as np

class CNode:
    """Base processing node with named input/output Element attributes."""
    _SERDE_TAG = '__cnode_serde__'
    input_shapes = {}

    def __init__(self, node_name, terminals, parent=None, alias=None, **processing):
        super().__init__(**processing)
        self.node_name = node_name
        self.alias = alias or node_name
        self.parent = parent
        self.elements = []
        self.pending_terminals = dict(terminals)

    def name(self):
        return self.alias

    def rename(self, name):
        self.alias = name

    def terminal_element_name(self, name):
        return name

    def get_nodes(self):
        return self.parent.get_nodes() if self.parent is not None else []

    def close(self):
        for element in self.elements:
            value = element.value
            if isinstance(value, CNode) and value.parent is self:
                value.close()
            element.close()

    def validate_parameters(self, changes):
        """Reject coupled changes before mutating processing state."""

    @staticmethod
    def migrate_parameters(parameters):
        """Normalize saved constructor parameters before building a node."""
        return parameters

    def parameters_changed(self, name):
        """Rebuild derived state after a parameter change."""

    def configure_graph(self, graph, parameters):
        """Update structural connections when constructor parameters change."""

    def disconnect_input(self, name, parameters):
        """Remove a saved source reference; return any outputs removed with it."""
        value = parameters.get(name)
        if type(value) is dict and "nodeId" in value:
            parameters.pop(name)
        return ()

    def connect_input(self, name, source, parameters):
        """Normalize a new binding and any resulting terminal name changes."""
        self.disconnect_input(name, parameters)
        return name, {}

    def c_update(self):
        return {}

    def saveState(self):
        from backend.components.elements.element import Element
        from backend.components.elements.parameters import ReferenceElement
        from ai.template_generator.adapter import serialize
        values = {}
        for name in inspect.signature(type(self)).parameters:
            element = vars(self).get(name)
            if isinstance(element, Element) and (not isinstance(element, ReferenceElement)):
                source = element._value_source
                values[name] = serialize(source if source is not None else element.value)
        return {'ctor_kwargs': values}

    @classmethod
    def serialize_state_value(cls, value):
        if isinstance(value, Enum):
            return cls._serde('enum', module=type(value).__module__, class_name=type(value).__name__, name=value.name)
        if isinstance(value, np.ndarray):
            return cls._serde('ndarray', dtype=str(value.dtype), value=value.tolist())
        if isinstance(value, np.generic):
            return cls._serde('npscalar', dtype=str(value.dtype), value=value.item())
        if isinstance(value, tuple):
            serialized = cls._serialize_sequence(value)
            return None if serialized is None else cls._serde('tuple', value=serialized)
        if isinstance(value, list):
            return cls._serialize_sequence(value)
        if isinstance(value, dict):
            return cls._serialize_mapping(value)
        if callable(value):
            return None
        if isinstance(value, (str, int, float, bool, type(None))):
            return value
        return None

    @classmethod
    def _serde(cls, serde_type, **payload):
        return {cls._SERDE_TAG: serde_type, **payload}

    @classmethod
    def _serialize_sequence(cls, values):
        serialized = [cls.serialize_state_value(item) for item in values]
        return serialized if all((item is not None for item in serialized)) else None

    @classmethod
    def _serialize_mapping(cls, values):
        serialized = {key: cls.serialize_state_value(item) for key, item in values.items()}
        return serialized if all((item is not None for item in serialized.values())) else None

    @classmethod
    def deserialize_state_value(cls, value):
        if isinstance(value, dict):
            serde_type = value.get(cls._SERDE_TAG)
            if serde_type == 'enum':
                return vars(import_module(value['module']))[value['class_name']][value['name']]
            if serde_type == 'ndarray':
                return np.array(value['value'], dtype=np.dtype(value['dtype']))
            if serde_type == 'npscalar':
                return np.dtype(value['dtype']).type(value['value'])
            if serde_type == 'tuple':
                return tuple((cls.deserialize_state_value(item) for item in value['value']))
            return {key: cls.deserialize_state_value(item) for key, item in value.items()}
        if isinstance(value, list):
            return [cls.deserialize_state_value(item) for item in value]
        return value

class OfflineCNode(CNode):
    """Analysis of full tracks, updated by playlist playback position."""
    is_offline = True

    def calculate_playlist(self, tracks):
        pass

    def update_audio_index(self, track_index, audio_index):
        pass

    def update_audio_position(self, track_index, position):
        pass
