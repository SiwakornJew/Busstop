
import pandas as pd
from rdflib import Graph
from rdflib.namespace import CSVW, DC, DCAT, DCTERMS, DOAP, FOAF, ODRL2, ORG, OWL, PROF, PROV, RDF, RDFS, SDO, SH, SKOS, SOSA, SSN, TIME, VOID, XMLNS, XSD
import re
from enum import Enum
from flask import json
import random

import pandas as pd
import numpy as np


class TravelType(Enum):
    Bus = 1
    Walk = 2


bus_path = 'data/csv/bus_routes.csv'
bus_route = pd.read_csv(bus_path)


def _genSparql(src="", des="", num_lines=1, show_stations=False):
    con1 = f" {src} "
    con2 = ""
    select = ""
    con3 = ""
    con3_list = []

    i = 1
    for i in range(1, num_lines+1):
        pi = f"?p{i}"
        xi = f"?x{i}"

        # select statement
        select += f" {pi} "
        if i < num_lines:
            select += f" {xi} " if show_stations else ""

        # chain of p
        if i < num_lines:
            con1 += f" {pi} {xi} . {xi} "

            # pi != pi+1
            pj = f"?p{i+1}"
            con3_list.append(f" ({pi} != {pj}) ")

        # p in plan item
        con2 += f" {pi} rdf:type tc:PlanItem . "

    # final hop
    con1 += f" {pi} {des} . "

    # filter condition
    if len(con3_list) > 0:
        con3 = " FILTER (" + " && ".join(con3_list) + " ) "

    return "SELECT DISTINCT " + select + " WHERE { " + con1 + con2 + con3 + " } " + "LIMIT 1"


def _formatBusResponse(seq, timeTravel, takeAt, getOffAt, reshaped_ansline):
    return {
        "seq": seq,
        "travel_type": 2,
        "travel_time_name": "bus",
        "travel_time_sec": timeTravel,
        "travel_distance_m": 100,
        "route": {
            "route_id": takeAt['path_id'],
            "route_name": takeAt['route_id'],
            "start_busstop_name_th": takeAt['sname'],
            "start_busstop_name_en": takeAt['name_e'],
            "end_busstop_id": getOffAt['sid'],
            "end_busstop_name_th": getOffAt['sname'],
            "end_busstop_name_en": getOffAt['name_e'],
        },
        "take_at_busstop": {
            "busstop_id": takeAt['sid'],
            "busstop_name_th": takeAt['sname'],
            "busstop_name_en": takeAt['name_e'],
            "busstop_lat": takeAt['lat'],
            "busstop_lon": takeAt['lon'],
        },
        "getoff_at_busstop": {
            "busstop_id": getOffAt['sid'],
            "busstop_name_th": getOffAt['sname'],
            "busstop_name_en": getOffAt['name_e'],
            "busstop_lat": getOffAt['lat'],
            "busstop_lon": getOffAt['lon'],
        },
        "from_place": None,
        "to_place": None,
        "polyline": reshaped_ansline
    }


def _formatWalkResponse(seq, timeTravel, from_place=None, to_place=None, start_lat=None, start_lon=None):
    if from_place is not None:
        return {
            "seq": seq,
            "travel_type": 1,
            "travel_time_name": "walk",
            "travel_time_sec": timeTravel,
            "travel_distance_m": 100,
            "route": None,
            "take_at_busstop": None,
            "getoff_at_busstop": None,
            "from_place": {
                "place_id": from_place['sid'],
                "place_name_th": from_place['sname'],
                "place_name_en": from_place['name_e'],
                "place_lat": from_place['lat'],
                "place_lon": from_place['lon'],
            },
            "to_place": {
                "place_id": to_place['sid'],
                "place_name_th": to_place['sname'],
                "place_name_en": to_place['name_e'],
                "place_lat": to_place['lat'],
                "place_lon": to_place['lon'],
            },
            "polyline": None

        }
    elif start_lat and start_lon is not None:
        return {
            "seq": seq,
            "travel_type": 1,
            "travel_time_name": "walk",
            "travel_time_sec": timeTravel,
            "travel_distance_m": 100,
            "route": None,
            "take_at_busstop": None,
            "getoff_at_busstop": None,
            "from_place": {
                "place_id": None,
                "place_name_th": "จุดเริ่มต้น",
                "place_name_en":  "Start Point",
                "place_lat": start_lat,
                "place_lon":  start_lon,
            },
            "to_place": {
                "place_id": to_place['sid'],
                "place_name_th": to_place['sname'],
                "place_name_en": to_place['name_e'],
                "place_lat": to_place['lat'],
                "place_lon": to_place['lon'],
            },
            "polyline": None

        }


