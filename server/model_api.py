import datetime
import json
import os
import multiprocessing as mp

import flask
from flask import request, jsonify, abort

from models import *
from server.model_server import ModelServer, ModelServerError

""" 

POST: /{model-server-name}/{action}
model-server-name：模型服务的名称，例如：openai，claude
action：
    activate：激活模型（部署）
    call：调用模型（需要模型是已激活状态）
    deactivate：撤下模型
    status：查看是否已部署
Header:
JSON for "call"
{
    "messages": [
        {"role": "user" or "assistant", "content": string},
    ],
    "model": str, // optional
    "temperature": float, // optional
}

parameters 可能包括：
model: 例如 openai 包括 text-davinci-003，chat-turbo-3.5
temperature

"""

from utils import log as _log


def log(action: str, **kwargs):
    _log({
        "action": action,
        "request": request.get_json(),
        "ip": request.remote_addr,
        # format 
        "time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "addtional": kwargs
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
        # if tmp < 0 or tmp > 1:
        #     return abort(400, "Bad Request")
    if data:
        return abort(400, "Unknown Fields in Request Body.")


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
        server.add(model_server_name)
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

        queue = mp.Queue()

        def callback(result_):
            nonlocal queue
            queue.put(result_)

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


def load_config_entries(root_dir):
    entries = {}
    for file_name in os.listdir(root_dir):
        if not file_name.endswith(".json"):
            continue
        config_path = os.path.join(root_dir, file_name)
        with open(config_path, "r") as f:
            config = json.load(f)
            f.close()
        entries[config["model_name"]] = ConfigEntry(config_path)
    return entries


if __name__ == '__main__':
    mp.set_start_method("spawn")
    entries = {}
    entries.update(load_config_entries("./configs"))
    with open("config.json") as f:
        models = json.load(f)
    server = ModelServer(models, ["cuda:%d" % i for i in range(8)])
    app.run(host="0.0.0.0", port=9998, debug=False, threaded=True)

""" 

TODO

- decode for each request: if input is too long, return error.

"""