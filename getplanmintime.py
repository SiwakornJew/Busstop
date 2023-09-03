from flask import Flask, jsonify, request
from semantic_Lines_Route import getRoute
from rdflib import Graph
app = Flask(__name__)

loaded_graph_rdf = Graph()
app.cache = loaded_graph_rdf.parse(
    "data/graph/Inferred_knowledge_graph(full).rdf", format="xml")


@app.route("/getplanmintime", methods=['GET'])
def getplanminhop():
    try:
        json_data = request.get_json()
        output = getRoute(json_data["start_lat"], json_data["start_lon"],
                          json_data["destination_lat"], json_data["destination_lon"], app.cache)
        return output
    except Exception as e:
        return jsonify({"error": str(e)}), 500
