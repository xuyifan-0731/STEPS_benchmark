# coding=utf8
import threading
import multiprocessing
from flask import Flask, jsonify, request, abort
from flask_cors import *
import os
import json
import sys
import time
import re
import math
import random
import datetime
import argparse
import requests
import glob
from typing import Callable, List, Dict, Any, Tuple, Optional, Union

import importlib.util


class ToolServerEntry:

    def __init__(self, folder_path) -> None:
        with open(os.path.join(folder_path, 'meta.json'), 'r') as f:
            meta_info = json.load(f)

        self.config = meta_info
        self.name = self.config["name"]
        self.description = self.config["description"]
        self.return_description = self.config["return"]
        self.parameters = self.config["parameters"]
        self.examples = self.config["examples"] if "examples" in self.config else (self.config["example"] if isinstance(self.config["example"], list) else [self.config["example"]])
        self.full_example = self.config["one_shot_example"] if ("one_shot_example" in self.config) else None

        # if __init__.py exists, import calling from it as self.__call__
        tool_path = os.path.join(folder_path, '__init__.py')
        if os.path.exists(tool_path):
            spec = importlib.util.spec_from_file_location("tool_server_entry", tool_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            self.__call__ = getattr(module, 'calling')

    # def __call__(self, parameters) -> str:
    #     raise NotImplementedError()

    def get_config_json(self) -> str:
        return self.config

    def get_request_handler(self, handler: Callable[[dict], str] = None) -> Callable[[], str]:
        def wrapper():
            nonlocal handler
            data = request.get_json()

            if data is None:
                return jsonify({"error": "Invalid Parameters."}), 400
            if not handler:
                handler = self.__call__
            response_data = handler(data)
            return jsonify(response_data)

        return wrapper

    def get_entrypoints(self, route_name, handler: Callable[[dict], str] = None) -> List[Dict[str, Any]]:
        return [
            {
                'route_name': route_name,
                'handler': self.get_request_handler(handler),
                'methods': ['POST']
            },
            {
                'route_name': route_name + '/.well-known/ai-plugin.json',
                'handler': self.get_config_json,
                'methods': ['GET', 'POST']
            },
        ]


class ToolServer:
    def __init__(self, tools: List[ToolServerEntry]):
        self.app = Flask(__name__)
        CORS(self.app, supports_credentials=True)

        self.tools = tools
        self.endpoints = []

        for tool in tools:
            self.endpoints.extend(tool.get_entrypoints('/tool/%s' % tool.name))

        self.register_endpoints(self.endpoints)
        self.app.add_url_rule('/', '/', self.index)

    def index(self):
        ret = []  # {name: str, meta_url: str, call_url: str}
        for tool in self.tools:
            ret.append({
                "name": tool.name,
                "meta_url": "/tool/%s/.well-known/ai-plugin.json" % tool.name,
                "call_url": "/tool/%s" % tool.name,
            })
        return jsonify(ret)

    def register_endpoints(self, endpoints):
        for endpoint in endpoints:
            route_name = endpoint["route_name"]
            handler = endpoint["handler"]
            methods = endpoint.get("methods", ['GET'])

            self.app.add_url_rule(route_name, route_name, handler, methods=methods)

    def run(self, host, port, debug):
        self.app.run(host=host, port=port, debug=debug)


def create_server_process(tool_root_dir, host, port):
    # tool_root_dir = 'data/tool_execution/server'
    tools = []
    for tool_dir in glob.glob(os.path.join(tool_root_dir, '*')):
        tools.append(ToolServerEntry(tool_dir))

    tool_server = ToolServer(tools)

    p = multiprocessing.Process(target=tool_server.run, kwargs={"host": host, "port": port})
    p.start()
    return p
