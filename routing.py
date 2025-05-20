import networkx as nx
import osmnx as ox
import math
from heapq import heappush, heappop

def haversine_distance(u, v, G):
    lon1, lat1 = G.nodes[u]['x'], G.nodes[u]['y']
    lon2, lat2 = G.nodes[v]['x'], G.nodes[v]['y']
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)

    a = math.sin(dphi/2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    R = 6371000
    return R * c

def geocode_point(point):
    if isinstance(point, str):
        location = ox.geocoder.geocode(point)
        return (location[1], location[0])  # (lat, lng)
    elif isinstance(point, (list, tuple)) and len(point) == 2:
        return point
    else:
        raise ValueError("Input must be an address string or (lat, lng) tuple")

def astar_route(G, origin_point, destination_point, weight='weighted_length'):
    """
    Perform A* search on graph G from origin_point to destination_point.

    Parameters:
    - G: networkx.MultiDiGraph with nodes having 'x','y',
         and edges having a numerical attribute `weight` (e.g. 'weighted_length').
    - origin_point: tuple (lat, lng) or address string
    - destination_point: tuple (lat, lng) or address string
    - weight: edge attribute name to use as cost

    Returns:
    - node_path: list of node IDs from origin to destination
    - edge_path: list of (u, v, key) tuples representing the route's edges
    - road_names: list of road names to follow along the path
    """
    origin_point = geocode_point(origin_point)
    destination_point = geocode_point(destination_point)

    orig_node = ox.distance.nearest_nodes(G, X=origin_point[1], Y=origin_point[0])
    dest_node = ox.distance.nearest_nodes(G, X=destination_point[1], Y=destination_point[0])

    open_set = []
    heappush(open_set, (0, orig_node))
    came_from = {}

    g_score = {node: float('inf') for node in G.nodes}
    g_score[orig_node] = 0

    f_score = {node: float('inf') for node in G.nodes}
    f_score[orig_node] = haversine_distance(orig_node, dest_node, G)

    closed_set = set()

    while open_set:
        current_f, current = heappop(open_set)

        if current == dest_node:
            node_path = [current]
            while current in came_from:
                current = came_from[current]
                node_path.append(current)
            node_path = node_path[::-1]

            edge_path = []
            road_names = []
            for i in range(len(node_path) - 1):
                u, v = node_path[i], node_path[i + 1]
                min_key = min(G[u][v], key=lambda k: G[u][v][k].get(weight, G[u][v][k].get('length', 1)))
                edge_path.append((u, v, min_key))

                # Get road name
                name = G[u][v][min_key].get("name")
                if isinstance(name, list):
                    name = name[0]
                if not name:
                    name = "Unnamed Road"
                road_names.append(name)

            return node_path, edge_path, road_names

        closed_set.add(current)

        for nbr in G.neighbors(current):
            if nbr in closed_set:
                continue

            cost = float('inf')
            for key, data in G[current][nbr].items():
                edge_cost = data.get(weight, data.get('length', 1))
                cost = min(cost, edge_cost)

            tentative_g = g_score[current] + cost
            if tentative_g < g_score.get(nbr, float('inf')):
                came_from[nbr] = current
                g_score[nbr] = tentative_g
                f_score[nbr] = tentative_g + haversine_distance(nbr, dest_node, G)
                heappush(open_set, (f_score[nbr], nbr))

    raise nx.NetworkXNoPath(f"No path between {origin_point} and {destination_point}")
