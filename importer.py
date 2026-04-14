import json
import re
import xml.etree.ElementTree as ET
from collections import Counter
from collections import defaultdict
from pathlib import Path

from graph import Graph


DEFAULT_JSON_ROAD_FILE = Path("data") / "real_neighborhood_roads.json"
DEFAULT_OSM_FILE = Path("data") / "neighborhood.osm"
DRIVABLE_HIGHWAYS = {
    "motorway",
    "motorway_link",
    "trunk",
    "trunk_link",
    "primary",
    "primary_link",
    "secondary",
    "secondary_link",
    "tertiary",
    "tertiary_link",
    "unclassified",
    "residential",
    "living_street",
    "service",
    "road",
}
DEFAULT_SPEED_KPH_BY_HIGHWAY = {
    "motorway": 100,
    "motorway_link": 60,
    "trunk": 80,
    "trunk_link": 50,
    "primary": 60,
    "primary_link": 45,
    "secondary": 50,
    "secondary_link": 40,
    "tertiary": 40,
    "tertiary_link": 35,
    "unclassified": 30,
    "residential": 30,
    "living_street": 15,
    "service": 20,
    "road": 30,
}
STOP_DELAY_SECONDS = 2
TRAFFIC_SIGNAL_DELAY_SECONDS = 5


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
        control_delay_seconds = road.get("control_delay_seconds", 0)
        return (distance_meters / speed_mps) + control_delay_seconds

    return distance_meters


def parse_maxspeed_kph(maxspeed):
    if maxspeed is None:
        return None

    if isinstance(maxspeed, (int, float)):
        return float(maxspeed)

    text = str(maxspeed).strip().lower()
    if not text:
        return None

    match = re.search(r"(\d+(?:\.\d+)?)", text)
    if match is None:
        return None

    value = float(match.group(1))
    if "mph" in text:
        return value * 1.60934

    return value


def default_speed_kph(tags):
    highway_type = tags.get("highway")
    return DEFAULT_SPEED_KPH_BY_HIGHWAY.get(highway_type, 30)


def direction_from_osm_tags(tags):
    oneway_value = str(tags.get("oneway", "")).strip().lower()
    junction_value = str(tags.get("junction", "")).strip().lower()

    if oneway_value in {"yes", "true", "1"} or junction_value == "roundabout":
        return "forward"
    if oneway_value in {"-1", "reverse"}:
        return "backward"
    return "both"


def is_routable_osm_way(tags):
    highway_type = tags.get("highway")
    if highway_type not in DRIVABLE_HIGHWAYS:
        return False

    if str(tags.get("area", "")).strip().lower() == "yes":
        return False

    return True


def build_segment_metadata(way, direction, speed_kph):
    tags = way["tags"]
    return {
        "id": way["id"],
        "direction": direction,
        "speed_kph": speed_kph,
        "name": tags.get("name"),
        "highway": tags.get("highway"),
        "osm_source": "way",
    }


def node_control_delay_seconds(node_tags):
    if not node_tags:
        return 0

    highway_value = str(node_tags.get("highway", "")).strip().lower()
    traffic_signal_value = str(node_tags.get("traffic_signals", "")).strip().lower()

    if highway_value == "traffic_signals" or traffic_signal_value == "signal":
        return TRAFFIC_SIGNAL_DELAY_SECONDS
    if highway_value == "stop":
        return STOP_DELAY_SECONDS

    return 0


def segment_control_delay_seconds(node_lookup, start_ref, end_ref, direction):
    start_delay = node_control_delay_seconds(node_lookup.get(start_ref, {}).get("tags"))
    end_delay = node_control_delay_seconds(node_lookup.get(end_ref, {}).get("tags"))

    if direction == "forward":
        return end_delay
    if direction == "backward":
        return start_delay

    return (start_delay + end_delay) / 2


def osm_segment_geometry(node_lookup, node_refs):
    geometry = []
    for node_ref in node_refs:
        node = node_lookup.get(node_ref)
        if node is None:
            continue
        geometry.append([node["lat"], node["lon"]])
    return geometry


