from flask import Flask, request, json, Response

app = Flask(__name__)


@app.route("/getplanmintime", methods=['GET'])
def getplanminhop():
    try:
        json_data = request.get_json()
        output = getroute(json_data['start_lat'], json_data['start_lon'],
                          json_data['destination_lat'], json_data['destination_lon'])

        return json.loads(json.dumps(output))
    except Exception as error:
        return Response("Data is not found", status=404)
