import json
from pathlib import Path

from graph import Graph


def road_geometry(graph, road, start_node, end_node):
    geometry = road.get("geometry")
    if geometry is not None:
        return geometry

    start_position = graph.get_position(start_node)
    end_position = graph.get_position(end_node)
    if start_position is None or end_position is None:
        return None

    return [
        [start_position[1], start_position[0]],
        [end_position[1], end_position[0]],
    ]


def road_weight(graph, geometry, road, cost_mode):
    distance_meters = graph.geometry_length(geometry)

    if cost_mode == "time":
        speed_kph = road.get("speed_kph", 30)
        speed_mps = speed_kph * 1000 / 3600
        if speed_mps == 0:
            raise ValueError(f"Road {road.get('id', '<unknown>')} has zero speed.")
        return distance_meters / speed_mps

    return distance_meters


def load_graph_from_road_file(path, cost_mode="distance"):
    road_file = Path(path)
    with road_file.open("r", encoding="utf-8") as input_file:
        payload = json.load(input_file)

    graph = Graph()

    for node in payload.get("nodes", []):
        graph.add_node(node["id"], position=(node["lon"], node["lat"]))

    for road in payload.get("roads", []):
        direction = road.get("direction", "both")
        bidirectional = direction == "both"
        if direction == "backward":
            start_node = road["to"]
            end_node = road["from"]
            base_geometry = road_geometry(graph, road, road["from"], road["to"])
            geometry = list(reversed(base_geometry)) if base_geometry is not None else None
        else:
            start_node = road["from"]
            end_node = road["to"]
            geometry = road_geometry(graph, road, start_node, end_node)

        graph.add_edge(
            start_node,
            end_node,
            weight=road_weight(graph, geometry, road, cost_mode),
            geometry=geometry,
            bidirectional=bidirectional,
            metadata={
                "id": road.get("id"),
                "direction": direction,
                "speed_kph": road.get("speed_kph"),
                "cost_mode": cost_mode,
            },
        )

    return graph


def build_imported_real_neighborhood_graph(cost_mode="distance"):
    return load_graph_from_road_file(Path("data") / "real_neighborhood_roads.json", cost_mode=cost_mode)
