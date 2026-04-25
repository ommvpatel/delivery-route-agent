# delivery-route-agent


This project is a map-based delivery route planner built with classical AI search algorithms on top of a real road network. It uses OpenStreetMap data to construct a weighted graph where intersections are represented as nodes and road segments are represented as edges. Routes can be optimized for either total distance or estimated travel time, with support for one-way roads, speed limits, and small stop-sign and traffic-signal penalties in time mode.

The system solves the problem in two layers. First, it computes shortest paths between the selected start location and delivery stops. Then, it solves the higher-level multi-stop routing problem by determining the best order to visit those stops. The project compares Greedy, Uniform Cost Search (UCS), and A* to analyze the tradeoff between runtime, search effort, and route quality.

A Leaflet-based web interface allows users to visualize the imported road graph, select stops directly on the map, solve the route, and compare algorithm results side by side. The project is designed to demonstrate how classical AI search and planning methods can be applied to a realistic delivery-routing problem using real-world map data.
