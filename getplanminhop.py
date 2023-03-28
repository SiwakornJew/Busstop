from flask import Flask, request, json, Response
from testroute import getroute
app = Flask(__name__)


@app.route("/getplanminhop", methods=['GET'])
def getplanminhop():
    json_data = request.get_json()
    output = getroute(json_data['start_lat'], json_data['start_lon'],
                      json_data['destination_lat'], json_data['destination_lon'])

    return json.loads(json.dumps(output))
