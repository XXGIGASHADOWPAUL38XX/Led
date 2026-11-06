import inspect
import unittest
from unittest.mock import patch

import numpy as np

from backend.components.elements.element import Element
from backend.components.elements.parameters import Parameter, ReferenceElement, SequenceElement
from backend.enums.gradiant.gradiant_mode import GradiantMode
from backend.nodes.simple.constant_array import ConstantArrayNode
from backend.overrides.CNode import CNode
from backend.registry.registry import nodes


class ParameterTests(unittest.TestCase):
    def test_registered_parameters_are_typed_and_defaults_fit_bounds(self):
        held = []
        with patch("threading.Thread.start"):
            for node_type in nodes:
                with self.subTest(node=node_type.nodeName):
                    kwargs = {}
                    if node_type.nodeName == "SCPlaylistPlayer":
                        kwargs["playlist_url"] = ""
                    if node_type.nodeName == "AmplitudeLevelFunction":
                        kwargs["number_points"] = 300
                    if node_type.nodeName == "Gathering":
                        source = ConstantArrayNode()
                        enabled = ConstantArrayNode(input_value=1, length=1)
                        held.extend((source, enabled))
                        kwargs.update(input_datas=[source.data], input_booleans=[enabled.data])
                    node = node_type(**kwargs)
                    held.append(node)
                    for name in inspect.signature(node_type).parameters:
                        if name in ("alias", "parent", "terminals"):
                            continue
                        parameter = vars(node)[name]
                        self.assertIsInstance(parameter, Element, name)
                        self.assertIsNot(type(parameter), Element, name)
                        if isinstance(parameter, Parameter) and parameter.kind == "number" and isinstance(parameter.value, (int, float)):
                            self.assertLessEqual(parameter.minimum, parameter.value, name)
                            self.assertLessEqual(parameter.value, parameter.maximum, name)
                    node.saveState()

    def test_integer_controls_callbacks_and_collections(self):
        with patch("threading.Thread.start"):
            node = ConstantArrayNode()
            parameter = Parameter(node, "count", 1, minimum=1, maximum=100, integer=True)
            parameter.value = 37
            self.assertIs(type(parameter.value), int)
            callback = lambda: self.fail("Callback must not be evaluated while wrapping")
            reference = ReferenceElement(node, "callback", callback)
            self.assertIs(reference.value, callback)
            child = ConstantArrayNode()
            collection = SequenceElement(node, "children", [child], register_in_node=False)
            self.assertIsNone(child.parent)
            self.assertEqual(list(collection), [child])

    def test_enum_and_authored_array_serialization(self):
        for value in (GradiantMode.MIRROR, np.array([[0.123456789, 1.0]], dtype=np.float64)):
            restored = CNode.deserialize_state_value(CNode.serialize_state_value(value))
            if isinstance(value, np.ndarray):
                np.testing.assert_array_equal(restored, value)
                self.assertEqual(restored.dtype, value.dtype)
            else:
                self.assertIs(restored, value)


if __name__ == "__main__":
    unittest.main()
