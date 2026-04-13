import time

import json
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler
from pathlib import Path
from socketserver import TCPServer
from urllib.parse import urlparse

from importer import build_active_graph
from importer import detect_active_graph_source
from planners import a_star_delivery_route
from planners import greedy_delivery_route
from planners import precompute_pairwise_shortest_paths
from planners import uniform_cost_delivery_route


WEB_ROOT = Path(__file__).parent / "web"
HOST = "127.0.0.1"
PORT = 8000
ALGORITHM_PREFERENCE = {"A*": 0, "UCS": 1, "Greedy": 2}


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
    source_info = detect_active_graph_source()
    graph = build_active_graph(cost_mode=cost_mode)
    important_nodes = {start, *stops}
    pairwise_costs, pairwise_paths, _ = precompute_pairwise_shortest_paths(graph, important_nodes)

    def run_algorithm(name, algorithm):
        start_time = time.perf_counter()
        result = algorithm(start, set(stops), pairwise_costs, pairwise_paths)
        elapsed_ms = (time.perf_counter() - start_time) * 1000

        if name == "Greedy":
            delivery_order, full_route, total_cost = result
            states_expanded = None
        else:
            delivery_order, full_route, total_cost, states_expanded = result

        return {
            "name": name,
            "delivery_order": list(delivery_order) if delivery_order is not None else None,
            "full_route": full_route,
            "route_geometry": graph_to_route_geometry(graph, full_route),
            "total_cost": total_cost,
            "states_expanded": states_expanded,
            "runtime_ms": elapsed_ms,
        }

    comparisons = [
        run_algorithm("Greedy", greedy_delivery_route),
        run_algorithm("UCS", uniform_cost_delivery_route),
        run_algorithm("A*", a_star_delivery_route),
    ]

    connected_results = [result for result in comparisons if result["delivery_order"] is not None]
    if not connected_results:
        raise ValueError("No connected route exists for the selected start and stops.")

    best_result = min(
        connected_results,
        key=lambda result: (result["total_cost"], ALGORITHM_PREFERENCE.get(result["name"], 99)),
    )

    optimal_cost = min(result["total_cost"] for result in connected_results)
    for result in comparisons:
        if result["delivery_order"] is None:
            result["cost_above_best"] = None
        else:
            result["cost_above_best"] = result["total_cost"] - optimal_cost

    return {
        "start": start,
        "stops": sorted(stops),
        "delivery_order": best_result["delivery_order"],
        "full_route": best_result["full_route"],
        "route_geometry": best_result["route_geometry"],
        "total_cost": best_result["total_cost"],
        "states_expanded": best_result["states_expanded"],
        "cost_mode": cost_mode,
        "cost_unit": "seconds" if cost_mode == "time" else "meters",
        "comparison_results": comparisons,
        "best_algorithm": best_result["name"],
        "graph_source": source_info,
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
            source_info = detect_active_graph_source()
            graph = build_active_graph()
            payload = graph.to_dict()
            payload["graph_source"] = source_info
            self.send_json(payload)
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

        try:
            result = solve_delivery_route(start, stops, cost_mode=cost_mode)
        except ValueError as error:
            self.send_json({"error": str(error)}, status=HTTPStatus.BAD_REQUEST)
            return

        self.send_json(result)


def main():
    with TCPServer((HOST, PORT), RoutePlannerHandler) as httpd:
        print(f"Serving Route Planner at http://{HOST}:{PORT}")
        httpd.serve_forever()


if __name__ == "__main__":
    main()
