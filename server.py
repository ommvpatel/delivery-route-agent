import json
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler
from pathlib import Path
from socketserver import TCPServer
from urllib.parse import urlparse

from importer import build_imported_real_neighborhood_graph
from planners import a_star_delivery_route
from planners import precompute_pairwise_shortest_paths


WEB_ROOT = Path(__file__).parent / "web"
HOST = "127.0.0.1"
PORT = 8000


def graph_to_route_geometry(graph, route_nodes):
    geometry = []

    if len(route_nodes) < 2:
        return geometry

    for start_node, end_node in zip(route_nodes, route_nodes[1:]):
        edge_geometry = graph.get_edge_geometry(start_node, end_node)
        if edge_geometry is None:
            start_position = graph.get_position(start_node)
            end_position = graph.get_position(end_node)
            if start_position is None or end_position is None:
                continue

            edge_geometry = [
                [start_position[1], start_position[0]],
                [end_position[1], end_position[0]],
            ]

        if not geometry:
            geometry.extend(edge_geometry)
            continue

        geometry.extend(edge_geometry[1:])

    return geometry


def solve_delivery_route(start, stops, cost_mode="distance"):
    graph = build_imported_real_neighborhood_graph(cost_mode=cost_mode)
    important_nodes = {start, *stops}
    pairwise_costs, pairwise_paths, _ = precompute_pairwise_shortest_paths(graph, important_nodes)

    delivery_order, full_route, total_cost, states_expanded = a_star_delivery_route(
        start,
        set(stops),
        pairwise_costs,
        pairwise_paths,
    )

    return {
        "start": start,
        "stops": sorted(stops),
        "delivery_order": list(delivery_order),
        "full_route": full_route,
        "route_geometry": graph_to_route_geometry(graph, full_route),
        "total_cost": total_cost,
        "states_expanded": states_expanded,
        "cost_mode": cost_mode,
        "cost_unit": "seconds" if cost_mode == "time" else "meters",
    }


class RoutePlannerHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(WEB_ROOT), **kwargs)

    def send_json(self, payload, status=HTTPStatus.OK):
        response = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(response)))
        self.end_headers()
        self.wfile.write(response)

    def do_GET(self):
        parsed = urlparse(self.path)

        if parsed.path == "/api/graph":
            graph = build_imported_real_neighborhood_graph()
            self.send_json(graph.to_dict())
            return

        super().do_GET()

    def do_POST(self):
        parsed = urlparse(self.path)

        if parsed.path != "/api/solve-route":
            self.send_error(HTTPStatus.NOT_FOUND, "Unknown API endpoint")
            return

        content_length = int(self.headers.get("Content-Length", "0"))
        raw_body = self.rfile.read(content_length)

        try:
            payload = json.loads(raw_body.decode("utf-8"))
            start = payload["start"]
            stops = payload["stops"]
            cost_mode = payload.get("cost_mode", "distance")
        except (json.JSONDecodeError, KeyError, TypeError):
            self.send_json({"error": "Invalid JSON payload."}, status=HTTPStatus.BAD_REQUEST)
            return

        if not start or not isinstance(start, str):
            self.send_json({"error": "A valid start node is required."}, status=HTTPStatus.BAD_REQUEST)
            return

        if not isinstance(stops, list) or not all(isinstance(stop, str) for stop in stops):
            self.send_json({"error": "Stops must be a list of node IDs."}, status=HTTPStatus.BAD_REQUEST)
            return

        if len(stops) == 0:
            self.send_json({"error": "At least one stop is required."}, status=HTTPStatus.BAD_REQUEST)
            return

        if start in stops:
            self.send_json({"error": "Start node cannot also be a stop."}, status=HTTPStatus.BAD_REQUEST)
            return

        if cost_mode not in {"distance", "time"}:
            self.send_json({"error": "cost_mode must be 'distance' or 'time'."}, status=HTTPStatus.BAD_REQUEST)
            return

        result = solve_delivery_route(start, stops, cost_mode=cost_mode)
        self.send_json(result)


def main():
    with TCPServer((HOST, PORT), RoutePlannerHandler) as httpd:
        print(f"Serving Route Planner at http://{HOST}:{PORT}")
        httpd.serve_forever()


if __name__ == "__main__":
    main()
