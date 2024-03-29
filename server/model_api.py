import argparse
import datetime
import json
import multiprocessing as mp

import flask
import torch.cuda
from flask import request, jsonify, abort

from server.model_server import ModelServer, ModelServerError
from utils import log as _log


def log(action: str, **kwargs):
    _log({
        "action": action,
        "request": request.get_json(),
        "ip": request.remote_addr,
        # format 
        "time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "additional": kwargs
    })


app = flask.Flask(__name__)


@app.before_request
def before_request():
    if request.method != "POST":
        return abort(405, "Method Not Allowed")

    # check data structure
    data = dict(request.get_json())
    msg = data.pop("messages", None)
    if msg:
        for item in msg:
            if "content" not in item or "role" not in item:
                return abort(400, "No Content or Role")
            if item["role"] not in ["user", "assistant"]:
                return abort(400, "Role must be user or assistant")
            if not isinstance(item["content"], str):
                return abort(400, "Content must be string")
    tmp = data.pop("temperature", None)
    if tmp:
        if not isinstance(tmp, float):
            return abort(400, "Temperature must be float")


@app.route('/api/v1/<model_server_name>/activate', methods=['POST'])
def activate(model_server_name):
    log("activate", model_server_name=model_server_name)
    try:
        if model_server_name not in server.models:
            return abort(403, "Invalid Model Name")
        if model_server_name not in server.model_devices:
            server.add(model_server_name)
        return jsonify({"status": 0})
    except ModelServerError as e:
        return jsonify({"status": -1, "message": str(e)})


@app.route('/api/v1/<model_server_name>/add', methods=['POST'])
def add(model_server_name):
    log("add", model_server_name=model_server_name)
    try:
        if model_server_name not in server.models:
            return abort(403, "Invalid Model Name")
        data = request.get_json()
        server.add(model_server_name, data.get("device", None))
        return jsonify({"status": 0})
    except ModelServerError as e:
        return jsonify({"status": -1, "message": str(e)})


@app.route('/api/v1/<model_server_name>/deactivate', methods=['POST'])
def deactivate(model_server_name):
    log("deactivate", model_server_name=model_server_name)
    try:
        if model_server_name not in server.models:
            return abort(403, "Invalid Model Name")
        server.remove(model_server_name)
        return jsonify({"status": 0})
    except ModelServerError as e:
        return jsonify({"status": -1, "message": str(e)})


@app.route('/api/v1/<model_server_name>/remove', methods=['POST'])
def remove(model_server_name):
    log("remove", model_server_name=model_server_name)
    try:
        if model_server_name not in server.models:
            return abort(403, "Invalid Model Name")
        server.remove(model_server_name)
        return jsonify({"status": 0})
    except ModelServerError as e:
        return jsonify({"status": -1, "message": str(e)})


@app.route('/api/v1/<model_server_name>/status', methods=['POST'])
def status(model_server_name):
    log("status", model_server_name=model_server_name)
    try:
        if model_server_name not in server.models:
            return abort(403, "Invalid Model Name")
        return jsonify({"status": 0, "model_server_status": server.status(model_server_name)})
    except ModelServerError as e:
        return jsonify({"status": -1, "message": str(e)})


@app.route('/api/v1/<model_server_name>/call', methods=['POST'])
def call(model_server_name):
    """
    This function is a little bit complicated
    
    1. Check if the model server is active and the model is deployed, if not, return error.
    2. Check if the key is valid, if not, return error.
    3. Register the message, temperature and callback into the model server. And wait for the callback to be called.
    4. when callback is called, return the result.
    """

    # record key, request, ip, time, model_server_name
    log("call", model_server_name=model_server_name)
    try:
        if model_server_name not in server.models:
            return abort(403, "Invalid Model Name")
        if not server.model_devices[model_server_name]:
            return jsonify({"status": -1, "message": "model server %s is not active" % model_server_name})
        data = request.get_json()
        if "messages" not in data:
            return abort(403, "Not Messages")
        messages = data["messages"]
        temperature = data.get("temperature", None)

        main_conn, sub_conn = mp.Pipe()
        server.register(model_server_name, messages, temperature, sub_conn)

        ret = main_conn.recv()
        log("call-result", result=ret)
        return jsonify({"status": 0, "result": ret})
    except ModelServerError as e:
        return jsonify({"status": -1, "message": str(e)})


@app.route('/api/v1/', methods=['POST'])
def global_status():
    log("global-status")
    return jsonify({"status": 0, "info": server.status()})


@app.route('/admin/ipython', methods=['POST'])
def start_ipython():
    import IPython
    IPython.embed()
    return jsonify({"status": 0})


if __name__ == '__main__':
    mp.set_start_method("spawn")
    entries = {}
    with open("config.json") as f:
        models = json.load(f)
    server = ModelServer(models, ["cuda:%d" % i for i in range(torch.cuda.device_count())])
    parse = argparse.ArgumentParser()
    parse.add_argument("--port", type=int, default=9999)
    parse.add_argument("--model", type=str, default="")
    parse.add_argument("--device", action="extend", nargs="+", type=str, default=[])
    args = parse.parse_args()
    if args.model:
        for d in args.device:  # could be further optimized with mp
            server.add(args.model, d)
    app.run(host="0.0.0.0", port=args.port, debug=False, threaded=True)
