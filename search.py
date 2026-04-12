import heapq
import math

"""
compute shortest time to travel between two points
"""
def reconstruct_path(came_from, goal):
    path = [goal]
    current = goal

    while current in came_from:
        current = came_from[current]
        path.append(current)

    path.reverse()
    return path


def euclidean_heuristic(graph, node, goal):
    node_position = graph.get_position(node)
    goal_position = graph.get_position(goal)

    if node_position is None or goal_position is None:
        return 0

    x1, y1 = node_position
    x2, y2 = goal_position
    straight_line_distance = math.hypot(x2 - x1, y2 - y1)
    return straight_line_distance * heuristic_scale(graph)


def heuristic_scale(graph):
    cached_scale = graph.get_heuristic_scale()
    if cached_scale is not None:
        return cached_scale

    minimum_ratio = float("inf")

    for start, end, weight in graph.edges():
        start_position = graph.get_position(start)
        end_position = graph.get_position(end)

        if start_position is None or end_position is None:
            continue

        x1, y1 = start_position
        x2, y2 = end_position
        segment_length = math.hypot(x2 - x1, y2 - y1)

        if segment_length > 0:
            minimum_ratio = min(minimum_ratio, weight / segment_length)

    if minimum_ratio == float("inf"):
        graph.set_heuristic_scale(0)
        return 0

    graph.set_heuristic_scale(minimum_ratio)
    return minimum_ratio


def uniform_cost_search(graph, start, goal):
    pq = [(0, start)]
    best_cost = {start: 0}
    came_from = {}
    nodes_expanded = 0

    while pq:
        cost, node = heapq.heappop(pq)

        if cost > best_cost.get(node, float("inf")):
            continue

        nodes_expanded += 1

        if node == goal:
            return cost, reconstruct_path(came_from, goal), nodes_expanded

        for neighbor, weight in graph.neighbors(node):
            new_cost = cost + weight
            if new_cost < best_cost.get(neighbor, float("inf")):
                best_cost[neighbor] = new_cost
                came_from[neighbor] = node
                heapq.heappush(pq, (new_cost, neighbor))

    return float("inf"), [], nodes_expanded


def greedy_best_first_search(graph, start, goal, heuristic=euclidean_heuristic):
    pq = [(heuristic(graph, start, goal), start)]
    came_from = {}
    visited = set()
    nodes_expanded = 0

    while pq:
        _, node = heapq.heappop(pq)

        if node in visited:
            continue

        visited.add(node)
        nodes_expanded += 1

        if node == goal:
            path = reconstruct_path(came_from, goal)
            path_cost = path_total_cost(graph, path)
            return path_cost, path, nodes_expanded

        for neighbor, _ in graph.neighbors(node):
            if neighbor not in visited:
                if neighbor not in came_from:
                    came_from[neighbor] = node
                priority = heuristic(graph, neighbor, goal)
                heapq.heappush(pq, (priority, neighbor))

    return float("inf"), [], nodes_expanded


def a_star_search(graph, start, goal, heuristic=euclidean_heuristic):
    pq = [(heuristic(graph, start, goal), 0, start)]
    best_cost = {start: 0}
    came_from = {}
    nodes_expanded = 0

    while pq:
        _, g_cost, node = heapq.heappop(pq)

        if g_cost > best_cost.get(node, float("inf")):
            continue

        nodes_expanded += 1

        if node == goal:
            return g_cost, reconstruct_path(came_from, goal), nodes_expanded

        for neighbor, weight in graph.neighbors(node):
            tentative_g = g_cost + weight
            if tentative_g < best_cost.get(neighbor, float("inf")):
                best_cost[neighbor] = tentative_g
                came_from[neighbor] = node
                f_cost = tentative_g + heuristic(graph, neighbor, goal)
                heapq.heappush(pq, (f_cost, tentative_g, neighbor))

    return float("inf"), [], nodes_expanded


def path_total_cost(graph, path):
    if len(path) < 2:
        return 0

    total_cost = 0
    for current, nxt in zip(path, path[1:]):
        for neighbor, weight in graph.neighbors(current):
            if neighbor == nxt:
                total_cost += weight
                break

    return total_cost


def dijkstra(graph, start, goal):
    return uniform_cost_search(graph, start, goal)


