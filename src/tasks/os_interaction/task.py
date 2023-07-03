from src.task import Task, DataPiece, Dataset
from src.agent import Agent, Session
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
import importlib
from typing import Callable, List, Dict, Any, Tuple, Optional, Union
import docker.models.containers
import docker

class Container:
    def __init__(self, image):
        self.image = image
        self.client = docker.from_env()
        self.container: docker.models.containers.Container = self.client.containers.run(
            image, detach=True, tty=True, stdin_open=True, remove=True,
            labels={"created_by": "os-pipeline"}
        )
        self.exec_id = self.client.api.exec_create(self.container.id, "bash --login", stdin=True, tty=True)["Id"]
        self.sock = self.client.api.exec_start(self.exec_id, socket=True)._sock
        self.sock.settimeout(5)
        # clear buffer
        self.sock.recv(1000)

    def __del__(self):
        # print("Releasing", self.container.name, self.container.id)
        self.container.stop()
        # print("Release", self.container.name, self.container.id, "OK")

    def execute(self, command: str):
        class DummyOutput:
            output: bytes
            exit_code: int

            def __init__(self, code, o):
                self.output = o
                self.exit_code = code

        print("=== EXECUTING ===\n", command)
        if not isinstance(command, str):
            return DummyOutput(-1, b'')
        self.sock.send(command.encode("utf-8") + b'\n')
        # ignore input line
        data = self.sock.recv(8)
        _, n = struct.unpack('>BxxxL', data)
        _ = self.sock.recv(n)
        output = b''
        while True:
            try:
                data = self.sock.recv(8)
                # print(data)
                if not data:
                    break
                _, n = struct.unpack('>BxxxL', data)
                line = self.sock.recv(n)
                output += line
                if re.search(b"\x1b.+@.+[#|$] ", line):
                    break
            except TimeoutError:
                break
            except socket.timeout:
                break
        # replace the very end \x1b.+@.+[#|$] into nothing (required the suffix)
        # output = re.sub(b"\x1b.+@.+[#|$] $", b"", output)
        return DummyOutput(0, output)

    def execute_independent(self, command, *params):
        print("=== EXECUTING INDEPENDENT ===\n", command)
        language, command = command
        if params:
            print("== Parameters ==\n", params)
        if language == "bash":
            cmd = ["bash", "-c", command]
            if params:
                cmd.append("--")
                cmd.extend(params)
        elif language == "python":
            cmd = ["python3", "-c", command, *params]
        elif language == "c++":
            self.execute_independent(("bash", f"echo \"{json.dumps(command)}\" > /tmp/main.cpp && "
                                              f"g++ -o /tmp/a.out /tmp/main.cpp"), None)
            cmd = ["/tmp/a.out", *params]
        elif language == "c":
            self.execute_independent(("bash", f"echo \"{json.dumps(command)}\" > /tmp/main.cpp && "
                                              f"gcc -o /tmp/a.out /tmp/main.cpp"), None)
            cmd = ["/tmp/a.out", *params]
        else:
            raise ValueError("Unsupported language")
        return self.container.exec_run(cmd)

one_shot = [
    {
        "role": "user",
        "content": 'You are an assistant that will act like a person, I am a linux(ubuntu) operating system. Your goal is to implement the operations required by the user or answer to the question proposed by the user. For each of your turn, you should take exact one of the two actions: "bash" or "commit". You should print a json format: {"thought": "Your thoughts to the problem and current action.", "action": str(either "bash" or "commit"), "content": str(For bash, this is the bash script you want to execute. For commit, this is the final answer to the question of the user. If no need to commit an answer, just make "content": null)}\nIf the output is too long, I will truncate it. The truncated output is not complete. You have to deal with the truncating problem by yourself. You could write a script to accomplish what you want. Attention, your bash code should not contain any input operation. My first question is: tell me how many files are in the directory "/etc"?'
    },
    {
        "role": "agent", "content": json.dumps({
            "thought": "To count the files in /etc, I need to print all the files in it.",
            "action": "bash",
            "content": "ls /etc"
        })
    },
    {
        "role": "user",
        "content": 'cpi cron.hourly fuse.conf iproute2 lvm networkd-dispatcher protocols selinux tmpfiles.d [truncated because the output is too long]'
    },
    {
        "role": "agent",
        "content": json.dumps({
            "thought": "The output has been truncated because it is too long, so I need to count files by script directly.",
            "action": "bash",
            "content": "ls -1 /etc | wc -l"
        })
    },
    {
        "role": "user",
        "content": '220'
    },
    {
        "role": "agent",
        "content": json.dumps({
            "thought": "Now I get the answer, it is 220.",
            "action": "commit",
            "content": "220"
        })
    }
]

class OSInteraction(Task):
    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.container = Container("ubuntu:latest")
        self.agent = OpenAIChatCompletion(name="gpt3", workers=1)
        self.interaction = Interaction(self.container, self.agent, round_limit=5)

    def release(self):
        self.container.__del__()
        self.agent.release()

    def evaluate(self, agent: Agent) -> Dict[str, Any]:
        print(f"Evaluating OS Interaction Task '{self.name}' ...")
        results = {}
        for i in range(10):
            print(f"=== Round {i} ===")
            result = self.interaction.query(one_shot)
            print("=== Result ===")
            print(result)
        return results

class Interaction:
    def __init__(self, container: Container, agent: Agent, round_limit=5) -> None:
        self.container = container
        self.agent = agent
        self.round_limit = round_limit

    def query(self, query):
        self.agent.user_message(query)

        for round in range(self.round_limit):
            print("=== Agent ===")
            try:
                root = self.agent.action()
                print(root)
            except Exception as e:
                print("Error", str(e), traceback.format_exc(), sep=" | ")
                return
            if "action" not in root or root["action"] not in ["bash", "commit"]:
                print("Error", "Invalid Action Field", traceback.format_exc(), sep=" | ")
                return

            action = root["action"]
            content = root["content"]
            if action == "commit":
                return content
            elif action == "bash":
                result = self.container.execute(content).output.decode('utf-8')
                if len(result) > 800:
                    result = result[:780] + "\n[truncated because the output is too long]"
                print("=== System ===")
                print(result)
                content = self.agent.system_message(result)