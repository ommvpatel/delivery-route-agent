from math import atan2
from math import cos
from math import radians
from math import sin
from math import sqrt


EARTH_RADIUS_METERS = 6_371_000


class Graph:
    def __init__(self):
        self.adj = {}
        self.positions = {}
        self.edge_records = []
        self._heuristic_scale_cache = None

    def add_node(self, node, position=None):
        if node not in self.adj:
            self.adj[node] = []
        if position is not None:
            self.positions[node] = position
        self._heuristic_scale_cache = None

    def set_position(self, node, position):
        self.add_node(node)
        self.positions[node] = position
        self._heuristic_scale_cache = None

    def get_position(self, node):
        return self.positions.get(node)

    def geometry_length(self, geometry):
        if geometry is None or len(geometry) < 2:
            return 0

        total_length = 0
        for start, end in zip(geometry, geometry[1:]):
            lat1, lon1 = start
            lat2, lon2 = end

            start_radians = (radians(lat1), radians(lon1))
            end_radians = (radians(lat2), radians(lon2))
            dlat = end_radians[0] - start_radians[0]
            dlon = end_radians[1] - start_radians[1]

            a = sin(dlat / 2) ** 2 + cos(start_radians[0]) * cos(end_radians[0]) * sin(dlon / 2) ** 2
            c = 2 * atan2(sqrt(a), sqrt(1 - a))
            total_length += EARTH_RADIUS_METERS * c

        return total_length

    def add_edge(
        self,
        u,
        v,
        weight=None,
        u_position=None,
        v_position=None,
        geometry=None,
        bidirectional=True,
        metadata=None,
    ):
        self.add_node(u, u_position)
        self.add_node(v, v_position)

        if geometry is None:
            u_position_value = self.get_position(u)
            v_position_value = self.get_position(v)
            if u_position_value is not None and v_position_value is not None:
                geometry = [
                    [u_position_value[1], u_position_value[0]],
                    [v_position_value[1], v_position_value[0]],
                ]

        if weight is None:
            weight = self.geometry_length(geometry)

        self.adj[u].append((v, weight))
        if bidirectional:
            self.adj[v].append((u, weight))

        self.edge_records.append({
            "from": u,
            "to": v,
            "weight": weight,
            "geometry": geometry,
            "bidirectional": bidirectional,
            "metadata": metadata or {},
        })
        self._heuristic_scale_cache = None

    def neighbors(self, node):
        return self.adj.get(node, [])

    def nodes(self):
        return list(self.adj.keys())

    def edges(self):
        for edge_record in self.edge_records:
            yield edge_record["from"], edge_record["to"], edge_record["weight"]

    def get_edge_record(self, u, v):
        for edge_record in self.edge_records:
            if edge_record["from"] == u and edge_record["to"] == v:
                return edge_record
            if edge_record["bidirectional"] and edge_record["from"] == v and edge_record["to"] == u:
                return edge_record

        return None

    def get_edge_geometry(self, u, v):
        edge_record = self.get_edge_record(u, v)
        if edge_record is None:
            return None

        geometry = edge_record.get("geometry")
        if geometry is None:
            return None

        if edge_record["from"] == u and edge_record["to"] == v:
            return geometry

        return list(reversed(geometry))

    def get_heuristic_scale(self):
        return self._heuristic_scale_cache

    def set_heuristic_scale(self, scale):
        self._heuristic_scale_cache = scale

    def to_dict(self):
        nodes = []
        for node in sorted(self.nodes()):
            position = self.get_position(node)
            node_entry = {"id": node}
            if position is not None:
                x, y = position
                node_entry["x"] = x
                node_entry["y"] = y
            nodes.append(node_entry)

        edges = []
        for edge_record in self.edge_records:
            edge_entry = {
                "from": edge_record["from"],
                "to": edge_record["to"],
                "weight": edge_record["weight"],
                "bidirectional": edge_record["bidirectional"],
            }
            if edge_record["geometry"] is not None:
                edge_entry["geometry"] = edge_record["geometry"]
            if edge_record["metadata"]:
                edge_entry["metadata"] = edge_record["metadata"]
            edges.append(edge_entry)

        return {"nodes": nodes, "edges": edges}
    
    def __str__(self):
        return str(self.adj)
