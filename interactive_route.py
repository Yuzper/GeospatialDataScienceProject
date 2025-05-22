import streamlit as st
import folium
from streamlit_folium import st_folium
import routing_utils as ru

# Load the graph once
@st.cache_resource
def load_helper():
    G = ru.load_graph()
    return G

# Streamlit interface
st.info("Loading the graph...")
st.info("On a first load this can take 2-5 minutes, depending on computer processing power...")
G = load_helper()
st.title("Click to Select Origin and Destination in LA")
st.markdown("Click once inside the marked area to set the origin, and again to set the destination.")

# Initialize state for clicked points
if "origin" not in st.session_state:
    st.session_state.origin = None
if "destination" not in st.session_state:
    st.session_state.destination = None

map_center = [34.05, -118.25]  # Central LA
m = folium.Map(location=map_center, zoom_start=12)
m = ru.city_overlay_helper(m) # helper function to overlay LA city boundary

# Origin marker
if st.session_state.origin:
    folium.Marker(
        st.session_state.origin,
        tooltip="Origin",
        icon=folium.Icon(color="green")
    ).add_to(m)

# Destination marker
if st.session_state.destination:
    folium.Marker(
        st.session_state.destination,
        tooltip="Destination",
        icon=folium.Icon(color="red")
    ).add_to(m)

# Weather condition selection
st.markdown("### Select Current Weather Condition")
weather_options = [
    "Clear",
    "Partially cloudy",
    "Overcast",
    "Rain"
]
weather = st.selectbox("🌤️ Select current weather condition:", weather_options)


# Run routing if both points are selected
if st.session_state.origin and st.session_state.destination:
    try:
        # Get the path for both cost_risk and cost_time
        edge_path_risk = ru.path_finding(G, "cost_risk", st.session_state.origin, st.session_state.destination, weather=weather)
        edge_path_time = ru.path_finding(G, "cost_time", st.session_state.origin, st.session_state.destination, weather=weather)
        
        # Calculate total travel time for each route (in minutes)
        ru.plot_route(G, edge_path_risk, m, "cost_risk", st.session_state.origin, st.session_state.destination)
        ru.plot_route(G, edge_path_time, m, "cost_time", st.session_state.origin, st.session_state.destination)

        st.session_state.last_routed = (st.session_state.origin, st.session_state.destination, weather)
        
    except Exception as e:
        st.error(f"Routing failed: {e}")

# Show the map and get click data
click_data = st_folium(m, height=800, width=1200)

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
if st.button("Reset - Clear Origin and Destination"):
    st.session_state.origin = None
    st.session_state.destination = None
    st.rerun()
