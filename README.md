# GeospatialDataScienceProject
This repository is for our project in the Geospatial Data Science course at ITU, masters in Data Science.


# Running our prototype routing:
cd to root directory, same as interactive_route.py


commandline:
streamlit run interactive_route.py

Will open a browser window running a local server, the loading of LA roads graph may take some time on the first load (2-5 minutes, depending on computer processing power). After that it should only take a second to calculate the routes.

To create a route, click anywhere within the marked LA area as origin spot, then another within as destination and it will calculate the fastest route (blue) and the route with minimal risk (green, can be orange and red segments if they are more risky).

