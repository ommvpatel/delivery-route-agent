from test_graphs import build_small_graph
from test_graphs import build_three_delivery_graph
from test_graphs import build_greedy_fail_graph
from planners import (
    precompute_pairwise_shortest_paths,
    greedy_delivery_route,
    brute_force_delivery_route,
)

def main():
    graph = build_greedy_fail_graph()
    start = "Depot"
    deliveries = {"A", "B", "C"}

    important_nodes = {start} | deliveries
    pairwise_costs, pairwise_paths, pairwise_stats = precompute_pairwise_shortest_paths(
        graph, important_nodes
    )

    greedy_order, greedy_route, greedy_cost = greedy_delivery_route(
        start, deliveries, pairwise_costs, pairwise_paths
    )

    optimal_order, optimal_route, optimal_cost = brute_force_delivery_route(
        start, deliveries, pairwise_costs, pairwise_paths
    )

    print("GREEDY")
    print("Order:", greedy_order)
    print("Route:", greedy_route)
    print("Cost:", greedy_cost)
    print()

    print("OPTIMAL")
    print("Order:", optimal_order)
    print("Route:", optimal_route)
    print("Cost:", optimal_cost)
    print()

    if greedy_cost == optimal_cost:
        print("Greedy matched optimal.")
    else:
        print("Greedy was suboptimal by", greedy_cost - optimal_cost)

if __name__ == "__main__":
    main()