def findMinHop(start, des, loaded_graph_rdf):
    hop = 3
    max_hops = 4
    source_node = f"sta:busnode_{start}"
    target_node = f"sta:busnode_{des}"
    found_result = False
    initNs = {
        "rdf": RDF,
        "rdfs": RDFS,
        "tc": "http://transline.org/terms/",
        "sta": "http://transline.org/stations/",
        "line": "http://transline.org/lines/"
    }
    linePath = []
    while hop <= max_hops and not found_result:
        spql = _genSparql(source_node, target_node, hop, True)
        res = loaded_graph_rdf.query(spql, initNs=initNs)

        if res:
            variables = res.vars
            linePath = []
            for binding in res.bindings:
                for var in variables:
                    linePath.append(binding[var].rsplit('/', 1)[-1])

            found_result = True

        else:
            hop += 1
    return linePath


def _findDistanceTH(lat1, lon1, lat2, lon2):
    return (110*((lat1-lat2)**2+(lon1-lon2)**2)**0.5)*1000


def find_closest_point(target, points):
    closest_point = min(points, key=lambda point: abs(
        target[0] - point[0]) + abs(target[1] - point[1]))
    return closest_point


def reshape_ansline_to_rpath(routeId, lines):
    rpath = bus_route[bus_route["route_id"] == routeId]["polyline"].iloc[0]
    rpath = eval(rpath)

    if len(lines) < 2:
        return None

    line_start = lines[0]
    line_end = lines[-1]

    closest_start = find_closest_point(line_start, rpath)
    closest_end = find_closest_point(line_end, rpath)

    start_index = rpath.index(closest_start)
    end_index = rpath.index(closest_end)

    if start_index < end_index + 1:
        reshaped_ansline = rpath[start_index: end_index + 1]
    else:
        reshaped_ansline = rpath[end_index: start_index + 1]

    return reshaped_ansline


