from flask import Flask, request, json, Response

app = Flask(__name__)


@app.route("/getplanminhop", methods=['GET'])
def hello_world():
    try:
        json_data = request.get_json()
        if json_data['app_key'] != "1256953732aD24v":
            print(json_data['app_key'])
            return Response(json_data['app_key'] + "is not app key",
                            status=404)
        da = open('mockdata.json')
        data = json.load(da)
        return Response(data + "ok", status=200)
    except Exception as error:
        return Response("Data is not found", status=404)
