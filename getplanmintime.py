from flask import Flask, jsonify, request, json, Response
from semantic_Lines_Route import getRoute
app = Flask(__name__)


@app.route("/getplanmintime", methods=['GET'])
def getplanminhop():
    try:
        json_data = request.get_json()
        output = getRoute(json_data["start_lat"], json_data["start_lon"],
                          json_data["destination_lat"], json_data["destination_lon"])
        return output
    except Exception as e:
        return jsonify({"error": str(e)}), 500
