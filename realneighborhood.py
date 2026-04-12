from math import atan2
from math import cos
from math import radians
from math import sin
from math import sqrt

from graph import Graph


EARTH_RADIUS_METERS = 6_371_000

REAL_NEIGHBORHOOD_POINTS = {
    "Library": (42.40594739254316, -71.05663926029985),
    "Dunkin": (42.40931637016323, -71.05338889338316),
    "Whittier": (42.404198513981676, -71.05810214227245),
    "Home": (42.40640672173467, -71.05413549779504),
}


def haversine_distance(point_a, point_b):
    lat1, lon1 = map(radians, point_a)
    lat2, lon2 = map(radians, point_b)

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    return EARTH_RADIUS_METERS * c


def project_to_local_xy(point, reference_latitude):
    lat, lon = point
    latitude_scale = 111_320
    longitude_scale = 111_320 * cos(radians(reference_latitude))
    x = lon * longitude_scale
    y = lat * latitude_scale
    return x, y


def point_on_segment_projection(point, segment_start, segment_end):
    reference_latitude = (segment_start[0] + segment_end[0]) / 2
    px, py = project_to_local_xy(point, reference_latitude)
    ax, ay = project_to_local_xy(segment_start, reference_latitude)
    bx, by = project_to_local_xy(segment_end, reference_latitude)

    abx = bx - ax
    aby = by - ay
    apx = px - ax
    apy = py - ay

    denominator = abx * abx + aby * aby
    if denominator == 0:
        return segment_start, 0

    t = (apx * abx + apy * aby) / denominator
    t = max(0, min(1, t))

    projected_x = ax + t * abx
    projected_y = ay + t * aby

    latitude_scale = 111_320
    longitude_scale = 111_320 * cos(radians(reference_latitude))
    projected_lat = projected_y / latitude_scale
    projected_lon = projected_x / longitude_scale
    return (projected_lat, projected_lon), t


def build_real_neighborhood_graph():
    points = dict(REAL_NEIGHBORHOOD_POINTS)

    main_junction, position_fraction = point_on_segment_projection(
        points["Home"],
        points["Library"],
        points["Dunkin"],
    )
    points["Main_Junction"] = main_junction

    graph = Graph()
    for node, point in points.items():
        lat, lon = point
        graph.add_node(node, position=(lon, lat))

    graph.add_edge("Whittier", "Library", haversine_distance(points["Whittier"], points["Library"]))
    graph.add_edge(
        "Library",
        "Main_Junction",
        haversine_distance(points["Library"], points["Main_Junction"]),
    )
    graph.add_edge(
        "Main_Junction",
        "Dunkin",
        haversine_distance(points["Main_Junction"], points["Dunkin"]),
    )
    graph.add_edge("Home", "Main_Junction", haversine_distance(points["Home"], points["Main_Junction"]))

    return graph, points, position_fraction


def print_real_neighborhood_summary():
    graph, points, position_fraction = build_real_neighborhood_graph()

    print("Real neighborhood graph")
    print()
    print("Nodes")
    for name in sorted(points):
        lat, lon = points[name]
        print(f"  {name}: lat={lat:.12f}, lon={lon:.12f}")

    print()
    print("Edges")
    for start, end, weight in graph.edges():
        print(f"  {start} <-> {end}: {weight:.1f} meters")

    print()
    print(
        "Main_Junction lies "
        f"{position_fraction * 100:.1f}% of the way from Library toward Dunkin along the main road segment."
    )


def main():
    print_real_neighborhood_summary()


if __name__ == "__main__":
    main()
