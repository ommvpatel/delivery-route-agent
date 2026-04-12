import time
from math import factorial

from planners import a_star_delivery_route
from planners import brute_force_delivery_route
from planners import greedy_delivery_route
from planners import precompute_pairwise_shortest_paths
from search import a_star_search
from search import greedy_best_first_search
from search import uniform_cost_search
from test_graphs import build_neighborhood_graph


def format_cost(value):
    return f"{value:.2f}"


def run_single_experiment(graph, start, goal, trials=200):
    algorithms = [
        ("UCS", uniform_cost_search),
        ("Greedy Best-First", greedy_best_first_search),
        ("A*", a_star_search),
    ]

    results = []

    for algorithm_name, algorithm in algorithms:
        cost, path, nodes_expanded = algorithm(graph, start, goal)

        start_time = time.perf_counter()
        for _ in range(trials):
            algorithm(graph, start, goal)
        elapsed_ms = ((time.perf_counter() - start_time) * 1000) / trials

        results.append(
            {
                "algorithm": algorithm_name,
                "cost": cost,
                "path": path,
                "nodes_expanded": nodes_expanded,
                "elapsed_ms": elapsed_ms,
            }
        )

    return results


def print_experiment_results(start, goal, results):
    print(f"Route query: {start} -> {goal}")

    for result in results:
        print(result["algorithm"])
        print(f"  Cost: {format_cost(result['cost'])}")
        print(f"  Path: {' -> '.join(result['path'])}")
        print(f"  Nodes expanded: {result['nodes_expanded']}")
        print(f"  Average runtime: {result['elapsed_ms']:.4f} ms")

    print()


def run_delivery_experiment(graph, start, deliveries, trials=200):
    important_nodes = set(deliveries) | {start}
    pairwise_costs, pairwise_paths, pairwise_stats = precompute_pairwise_shortest_paths(
        graph, important_nodes
    )

    algorithms = [
        (
            "Greedy Delivery",
            lambda: greedy_delivery_route(start, deliveries, pairwise_costs, pairwise_paths),
        ),
        (
            "Brute Force Optimal",
            lambda: brute_force_delivery_route(start, deliveries, pairwise_costs, pairwise_paths),
        ),
        (
            "Delivery A*",
            lambda: a_star_delivery_route(start, deliveries, pairwise_costs, pairwise_paths),
        ),
    ]

    results = []

    for algorithm_name, algorithm in algorithms:
        output = algorithm()

        start_time = time.perf_counter()
        for _ in range(trials):
            algorithm()
        elapsed_ms = ((time.perf_counter() - start_time) * 1000) / trials

        if algorithm_name == "Delivery A*":
            order, full_route, total_cost, states_expanded = output
        else:
            order, full_route, total_cost = output
            states_expanded = None

        results.append(
            {
                "algorithm": algorithm_name,
                "order": list(order) if order is not None else None,
                "full_route": full_route,
                "total_cost": total_cost,
                "states_expanded": states_expanded,
                "elapsed_ms": elapsed_ms,
            }
        )

    pairwise_expansions = sum(pairwise_stats.values())
    return results, pairwise_expansions


def print_delivery_results(start, deliveries, results, pairwise_expansions):
    print("Delivery Planning Comparison")
    print(f"Start: {start}")
    print(f"Stops: {', '.join(sorted(deliveries))}")
    print(f"Pairwise preprocessing node expansions: {pairwise_expansions}")
    print(f"Brute-force route orders checked: {factorial(len(deliveries))}")
    print()

    optimal_cost = min(result["total_cost"] for result in results)

    for result in results:
        print(result["algorithm"])
        print(f"  Stop order: {' -> '.join(result['order'])}")
        print(f"  Full route: {' -> '.join(result['full_route'])}")
        print(f"  Total cost: {format_cost(result['total_cost'])}")
        print(f"  Cost above optimum: {format_cost(result['total_cost'] - optimal_cost)}")
        if result["states_expanded"] is not None:
            print(f"  Search states expanded: {result['states_expanded']}")
        print(f"  Average runtime: {result['elapsed_ms']:.4f} ms")

    print()


def main():
    graph = build_neighborhood_graph()
    pathfinding_queries = [
        ("Home", "Store"),
        ("Home", "Pharmacy"),
        ("Home", "School"),
        ("Store", "Pharmacy"),
    ]
    delivery_start = "Home"
    delivery_stops = {"Park", "Store", "School", "Pharmacy"}

    print("Pathfinding Comparison on Neighborhood Graph")
    print("Each runtime is averaged over repeated runs to reduce noise.")
    print()

    for start, goal in pathfinding_queries:
        results = run_single_experiment(graph, start, goal)
        print_experiment_results(start, goal, results)

    delivery_results, pairwise_expansions = run_delivery_experiment(
        graph, delivery_start, delivery_stops
    )
    print_delivery_results(
        delivery_start,
        delivery_stops,
        delivery_results,
        pairwise_expansions,
    )


if __name__ == "__main__":
    main()