def getRoute(start_lat, start_lon, destination_lat, destination_lon):
    seq = 1
    firstTime = True
    seqPath = []
    planPath = []

    _mainRoutes = "data/csv/mainRoutes.csv"
    mainRoutes = pd.read_csv(_mainRoutes)

    mainRoutes['distance_to_start'] = _findDistanceTH(
        start_lat, start_lon, mainRoutes['lat'], mainRoutes['lon'])
    mainRoutes['distance_to_destination'] = _findDistanceTH(
        destination_lat, destination_lon, mainRoutes['lat'], mainRoutes['lon'])

    loaded_graph_rdf = Graph()
    loaded_graph_rdf.parse(
        "data/graph/Inferred_knowledge_graph.rdf", format="xml")

    closest_startpoint = mainRoutes.loc[mainRoutes['distance_to_start'].idxmin(
    )]
    closest_destinationpoint = mainRoutes.loc[mainRoutes['distance_to_destination'].idxmin(
    )]
    minHops = findMinHop(closest_startpoint["sid"],
                         closest_destinationpoint["sid"], loaded_graph_rdf)

    for i in range(len(minHops)):
        if minHops[i].startswith("bus_"):
            busNumber = re.search(r'\d+', minHops[i]).group()
            if minHops[i].endswith("_gt"):
                mainGo = mainRoutes[(mainRoutes['direction'] == 'go') & (
                    mainRoutes['route_id'] == str(busNumber))]

                if firstTime:
                    busStop = re.search(r'\d+', minHops[i+1]).group()

                    nameEng = mainRoutes.loc[mainRoutes['sid'] == int(
                        busStop), 'name_e'].values[0]
                    seqEnd = mainGo.loc[(
                        mainGo['name_e'] == nameEng), 'seq'].values[0]
                    path = mainGo[(mainGo['seq'] >= closest_startpoint['seq']) & (
                        mainRoutes['seq'] <= seqEnd)]
                    firstTime = False
                    seqPath.append({1: path})

                elif i == len(minHops)-1:
                    busStop = re.search(r'\d+', minHops[i-1]).group()

                    nameEng = mainRoutes.loc[mainRoutes['sid'] == int(
                        busStop), 'name_e'].values[0]
                    seqStart = mainGo.loc[(mainGo['name_e']
                                           == nameEng), 'seq'].values[0]
                    seqEnd = mainGo.loc[(mainGo['name_e']
                                         == closest_destinationpoint['name_e']), 'seq'].values[0]

                    path = mainGo[(mainRoutes['seq'] <= seqEnd) & (
                        mainGo['seq'] >= seqStart)]
                    seqPath.append({1: path})

                else:
                    busStopHead = re.search(r'\d+', minHops[i+1]).group()
                    busStopTail = re.search(r'\d+', minHops[i-1]).group()

                    nameEngHead = mainRoutes.loc[mainRoutes['sid'] == int(
                        busStopHead), 'name_e'].values[0]
                    nameEngTail = mainRoutes.loc[mainRoutes['sid'] == int(
                        busStopTail), 'name_e'].values[0]
                    seqStart = mainBack.loc[(mainBack['name_e']
                                             == nameEngHead), 'seq'].values[0]
                    seqEnd = mainBack.loc[(mainBack['name_e']
                                           == nameEngTail), 'seq'].values[0]
                    path = mainBack[(mainBack['seq']
                                     >= seqStart) & (mainRoutes['seq'] <= seqEnd)]
                    seqPath.append({1: path})

            elif minHops[i].endswith("_bt"):
                mainBack = mainRoutes[(
                    mainRoutes['direction'] == 'back') & (mainRoutes['route_id'] == str(busNumber))]
                if firstTime:
                    busStop = re.search(r'\d+', minHops[i+1]).group()
                    nameEng = mainRoutes.loc[mainRoutes['sid'] == int(
                        busStop), 'name_e'].values[0]
                    seqStart = mainBack.loc[(mainBack['name_e']
                                             == closest_startpoint['name_e']), 'seq'].values[0]
                    seqEnd = mainBack.loc[(mainBack['name_e']
                                           == nameEng), 'seq'].values[0]
                    path = mainBack[(mainBack['seq']
                                     >= seqStart) & (mainRoutes['seq'] <= seqEnd)]
                    firstTime = False
                    seqPath.append({1: path})

                elif i == len(minHops)-1:
                    busStop = re.search(r'\d+', minHops[i-1]).group()
                    nameEng = mainRoutes.loc[mainRoutes['sid'] == int(
                        busStop), 'name_e'].values[0]
                    seqStart = mainGo.loc[(mainGo['name_e']
                                           == nameEng), 'seq'].values[0]
                    seqEnd = mainGo.loc[(mainGo['name_e']
                                         == closest_destinationpoint['name_e']), 'seq'].values[0]
                    path = mainGo[(mainRoutes['seq'] <= seqEnd) & (
                        mainGo['seq'] >= seqStart)]
                    seqPath.append({1: path})

                else:
                    busStopHead = re.search(r'\d+', minHops[i+1]).group()
                    busStopTail = re.search(r'\d+', minHops[i-1]).group()

                    timeTravel.findTravelTime(busStopHead, busStopTail)

                    nameEngHead = mainRoutes.loc[mainRoutes['sid'] == int(
                        busStopHead), 'name_e'].values[0]
                    nameEngTail = mainRoutes.loc[mainRoutes['sid'] == int(
                        busStopTail), 'name_e'].values[0]
                    seqStart = mainBack.loc[(mainBack['name_e']
                                             == nameEngHead), 'seq'].values[0]
                    seqEnd = mainBack.loc[(mainBack['name_e']
                                           == nameEngTail), 'seq'].values[0]
                    path = mainBack[(mainBack['seq']
                                     >= seqStart) & (mainRoutes['seq'] <= seqEnd)]

                    seqPath.append({1: path})

        elif minHops[i].startswith("walk"):

            seqPath.append({2: "walk"})
    ansline = []
    route_ansLines = {}
    for index in range(len(seqPath)):
        for key in seqPath[index]:
            timeTravel = random.randint(5, 10)*60
            if index == 0 and key != TravelType.Walk.value:
                if index == 0:
                    plan = _formatWalkResponse(
                        seq, timeTravel, start_lat=start_lat, start_lon=start_lon, to_place=closest_startpoint)
                    planPath.append(plan)
                    print(plan)
                    seq += 1

            elif key == TravelType.Walk.value and index > 1:
                from_place = seqPath[index+1][TravelType.Bus.value].iloc[-1]
                to_place = seqPath[index-1][TravelType.Bus.value].iloc[0]
                plan = _formatWalkResponse(
                    seq, timeTravel, from_place=from_place, to_place=to_place)
                planPath.append(plan)
                seq += 1

            elif key == TravelType.Walk.value:
                to_place = seqPath[index+1][TravelType.Bus.value].iloc[0]
                plan = _formatWalkResponse(
                    seq, timeTravel, to_place=to_place, start_lat=start_lat, start_lon=start_lon)
                planPath.append(plan)
                seq += 1

            elif key == TravelType.Bus.value:
                busPlan = seqPath[index][key]
                takeAt = busPlan.iloc[0]
                getOffAt = busPlan.iloc[-1]
                _polyLine = busPlan[['lat', 'lon']].astype(
                    float).values.tolist()
                for i in _polyLine:
                    ansline.append(i)

                reshaped_ansline = reshape_ansline_to_rpath(
                    takeAt['route_id'], ansline)
                route_ansLines[takeAt['route_id']] = reshaped_ansline
                plan = _formatBusResponse(seq, timeTravel,
                                          takeAt, getOffAt, reshaped_ansline)
                planPath.append(plan)
                seq += 1
                ansline = []
    response = {"code": 200, "message": "ok", "plan": planPath}
    parsed_data = json.dumps(response, default=int)

    return parsed_data, route_ansLines
