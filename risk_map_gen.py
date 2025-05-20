import os
import pandas as pd
import osmnx as ox
from collections import defaultdict, deque


def fill_missing_edge_names_with_bfs(G, edge_to_name, max_depth=None):
    """
    Replaces 'Unnamed Road' edges with names from nearby connected edges via BFS.
    Modifies edge_to_name in-place.

    Parameters:
    - G: networkx.MultiDiGraph from OSMnx
    - edge_to_name: dict mapping (u, v, key) -> road name
    - max_depth: Optional[int] max BFS depth; None for unlimited
    """
    print("Filling in unnamed roads using BFS...")

    # Precompute named and unnamed edge sets
    named_edges = {edge for edge, name in edge_to_name.items() if name != 'Unnamed Road'}
    unnamed_edges = [edge for edge, name in edge_to_name.items() if name == 'Unnamed Road']

    for u, v, k in unnamed_edges:
        visited = set()
        queue = deque([(u, 0), (v, 0)])  # start from both endpoints
        found_name = None

        while queue:
            node, depth = queue.popleft()
            if node in visited:
                continue
            visited.add(node)

            if max_depth is not None and depth > max_depth:
                continue

            # Explore connected edges
            for nbr in G.neighbors(node):
                for key, data in G[node][nbr].items():
                    candidate = (node, nbr, key)
                    reverse = (nbr, node, key)

                    if candidate in named_edges:
                        found_name = edge_to_name[candidate]
                    elif reverse in named_edges:
                        found_name = edge_to_name[reverse]

                    if found_name:
                        break
                if found_name:
                    break

                if nbr not in visited:
                    queue.append((nbr, depth + 1))

            if found_name:
                break

        if found_name:
            edge_to_name[(u, v, k)] = found_name

    print("Unnamed roads updated.")


def main():
    # --- 1. Load accident data ---
    df = pd.read_csv('data/merged_data.csv')

    # --- 2. Load the road network graph ---
    print("Downloading street network...")
    G = ox.graph_from_place(
        'Los Angeles, California, USA', network_type='drive'
    )

    # --- 3. Match accidents to nearest road edges ---
    print("Matching accidents to roads...")
    edges = ox.distance.nearest_edges(
        G, X=df['Start_Lng'].values, Y=df['Start_Lat'].values
    )
    df['edge'] = list(edges)

    # --- 4. Build edge-to-name mapping ---
    edge_to_name = {}
    for u, v, k, data in G.edges(keys=True, data=True):
        name = data.get('name')
        if isinstance(name, list):
            name = name[0]
        elif not name:
            name = 'Unnamed Road'
        edge_to_name[(u, v, k)] = name

    # --- 5. Fill missing names via BFS ---
    fill_missing_edge_names_with_bfs(G, edge_to_name)

    # --- 6. Map edges to road names in DataFrame ---
    df['road_name'] = df['edge'].map(edge_to_name)

    # --- 7. Define target weather conditions ---
    target_conditions = [
        'Clear', 'Partially cloudy', 'Overcast', 'Rain',
        'Rain, Overcast', 'Rain, Partially cloudy'
    ]

    # --- 8. Ensure output directory exists ---
    output_dir = 'risk_maps'
    os.makedirs(output_dir, exist_ok=True)

    # --- 9. Compute and export risk maps per condition ---
    for condition_filter in target_conditions:
        print(f"Processing condition: {condition_filter}")

        # Filter rows exactly matching the condition
        df_filtered = df[df['conditions'] == condition_filter]

        # Count accidents per road under this condition
        road_risk_count = defaultdict(int)
        for road in df_filtered['road_name']:
            road_risk_count[road] += 1

        # Normalize risk scores between 0 and 1
        max_count = max(road_risk_count.values(), default=1)
        road_risk_score = {
            road: count / max_count
            for road, count in road_risk_count.items()
        }

        # Build DataFrame and save
        risk_df = pd.DataFrame(
            [{'road_name': road, 'risk_score': score}
             for road, score in road_risk_score.items()]
        ).sort_values(by='risk_score', ascending=False)

        filename = os.path.join(
            output_dir,
            f"{condition_filter.replace(', ', '_').replace(' ', '_')}.csv"
        )
        risk_df.to_csv(filename, index=False)
        print(f"Saved: {filename}")


if __name__ == '__main__':
    main()
