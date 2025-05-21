import streamlit as st
import folium
from streamlit_folium import st_folium
import osmnx as ox
from shapely.geometry import LineString
from routing import astar_route  # Your A* pathfinding function

# Load the graph once
@st.cache_resource
def load_graph():
    return ox.graph_from_place("Los Angeles, California, USA", network_type="drive")

G = load_graph()

# Precompute costs (use real risk model here if available)
for u, v, k, data in G.edges(keys=True, data=True):
    length = data.get("length", 1.0)
    data["cost_distance"] = length
    data["cost_risk"] = length  # Replace with risk logic if needed

# Streamlit interface
st.title("Click to Select Origin and Destination in LA")
st.markdown("Click once to set the origin, and again to set the destination.")

# Initialize state for clicked points
if "origin" not in st.session_state:
    st.session_state.origin = None
if "destination" not in st.session_state:
    st.session_state.destination = None

# Base map
map_center = [34.05, -118.25]  # Central LA
m = folium.Map(location=map_center, zoom_start=12)

# Display existing markers
if st.session_state.origin:
    folium.Marker(
        st.session_state.origin,
        tooltip="Origin",
        icon=folium.Icon(color="green")
    ).add_to(m)

if st.session_state.destination:
    folium.Marker(
        st.session_state.destination,
        tooltip="Destination",
        icon=folium.Icon(color="red")
    ).add_to(m)

# Run routing if both points are selected
if st.session_state.origin and st.session_state.destination:
    try:
        node_path, edge_path, road_names = astar_route(
            G,
            origin_point=st.session_state.origin,
            destination_point=st.session_state.destination,
            weight="cost_risk"
        )

        # Draw the route
        for u, v, k in edge_path:
            data = G.edges[u, v, k]
            if "geometry" in data:
                line = data["geometry"]
            else:
                point_u = (G.nodes[u]["y"], G.nodes[u]["x"])
                point_v = (G.nodes[v]["y"], G.nodes[v]["x"])
                line = LineString([point_u, point_v])

            folium.PolyLine(
                [(lat, lon) for lon, lat in line.coords],
                color="red", weight=5, opacity=0.8
            ).add_to(m)

        st.markdown("### Route:")
        st.write(road_names)

    except Exception as e:
        st.error(f"Routing failed: {e}")

# Show the map and get click data
click_data = st_folium(m, height=500, width=700)

# Handle new click
if click_data and click_data.get("last_clicked"):
    clicked_point = (
        click_data["last_clicked"]["lat"],
        click_data["last_clicked"]["lng"]
    )

    if not st.session_state.origin:
        st.session_state.origin = clicked_point
        st.rerun()
    elif not st.session_state.destination:
        st.session_state.destination = clicked_point
        st.rerun()

# Reset button
if st.button("Reset"):
    st.session_state.origin = None
    st.session_state.destination = None
    st.rerun()
