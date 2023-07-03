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


def compose_tool_usage(name: str, parameters: dict):
    js = {
        'tool': name,
        'input': parameters
    }
    return "Call Tool: %s" % (json.dumps(js, ensure_ascii=False))


class Tool:
    # TODO: adapt to more APIs in the Internet, now is used for local toy APIs
    def __init__(self, call_url, meta_url) -> None:
        res = requests.get(meta_url)
        if res.status_code != 200:
            raise Exception("Invalid tool server")
        self.config = res.json()
        self.url = call_url

        self.name = self.config["name"]
        self.description = self.config["description"]
        self.return_description = self.config["return"]
        self.parameters = self.config["parameters"]
        self.examples = self.config["examples"] if "examples" in self.config else (self.config["example"] if isinstance(self.config["example"], list) else [self.config["example"]])
        self.full_example = self.config["one_shot_example"] if (
            "one_shot_example" in self.config) else None

    def __call__(self, parameters) -> str:
        # with open("tmp2", "w", encoding="utf-8") as f:
        #     print(parameters, file=f)
        res = requests.post(self.url, json=parameters)
        if res.status_code != 200:
            try:
                return "Error Occurs when calling the tool:\n" + res.json()
            except:
                return "Error Occurs when calling the tool:\n" + res.text
        return res.json()

    @property
    def full_documentation(self):
        parameter_str = "\n".join(["%s%s: %s" % (item["name"], " (Optional)" if (
            "optional" in item and item["optional"]) else "", item["description"]) for item in self.parameters])
        item = random.choice(self.examples)
        example_str = "[Example Input]\n%s\n[Example Output]\n%s" % (
            compose_tool_usage(self.name, item["input"]),
            item["output"],
        )
        return "Tool: %s\nDescription: %s\nReturn: %s\n[Parameters]\n%s\n%s" % (self.name, self.description, self.return_description, parameter_str, example_str)


class ToolClient(dict):
    def __init__(self, server_url) -> None:
        # a dict of tool name -> tool
        self.server_url = server_url
        resp = requests.get(server_url).json()
        # for tool in resp:
        #     print(tool["name"])
        # print(tool_server_url)
        available_tools = [{
            "call_url": server_url.removesuffix("/") + tool["call_url"],
            "meta_url": server_url.removesuffix("/") + tool["meta_url"],
        } for tool in resp]
        tools = {}
        for tool_dict in available_tools:
            tool = Tool(tool_dict["call_url"], tool_dict["meta_url"])
            tools[tool.name] = tool
        super().__init__(tools)

    def __call__(self, name, parameters):
        return self[name](parameters)
