# -*- coding: utf-8 -*-

import pandas as pd
import numpy as np
import folium
import random
import math
from folium import plugins
import bisect
from geopy.distance import distance
from geopy.distance import geodesic
from math import sin, cos, sqrt, atan2, radians


def getroute(start_lat, start_lon, destination_lat, destination_lon):

    def get_inner_points(lat1, lon1, lat2, lon2, meters=100):

        res_list = [(lat1, lon1)]
        dist = 110*1000*((lat1-lat2)**2 + (lon1-lon2)**2)**0.5
        n_chunks = int(dist/meters)
        if n_chunks > 0:
            dlat = (lat2-lat1)/n_chunks
            dlon = (lon2-lon1)/n_chunks
            for di in range(1, n_chunks+1):
                next_lat = lat1 + dlat*di
                next_lon = lon1 + dlon*di
                res_list.append((next_lat, next_lon))
        res_list.append((lat2, lon2))

        return res_list

    def get_sq(lat, lon, diff=0.0001, num=2):
        res_list = []
        for i in range(-num, num+1):
            for j in range(-num, num+1):
                res_list.append((lat+diff*i, lon+diff*j))

        return res_list

    def find_in_sorted_list(elem, sorted_list):
        'Locate the leftmost value exactly equal to x'
        i = bisect.bisect_left(sorted_list, elem)
        if i != len(sorted_list) and sorted_list[i] == elem:
            return i
        return -1

    def in_sorted_list(elem, sorted_list):
        i = bisect.bisect_left(sorted_list, elem)
        return i != len(sorted_list) and sorted_list[i] == elem

    route_path = 'data/route_stations(full).csv'
    bus_path = 'data/bus_routes.csv'
    bus_stop = 'data/busstops-dat.csv'
    route_station = pd.read_csv(route_path)
    bus_route = pd.read_csv(bus_path)
    bstops = pd.read_csv(bus_stop)
    bstops.set_index('stopid', inplace=True)
    route_station['lat'] = route_station['sid'].apply(
        lambda x: bstops.loc[x, 'lat'] if x in bstops.index else None)
    route_station['lon'] = route_station['sid'].apply(
        lambda x: bstops.loc[x, 'lon'] if x in bstops.index else None)
    route_station['name_e'] = route_station['sid'].apply(
        lambda x: bstops.loc[x, 'name_e'] if x in bstops.index else None)
    b_145 = route_station[route_station['route_id'] == '145']
    x = bus_route[bus_route['route_id'] == '145']
    rinfo = x.iloc[0]
    rpath = eval(rinfo['polyline'])
    new_rpath = []

    for ix, val in enumerate(rpath[:-1]):
        lat1, lon1 = val
        lat2, lon2 = rpath[ix+1]
        # ใช้ innner points
        rd10 = get_inner_points(lat1, lon1, lat2, lon2, 10)
        rd10sq = []
        # แล้วต่อด้วย square
        for latlon in rd10:
            lat, lon = latlon
            rd10sq += get_sq(lat, lon, num=1)

        new_rpath += [(round(x[0], 4), round(x[1], 4)) for x in rd10sq]
    new_rpath = list(set(new_rpath))

    route_station_145 = route_station[(route_station['route_id'] == '145') & (
        route_station['path_type'] == 'main')]
    route_station_145

    BSTOP_LOOKUP = {}
    for index, row in route_station_145 .iterrows():
        stopid = row['sid']
        lat = row['lat']
        lon = row['lon']

        sq_latlons = get_sq(lat, lon, num=2)

        route_station_145.loc[index, 'sqs'] = str(sq_latlons)

        for xlat, xlon in sq_latlons:
            xkey = str(round(xlat, 4)) + '-' + str(round(xlon, 4))
            BSTOP_LOOKUP[xkey] = stopid

    route_station_145

    """# LATLON START & DESTINATION

    """

    # start_lat = 13.623538481929756
    # start_lon = 100.62092075434273

    # start_lat = 13.807127464
    # start_lon = 100.56234114
    start_latlon = (start_lat, start_lon)

    # destination_lat = 13.81305880286374
    # destination_lon = 100.55455060551576
    destination_latlon = (destination_lat, destination_lon)

    # Function หา distance

    def get_distance(point1, point2):
        return distance(point1, point2).meters

    # create a sample dataframe
    df = pd.DataFrame()
    df['lat'] = route_station_145['lat']
    df['lon'] = route_station_145['lon']
    df['name'] = route_station_145['sname']
    df['name_e'] = route_station_145['name_e']
    df['sqs'] = route_station_145['sqs']

    # define a function to compute the geodesic distance between two points

    def start_distance_to_xy(row):
        point = (row['lat'], row['lon'])
        return geodesic((start_lat, start_lon), point).meters

    def desination_distance_to_xy(row):
        point = (row['lat'], row['lon'])
        return geodesic((destination_lat, destination_lon), point).meters

    # compute the geodesic distance between (x,y) and each point in the dataframe
    df['distance_to_start'] = df.apply(start_distance_to_xy, axis=1)
    df['distance_to_destination'] = df.apply(desination_distance_to_xy, axis=1)

    # print the closest point to (x,y)
    closest_startpoint = df.loc[df['distance_to_start'].idxmin()]
    closest_destinationpoint = df.loc[df['distance_to_destination'].idxmin()]
    # Define the main polyline as a list of coordinates
    main_polyline = rpath

    # Define the two points between which you want to create a new polyline
    point1 = (closest_startpoint['lat'], closest_startpoint['lon'])
    point2 = (closest_destinationpoint['lat'], closest_destinationpoint['lon'])

    # Find the closest points on the main polyline to point1 and point2
    closest_point_to_point1 = min(
        main_polyline, key=lambda x: get_distance(x, point1))
    closest_point_to_point2 = min(
        main_polyline, key=lambda x: get_distance(x, point2))

    # Get the indices of the closest points in the main polyline
    index1 = main_polyline.index(closest_point_to_point1)
    index2 = main_polyline.index(closest_point_to_point2)

    # Create a new list of coordinates containing only the portion of the main polyline between the closest points
    if index1 < index2:
        new_polyline = main_polyline[index1:index2+1]
    else:
        new_polyline = main_polyline[index2:index1+1]

    # Define a function to calculate the distance between two points using the haversine formula

    def get_distance(latlon1, latlon2):
        # approximate radius of earth in km
        R = 6373.0

        lat1, lon1 = radians(latlon1[0]), radians(latlon1[1])
        lat2, lon2 = radians(latlon2[0]), radians(latlon2[1])

        dlon = lon2 - lon1
        dlat = lat2 - lat1

        a = sin(dlat / 2)**2 + cos(lat1) * cos(lat2) * sin(dlon / 2)**2
        c = 2 * atan2(sqrt(a), sqrt(1 - a))

        distance = R * c * 1000  # convert to meters
        return distance

    tolerance = 0.0005  # define the tolerance
    startBusStop_data = []  # create an empty list to collect start bus stop data
    endBusStop_data = []  # create an empty list to collect end bus stop data

    for x, y in route_station_145.iterrows():
        setlatlon = ((round(y['lat'], 4)), (round(y['lon'], 4)))
        for z in new_polyline:
            if abs(setlatlon[0]-z[0]) < tolerance and abs(setlatlon[1]-z[1]) < tolerance:
                data = {"busstop_id": y['sid'], "busstop_name_th": y['sname'],
                        "busstop_name_en": y['name_e'], "busstop_lat": y['lat'], "busstop_lon": y['lon']}
                if len(endBusStop_data) == 0:
                    endBusStop_data.append(data)
                    startBusStop_data.append(data)
                    continue
                startBusStop_data[0] = data
                break

    fist_bus = route_station_145.iloc[0]
    last_bus = route_station_145.iloc[-1]
    route = {"route_id": rinfo['path_id'], "route_name": rinfo['route_id'], "start_busstop_id": fist_bus['sid'], "start_busstop_name_th": fist_bus['sname'],
             "start_busstop_name_en": fist_bus['name_e'], "end_busstop_id": last_bus['sid'], "end_busstop_name_th": last_bus['sname'], "end_busstop_name_en": last_bus['name_e']}

    main_polyline_list = []
    for lat, lon in main_polyline:
        main_polyline_list.append({"line_lat": lat, "line_lon": lon})

    # START
    from_place_data = {"place_id": None, "place_name_th": 'จุดเริ่มต้น', "place_name_en": 'Start_point',
                       'place_lat': round(start_lat, 4), 'place_lon': round(start_lon, 4)}
    from_place_1 = {"from_place": from_place_data}
    to_place_data = {"place_id": None, "place_name_th": closest_startpoint['name'], "place_name_en": closest_startpoint[
        'name_e'], "place_lat": closest_startpoint['lat'], "place_lon": closest_startpoint['lon']}
    to_place_1 = {"to_place": to_place_data}
    # desination
    from_place_data = {"place_id": None, "place_name_th": closest_destinationpoint['name'], "place_name_en": closest_destinationpoint[
        'name_e'], "place_lat": closest_destinationpoint['lat'], "place_lon": closest_destinationpoint['lon']}
    from_place_2 = {"from_place": from_place_data}
    to_place_data = {"place_id": None, "place_name_th": 'จุดหมาย', "place_name_en": 'endpoint',
                     "place_lat": round(destination_lat, 4), "place_lon": round(destination_lon, 4)}
    to_place_2 = {"to_place": to_place_data}
    # seq_1
    seq_1 = {"seq_id": 1, "travel_type": 2, "travel_name": "walk", "travel_distance_m": round(
        1, 4), "route": None, "take_at_busstop": None, "getoff_at_busstop": None, "from_place": from_place_1, "to_place": to_place_1, "polyline": None}
    seq_2 = {"seq_id": 2, "travel_type": 1, "travel_name": "bus", "travel_distance_m": distance, "route": route, "take_at_busstop": startBusStop_data,
             "getoff_at_busstop": endBusStop_data, "from_place": None, "to_place": None, "polyline": main_polyline_list}
    seq_3 = {"seq_id": 1, "travel_type": 2, "travel_name": "walk", "travel_distance_m": round(
        1, 4), "route": None, "take_at_busstop": None, "getoff_at_busstop": None, "from_place": from_place_2, "to_place": to_place_2, "polyline": None}
    plan = [seq_1, seq_2, seq_3]
    outputjson = {"code": 200, "message": "ok", "plan": plan}
    return str(outputjson)
