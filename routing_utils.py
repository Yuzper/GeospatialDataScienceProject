import osmnx as ox
import pandas as pd
from routing import astar_route
import folium
import matplotlib.pyplot as plt
import os

def load_graph():
    # Load the LA driving graph
    places = [
        "Los Angeles, California, USA",
        "Santa Monica, California, USA",
        "Beverly Hills, California, USA",
        "West Hollywood, California, USA",
        "Culver City, California, USA",
        "Inglewood, California, USA",
        "Glendale, California, USA",
        "Burbank, California, USA",
        "Pasadena, California, USA"
    ]

    if not os.path.exists("data/la.graphml"):
        # Download the graph and save it to a file
        G = ox.graph_from_place(places, network_type="drive")
        ox.save_graphml(G, "data/la.graphml")

    else:
        G = ox.load_graphml("data/la.graphml")
    return G


def city_overlay_helper(m):
    places = [
        "Los Angeles, California, USA",
        "Santa Monica, California, USA",
        "Beverly Hills, California, USA",
        "West Hollywood, California, USA",
        "Culver City, California, USA",
        "Inglewood, California, USA",
        "Glendale, California, USA",
        "Burbank, California, USA",
        "Pasadena, California, USA"
    ]
    for place in places:
        gdf = ox.geocode_to_gdf(place)
        folium.GeoJson(
            gdf.geometry.iloc[0],
            name=place,
            style_function=lambda x: {
                'color': 'blue',
                'weight': 2,
                'fillOpacity': 0.15
            }
        ).add_to(m)
    return m



def get_edge_data(G, weather="Clear"): # Pick one of: Clear, Partially cloudy, Overcast, Rain
    risk_csv = os.path.join("risk_maps/", f"{weather.replace(', ', '_').replace(' ', '_')}.csv")
    risk_df = pd.read_csv(risk_csv)
    risk_lookup = dict(zip(risk_df["road_name"], risk_df["risk_score"]))

    for u, v, key, data in G.edges(keys=True, data=True):
        # Length
        length = data.get("length", 1.0)
        data["cost_distance"] = length

        # Risk
        name = data.get("name")
        if isinstance(name, list): name = name[0]
        if not name: name = "Unnamed Road"
        risk = risk_lookup.get(name, 0.0)
        data["cost_risk"] = length * (1 + risk)

        # Time (travel time in hours)
        maxspeed = data.get("maxspeed")
        if isinstance(maxspeed, list):
            try:
                maxspeed = float(maxspeed[0])
            except: maxspeed = None
        try:
            maxspeed = float(maxspeed)
        except:
            maxspeed = None
        if not maxspeed or maxspeed <= 0:
            maxspeed = 50  # Default speed in km/h

        time_hours = (length / 1000) / maxspeed
        data["cost_time"] = time_hours
    return G

def path_finding(G, cost_attribute, origin, dest, weather):
    G = get_edge_data(G, weather)

    # Compute the route based on the selected cost attribute
    node_path, edge_path, road_names = astar_route(
        G,
        origin_point=origin,
        destination_point=dest,
        weight=cost_attribute,
    )
    
    print(node_path)
    print(f"Number of nodes in path {cost_attribute}: {len(node_path)}")
    print(f"Number of edges in path {cost_attribute}: {len(edge_path)}")
    print(f"Roads to follow {cost_attribute}: ", road_names)
    return edge_path

