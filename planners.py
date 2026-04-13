from search import dijkstra
import itertools
import heapq


def delivery_mst_lower_bound(nodes, pairwise_costs):
    if len(nodes) <= 1:
        return 0

    remaining = set(nodes)
    start = min(remaining)
    remaining.remove(start)
    visited = {start}
    total_cost = 0

    edge_queue = []
    for node in remaining:
        heapq.heappush(edge_queue, (pairwise_costs[(start, node)], start, node))

    while remaining and edge_queue:
        cost, _, destination = heapq.heappop(edge_queue)
        if destination in visited:
            continue

        visited.add(destination)
        remaining.remove(destination)
        total_cost += cost

        for node in remaining:
            heapq.heappush(edge_queue, (pairwise_costs[(destination, node)], destination, node))

    return total_cost


def delivery_heuristic(current_node, remaining, pairwise_costs):
    if not remaining:
        return 0

    connection_cost = min(pairwise_costs[(current_node, node)] for node in remaining)
    mst_cost = delivery_mst_lower_bound(remaining, pairwise_costs)
    return connection_cost + mst_cost

"""
greedy algorithm that
start at depot
among unvisited deliveries, choose the one with lowest shortest-path cost from current location
move there
repeat until all deliveries are done
"""
def greedy_delivery_route(start, deliveries, pairwise_costs, pairwise_paths):
    current = start
    remaining = set(deliveries)
    delivery_order = []
    full_route = [start]
    total_cost = 0

    while remaining:
        best_target = None
        best_cost = float("inf")

        for target in sorted(remaining):
            cost = pairwise_costs[(current, target)]
            if cost < best_cost:
                best_cost = cost
                best_target = target

        total_cost += best_cost
        delivery_order.append(best_target)

        path_segment = pairwise_paths[(current, best_target)]
        if len(path_segment) > 1:
            full_route.extend(path_segment[1:])

        current = best_target
        remaining.remove(best_target)

    return delivery_order, full_route, total_cost



def precompute_pairwise_shortest_paths(graph, important_nodes):
    pairwise_costs = {}
    pairwise_paths = {}
    pairwise_stats = {}

    for start in sorted(important_nodes):
        for goal in sorted(important_nodes):
            if start == goal:
                pairwise_costs[(start, goal)] = 0
                pairwise_paths[(start, goal)] = [start]
                pairwise_stats[(start, goal)] = 0
            else:
                cost, path, nodes_expanded = dijkstra(graph, start, goal)
                pairwise_costs[(start, goal)] = cost
                pairwise_paths[(start, goal)] = path
                pairwise_stats[(start, goal)] = nodes_expanded

    return pairwise_costs, pairwise_paths, pairwise_stats


def brute_force_delivery_route(start, deliveries, pairwise_costs, pairwise_paths):
    best_order = None
    best_cost = float("inf")
    best_full_route = []

    for order in itertools.permutations(sorted(deliveries)):
        total_cost = 0
        current = start
        full_route = [start]

        for destination in order:
            total_cost += pairwise_costs[(current, destination)]
            path_segment = pairwise_paths[(current, destination)]

            if len(path_segment) > 1:
                full_route.extend(path_segment[1:])

            current = destination

        if total_cost < best_cost:
            best_cost = total_cost
            best_order = order
            best_full_route = full_route

    return best_order, best_full_route, best_cost


def informed_delivery_route(start, deliveries, pairwise_costs, pairwise_paths, heuristic_fn):
    all_deliveries = frozenset(deliveries)
    start_state = (start, frozenset())

    pq = []
    heapq.heappush(pq, (0, 0, start_state, [start]))  
    

    best_g = {start_state: 0}
    nodes_expanded = 0

    while pq:
        f, g, state, delivery_order = heapq.heappop(pq)
        current_node, visited = state

        if visited == all_deliveries:
            full_route = [start]
            route_node = start

            for destination in delivery_order[1:]:
                path_segment = pairwise_paths[(route_node, destination)]
                if len(path_segment) > 1:
                    full_route.extend(path_segment[1:])
                route_node = destination

            return delivery_order[1:], full_route, g, nodes_expanded

        if g > best_g.get(state, float("inf")):
            continue

        nodes_expanded += 1

        remaining = all_deliveries - visited
        for next_delivery in sorted(remaining):
            new_visited = frozenset(set(visited) | {next_delivery})
            new_state = (next_delivery, new_visited)

            step_cost = pairwise_costs[(current_node, next_delivery)]
            new_g = g + step_cost
            new_remaining = all_deliveries - new_visited
            h = heuristic_fn(next_delivery, new_remaining, pairwise_costs)
            new_f = new_g + h

            if new_g < best_g.get(new_state, float("inf")):
                best_g[new_state] = new_g
                heapq.heappush(
                    pq,
                    (new_f, new_g, new_state, delivery_order + [next_delivery])
                )

    return None, [], float("inf"), nodes_expanded


def uniform_cost_delivery_route(start, deliveries, pairwise_costs, pairwise_paths):
    return informed_delivery_route(
        start,
        deliveries,
        pairwise_costs,
        pairwise_paths,
        heuristic_fn=lambda current_node, remaining, costs: 0,
    )


def a_star_delivery_route(start, deliveries, pairwise_costs, pairwise_paths):
    return informed_delivery_route(
        start,
        deliveries,
        pairwise_costs,
        pairwise_paths,
        heuristic_fn=delivery_heuristic,
    )
