# -*- coding: utf-8 -*-

import pandas as pd
from math import sin, cos, sqrt, atan2, radians
from rdflib import URIRef, BNode, Literal
from rdflib import Namespace
from rdflib import Graph
from rdflib.namespace import CSVW, DC, DCAT, DCTERMS, DOAP, FOAF, ODRL2, ORG, OWL, PROF, PROV, RDF, RDFS, SDO, SH, SKOS, SOSA, SSN, TIME, VOID, XMLNS, XSD
from rdflib.plugins import sparql
from rdflib.plugins.sparql.processor import SPARQLResult
import re
from enum import Enum
from flask import json


class TravelType(Enum):
    Bus = 1
    Walk = 2


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
                mainGo = mainRoutes[(
                    mainRoutes['direction'] == 'go') & (mainRoutes['route_id'] == str(busNumber))]

                if firstTime:
                    busStop = re.search(r'\d+', minHops[i+1]).group()
                    nameEng = mainRoutes.loc[mainRoutes['sid'] == int(
                        busStop), 'name_e'].values[0]
                    seqEnd = mainGo.loc[(mainGo['name_e']
                                         == nameEng), 'seq'].values[0]
                    path = mainGo[(mainGo['seq']
                                   >= closest_startpoint['seq']) & (mainRoutes['seq'] <= seqEnd)]
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
    for index in range(len(seqPath)):
        for key in seqPath[index]:
            if index == 0 and key != TravelType.Walk.value:
                if index == 0:
                    plan = {
                        "seq": seq,
                        "travel_type": 1,
                        "travel_time_name": "walk",
                        "travel_time_sec": 1000,
                        "travel_distance_m": 100,
                        "route": None,
                        "take_at_busstop": None,
                        "getoff_at_busstop": None,
                        "from_place": {
                            "place_id": None,
                            "place_name_th": "จุดเริ่มต้น",
                            "place_name_en": "Start Point",
                            "place_lat": start_lat,
                            "place_lon": start_lon
                        },
                        "to_place": {
                            "place_id": closest_startpoint['sid'],
                            "place_name_th": closest_startpoint['sname'],
                            "place_name_en": closest_startpoint['name_e'],
                            "place_lat": int(closest_startpoint['lat']),
                            "place_lon": int(closest_startpoint['lon'])
                        },
                        "polyline": None
                    }
                    planPath.append(plan)
                    seq += 1

            elif key == TravelType.Walk.value and index > 1:
                from_place = seqPath[index+1][TravelType.Bus.value].iloc[-1]
                to_place = seqPath[index-1][TravelType.Bus.value].iloc[0]
                plan = {
                    "seq": seq,
                    "travel_type": 1,
                    "travel_time_name": "walk",
                    "travel_time_sec": 1000,
                    "travel_distance_m": 100,
                    "route": None,
                    "take_at_busstop": None,
                    "getoff_at_busstop": None,
                    "from_place": {
                        "place_id": from_place['sid'],
                        "place_name_th": from_place['sname'],
                        "place_name_en": from_place['name_e'],
                        "place_lat": int(from_place['lat']),
                        "place_lon": int(from_place['lon'])
                    },
                    "to_place": {
                        "place_id": to_place['sid'],
                        "place_name_th": to_place['sname'],
                        "place_name_en": to_place['name_e'],
                        "place_lat": int(to_place['lat']),
                        "place_lon": int(to_place['lon']),
                    },
                    "polyline": None

                }
                planPath.append(plan)
                seq += 1

            elif key == TravelType.Walk.value:
                to_place = seqPath[index+1][TravelType.Bus.value].iloc[0]
                plan = {
                    "seq": seq,
                    "travel_type": 1,
                    "travel_time_name": "walk",
                    "travel_time_sec": 1000,
                    "travel_distance_m": 100,
                    "route": None,
                    "take_at_busstop": None,
                    "getoff_at_busstop": None,
                    "from_place": {
                        "place_id": None,
                        "place_name_th": "จุดเริ่มต้น",
                        "place_name_en": "Start Point",
                        "place_lat": start_lat,
                        "place_lon": start_lon
                    },
                    "to_place": {
                        "place_id": to_place['sid'],
                        "place_name_th": to_place['sname'],
                        "place_name_en": to_place['name_e'],
                        "place_lat": int(to_place['lat']),
                        "place_lon": int(to_place['lon']),
                    },
                    "polyline": None
                }
                planPath.append(plan)
                seq += 1

            elif key == TravelType.Bus.value:
                busPlan = seqPath[index][key]
                takeAt = busPlan.iloc[0]
                getOffAt = busPlan.iloc[-1]
                _polyLine = busPlan[['lat', 'lon']].astype(int).values.tolist()
                polyLine = [{"line_lat": lat, "line_lon": lon}
                            for lat, lon in _polyLine]
                plan = {
                    "seq": seq,
                    "travel_type": 2,
                    "travel_time_name": "bus",
                    "travel_time_sec": 1000,
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
                        "busstop_lat": int(takeAt['lat']),
                        "busstop_lon": int(takeAt['lon']),
                    },
                    "getoff_at_busstop": {
                        "busstop_id": getOffAt['sid'],
                        "busstop_name_th": getOffAt['sname'],
                        "busstop_name_en": getOffAt['name_e'],
                        "busstop_lat": int(getOffAt['lat']),
                        "busstop_lon": int(getOffAt['lon']),
                    },
                    "from_place": None,
                    "to_place": None,
                    "polyline": polyLine
                }
                planPath.append(plan)
                seq += 1
    response = {"code": 200, "message": "ok", "plan": planPath}
    parsed_data = json.dumps(response, default=int)

    return parsed_data


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