def load_graph_from_osm_file(path, cost_mode="distance"):
    osm_file = Path(path)
    tree = ET.parse(osm_file)
    root = tree.getroot()

    node_lookup = {}
    for node in root.findall("node"):
        tags = {tag.attrib["k"]: tag.attrib["v"] for tag in node.findall("tag")}
        node_lookup[node.attrib["id"]] = {
            "lat": float(node.attrib["lat"]),
            "lon": float(node.attrib["lon"]),
            "tags": tags,
        }

    highway_ways = []
    node_usage = Counter()
    node_way_names = defaultdict(set)

    for way in root.findall("way"):
        tags = {tag.attrib["k"]: tag.attrib["v"] for tag in way.findall("tag")}
        if not is_routable_osm_way(tags):
            continue

        node_refs = [nd.attrib["ref"] for nd in way.findall("nd") if nd.attrib["ref"] in node_lookup]
        if len(node_refs) < 2:
            continue

        way_record = {
            "id": way.attrib["id"],
            "node_refs": node_refs,
            "tags": tags,
        }
        highway_ways.append(way_record)

        for node_ref in node_refs:
            node_usage[node_ref] += 1

        road_name = tags.get("name") or tags.get("highway") or "road"
        for node_ref in set(node_refs):
            node_way_names[node_ref].add(road_name)

    important_nodes = set()
    for way in highway_ways:
        important_nodes.add(way["node_refs"][0])
        important_nodes.add(way["node_refs"][-1])

    for node_ref, usage_count in node_usage.items():
        if usage_count > 1:
            important_nodes.add(node_ref)

    graph = Graph()
    osm_to_graph = {}
    used_labels = set()

    def graph_node_id(osm_ref):
        if osm_ref in osm_to_graph:
            return osm_to_graph[osm_ref]

        road_names = sorted(node_way_names.get(osm_ref, []))
        if len(road_names) >= 2:
            base_label = f"{road_names[0]} & {road_names[1]}"
        elif len(road_names) == 1:
            base_label = f"{road_names[0]} [{osm_ref}]"
        else:
            base_label = f"OSM {osm_ref}"

        label = base_label
        suffix = 2
        while label in used_labels:
            label = f"{base_label} ({suffix})"
            suffix += 1

        used_labels.add(label)
        osm_to_graph[osm_ref] = label
        node = node_lookup[osm_ref]
        graph.add_node(label, position=(node["lon"], node["lat"]))
        return label

    for way in highway_ways:
        refs = way["node_refs"]
        segment_start_index = 0

        for index in range(1, len(refs)):
            current_ref = refs[index]
            is_segment_end = current_ref in important_nodes
            if not is_segment_end:
                continue

            segment_refs = refs[segment_start_index:index + 1]
            if len(segment_refs) < 2:
                segment_start_index = index
                continue

            start_ref = segment_refs[0]
            end_ref = segment_refs[-1]
            start_node = graph_node_id(start_ref)
            end_node = graph_node_id(end_ref)
            geometry = osm_segment_geometry(node_lookup, segment_refs)
            direction = direction_from_osm_tags(way["tags"])
            speed_kph = parse_maxspeed_kph(way["tags"].get("maxspeed")) or default_speed_kph(way["tags"])
            control_delay_seconds = segment_control_delay_seconds(node_lookup, start_ref, end_ref, direction)

            if direction == "backward":
                road_info = {
                    "speed_kph": speed_kph,
                    "id": way["id"],
                    "control_delay_seconds": control_delay_seconds,
                }
                graph.add_edge(
                    end_node,
                    start_node,
                    weight=road_weight(graph, list(reversed(geometry)), road_info, cost_mode),
                    geometry=list(reversed(geometry)),
                    bidirectional=False,
                    metadata=build_segment_metadata(way, direction, speed_kph) | {"control_delay_seconds": control_delay_seconds},
                )
            else:
                road_info = {
                    "speed_kph": speed_kph,
                    "id": way["id"],
                    "control_delay_seconds": control_delay_seconds,
                }
                graph.add_edge(
                    start_node,
                    end_node,
                    weight=road_weight(graph, geometry, road_info, cost_mode),
                    geometry=geometry,
                    bidirectional=(direction == "both"),
                    metadata=build_segment_metadata(way, direction, speed_kph) | {"control_delay_seconds": control_delay_seconds},
                )

            segment_start_index = index

    return graph


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
    return load_graph_from_road_file(DEFAULT_JSON_ROAD_FILE, cost_mode=cost_mode)


def detect_active_graph_source(osm_path=DEFAULT_OSM_FILE, json_path=DEFAULT_JSON_ROAD_FILE):
    osm_path = Path(osm_path)
    json_path = Path(json_path)

    if osm_path.exists():
        return {
            "type": "osm",
            "label": "OSM XML",
            "path": str(osm_path),
        }

    return {
        "type": "json",
        "label": "JSON",
        "path": str(json_path),
    }


def build_active_graph(cost_mode="distance", osm_path=DEFAULT_OSM_FILE, json_path=DEFAULT_JSON_ROAD_FILE):
    source = detect_active_graph_source(osm_path=osm_path, json_path=json_path)
    if source["type"] == "osm":
        return load_graph_from_osm_file(osm_path, cost_mode=cost_mode)

    return load_graph_from_road_file(Path(json_path), cost_mode=cost_mode)
