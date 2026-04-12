from graph import Graph

def build_small_graph():
    g = Graph()
    g.add_edge("Depot", "A", 4)
    g.add_edge("Depot", "B", 2)
    g.add_edge("A", "C", 3)
    g.add_edge("B", "C", 5)
    g.add_edge("B", "D", 6)
    g.add_edge("C", "D", 1)
    return g

def build_greedy_fail_graph():
    g = Graph()

    g.add_edge("Depot", "A", 1)
    g.add_edge("Depot", "B", 2)
    g.add_edge("Depot", "C", 2)

    g.add_edge("A", "B", 2)
    g.add_edge("A", "C", 2)
    g.add_edge("B", "C", 4)

    return g


def build_three_delivery_graph():
    g = Graph()
    g.add_edge("Depot", "A", 2)
    g.add_edge("Depot", "B", 5)
    g.add_edge("A", "C", 2)
    g.add_edge("B", "D", 1)
    g.add_edge("C", "E", 6)
    g.add_edge("D", "E", 1)
    g.add_edge("A", "D", 7)
    g.add_edge("B", "C", 7)
    return g


def build_neighborhood_graph():
    g = Graph()

    positions = {
        "Home": (0, 0),
        "Pine&1st": (1, 1),
        "Pine&2nd": (2, 2),
        "Store": (4, 2),
        "Oak&1st": (1, -1),
        "Oak&2nd": (2, -2),
        "Pharmacy": (4, -2),
        "Center": (2, 0),
        "Park": (3, 0),
        "School": (5, 0),
    }

    for node, position in positions.items():
        g.add_node(node, position)

    g.add_edge("Home", "Pine&1st", 1.5)
    g.add_edge("Pine&1st", "Pine&2nd", 1.5)
    g.add_edge("Pine&2nd", "Store", 2.2)

    g.add_edge("Home", "Oak&1st", 1.4)
    g.add_edge("Oak&1st", "Oak&2nd", 1.6)
    g.add_edge("Oak&2nd", "Pharmacy", 2.1)

    g.add_edge("Home", "Center", 2.1)
    g.add_edge("Center", "Park", 1.0)
    g.add_edge("Park", "School", 2.0)

    g.add_edge("Pine&1st", "Center", 1.2)
    g.add_edge("Oak&1st", "Center", 1.3)
    g.add_edge("Pine&2nd", "Park", 1.4)
    g.add_edge("Oak&2nd", "Park", 1.5)
    g.add_edge("Store", "School", 2.3)
    g.add_edge("Pharmacy", "School", 2.4)
    g.add_edge("Store", "Park", 2.0)
    g.add_edge("Pharmacy", "Park", 2.2)

    return g