def plot_route(G, edge_path, m, cost_attribute, origin, dest):
    counter = -1
    for u, v, key in edge_path:
        data = G.edges[u, v, key]
        counter += 1

        # Determine geometry
        if 'geometry' in data:
            line = data['geometry']
            coords = [(lat, lon) for lon, lat in line.coords]
        else:
            point_u = (G.nodes[u]['y'], G.nodes[u]['x'])
            point_v = (G.nodes[v]['y'], G.nodes[v]['x'])
            coords = [point_u, point_v]
    
        # Determine color and popup based on cost type
        if cost_attribute == "cost_risk":
            length = data.get("length", 1.0)
            cost_risk = data.get("cost_risk", length)
            base_risk = (cost_risk / length) - 1
            color = risk_to_color(base_risk)
            if counter == 0:
                first_color = color
            elif counter == len(edge_path) - 1:
                last_color = color
            popupString = f"{data.get('name', 'Unnamed Road')}<br>Risk: {base_risk:.2f}"
            
        else:
            color = "blue"
            if counter == 0:
                first_color = color
            elif counter == len(edge_path) - 1:
                last_color = color
            popupString = f"{data.get('name', 'Unnamed Road')}<br>Fastest Route"

        folium.PolyLine(
            locations=coords,
            color=color,
            weight=5,
            opacity=0.8,
            popup=popupString
        ).add_to(m)

    
    first_u, first_v, first_key = edge_path[0]
    data_first = G.edges[first_u, first_v, first_key]
    last_u, last_v, last_key = edge_path[-1]
    data_last = G.edges[last_u, last_v, last_key]

    if 'geometry' in data_last:
        last_coords = (data_last['geometry'].coords[-1][1], data_last['geometry'].coords[-1][0])  # (lat, lon)
    else:
        last_coords = (G.nodes[last_v]['y'], G.nodes[last_v]['x'])  # fallback if no geometry
    if 'geometry' in data_first:
        first_node_coords = (data_first['geometry'].coords[0][1], data_first['geometry'].coords[0][0])  # (lat, lon)
    else:
        first_node_coords = (G.nodes[first_u]['y'], G.nodes[first_u]['x'])


    # Add the start coords to first node line and end coords to last node line
    folium.PolyLine(locations=[origin, first_node_coords],
                    color=first_color,
                    weight=5,
                    opacity=0.8,
                    popup=popupString
                    ).add_to(m)
    

    folium.PolyLine(locations=[last_coords, dest],
                color=last_color,
                weight=5,
                opacity=0.8,
                popup=popupString
                ).add_to(m)
    
    # Add start and end markers
    folium.Marker(origin, tooltip="Start", icon=folium.Icon(color="green")).add_to(m)
    folium.Marker(dest, tooltip="Destination", icon=folium.Icon(color="red")).add_to(m)


# Define a color scale for risk (0.0 = green, 1.0+ = red)
def risk_to_color(risk):
    # Clamp risk between 0 and 1
    risk = min(max(risk, 0), 1)
    # Use a color map (green to red)
    cmap = plt.get_cmap("RdYlGn_r")  # reverse of green→red
    r, g, b, _ = cmap(risk)
    return f'#{int(r*255):02x}{int(g*255):02x}{int(b*255):02x}'


def VisualizeMap(G, origin, dest, weather):
    edge_path = path_finding(G, "cost_risk", origin, dest, weather)
    edge_path_fast = path_finding(G, "cost_time", origin, dest, weather)
    # Calculate total travel time for each route (in minutes)
    total_time_risk = sum(G.edges[u, v, key]["cost_time"] for u, v, key in edge_path) * 60
    total_time_fast = sum(G.edges[u, v, key]["cost_time"] for u, v, key in edge_path_fast) * 60

    # Create a folium map centered on the origin
    m = folium.Map(location=origin, zoom_start=13)
    m = city_overlay_helper(m) # helper function to overlay LA city boundary

    plot_route(G, edge_path, m, "cost_risk", origin, dest)
    plot_route(G, edge_path_fast, m, "cost_time", origin, dest)



    # Add info box with travel times
    info_html = f"""
    <div style="position: fixed; 
                top: 10px; left: 60px; width: 250px; height: 100px; 
                background-color: white; z-index:9999; font-size:14px;
                border:2px solid grey; padding: 10px;">
    <b>Route Time Estimates</b><br>
    <span style='color:black;'>Safest route: </span>{total_time_risk:.1f} min<br>
    <span style='color:blue;'>Fastest route: </span>{total_time_fast:.1f} min
    </div>
    """
    m.get_root().html.add_child(folium.Element(info_html))

    # Risk legend
    legend_html = """
    <div style="position: fixed; 
                top: 10px; left: 280px; width: 150px; height: 100px; 
                background-color: white; z-index:9999; font-size:14px;
                border:2px solid grey; padding: 10px;">
    <b>Risk Level</b><br>
    <span style="color:#00ff00;">●</span> Low<br>
    <span style="color:#ffff00;">●</span> Medium<br>
    <span style="color:#ff0000;">●</span> High
    </div>
    """
    m.get_root().html.add_child(folium.Element(legend_html))


    # Map styles
    folium.TileLayer(titles = "Stamen Terrain").add_to(m)
    folium.TileLayer("CartoDB Positron").add_to(m)
    folium.TileLayer("openstreetmap").add_to(m)
    folium.LayerControl().add_to(m)

    # Save to HTML
    m.save("risky_path.html")
    print("Map saved to risky_path.html")


