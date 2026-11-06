"""Shared processing node metadata and isolated construction."""
import inspect
from contextlib import contextmanager
from unittest.mock import patch


@contextmanager
def preview_nodes():
    """Disable workers and preserve update registries while inspecting nodes."""
    from backend.updatable.updatable import audio_updatable_objects, visual_updatable_objects
    audio, visual = list(audio_updatable_objects), list(visual_updatable_objects)
    try:
        with patch("threading.Thread.start"):
            yield
    finally:
        audio_updatable_objects[:] = audio
        visual_updatable_objects[:] = visual


class NodeCatalog:
    """Inspect registered node constructors and their Elements at runtime."""
    def __init__(self):
        from backend.registry.registry import nodes
        from backend.nodes.simple.constant_array import ConstantArrayNode
        from backend.components.elements.parameters import Parameter

        self.classes = {cls.nodeName: cls for cls in nodes}
        self.defaults, self.descriptions = {}, {}
        self.prototypes = []
        with preview_nodes():
            support = ConstantArrayNode(alias="ConstantArray.support")
            self.prototypes.append(support)
            for name, cls in self.classes.items():
                kwargs = {}
                if name == "Gathering":
                    kwargs.update(input_datas=[support.data], input_booleans=[support.length])
                if name == "AmplitudeLevelFunction":
                    kwargs["number_points"] = 300
                node = cls(**kwargs)
                self.prototypes.append(node)
                if name == "ESP32":
                    node.close()
                fields = []
                for parameter in inspect.signature(cls).parameters:
                    if parameter in ("alias", "parent", "terminals", "node_selector"):
                        continue
                    element = vars(node)[parameter]
                    if type(element) is Parameter:
                        details = element.kind
                        if element.kind == "number":
                            details += f" [{element.minimum}, {element.maximum}], integer={element.integer}, optional={element.optional}"
                    else:
                        details = type(element).__name__
                    fields.append(f"{parameter}: {details}")
                self.defaults[name] = {key: value for key, value in kwargs.items()
                                       if key not in ("input_datas", "input_booleans")}
                self.descriptions[name] = f"{inspect.getdoc(cls) or name} Parameters: {', '.join(fields)}"
            self.defaults["SCPlaylistPlayer"]["playlist_url"] = inspect.signature(
                self.classes["SCPlaylistPlayer"]).parameters["playlist_url"].default
