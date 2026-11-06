from backend.overrides.point_count_node import PointCountNode

class BarGraphChartNode(PointCountNode):
    """Expose bar heights and per-bar RGBA colors to frontend subscribers.

    Inputs `data` and `brushes` provide arrays; `number_points` records the
    light count. The node performs no rendering or signal transformation."""
    nodeName = 'BarGraphChart'

    def __init__(self, data=None, number_points=None, brushes=None, alias: str | None = None) -> None:
        super().__init__(node_name=self.nodeName, terminals={'brushes': {'io': 'in'}, 'data': {'io': 'in'}}, alias=alias)
        self.init_points(number_points, data=(data, ()), brushes=(brushes, (4,)))
