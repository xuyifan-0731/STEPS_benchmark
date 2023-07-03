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
import traceback


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


class JudgeConfig:
    image: str = None
    init_script: List[Tuple[str, str]] = None
    start: Tuple[str, str] = None
    description: str
    check: list = None
    match: dict = None
    example_script: str = None

    def get_evaluation_type(self):
        if self.check:
            return "check"
        elif self.match:
            return "match"

    def get_evaluation_content(self):
        return self.check or self.match


class OSInteraction(Task):
    def _load_configs(self, config_path, script_root_dir=".") -> List[JudgeConfig]:
        def load_script(script_obj):
            if script_obj is None:
                return None
            if type(script_obj) is str:
                return "bash", script_obj
            if "language" not in script_obj:
                language = "bash"
            else:
                language = script_obj["language"]
            if "file" in script_obj:
                with open(os.path.join(script_root_dir, script_obj["file"]), encoding="utf-8") as f:
                    return language, f.read()
            elif "code" in script_obj:
                return language, script_obj["code"]
            else:
                raise ValueError("Invalid Script Object")

        # 1. handle input file:
        if config_path.endswith(".json"):
            with open(config_path, encoding="utf-8") as f:
                config_raw = json.load(f)
            if isinstance(config_raw, list):
                pass
            elif isinstance(config_raw, dict):
                config_raw = [config_raw]
            else:
                raise ValueError("Invalid Config File")
        elif config_path.endswith(".jsonl"):
            with open(config_path, encoding="utf-8") as f:
                config_raw = [json.loads(line) for line in f.readlines()]
        else:
            raise ValueError("Invalid Config File")

        # 2. handle configs
        configs: list[JudgeConfig] = []
        for item in config_raw:
            config = JudgeConfig()
            config.description = item["description"]
            if "create" in item:
                config.image = item["create"]["image"] if ("image" in item["create"]) else (self.docker_config["localhost"] + "/default")
                if "init" in item["create"]:
                    if type(item["create"]["init"]) is not list:
                        config.init_script = [load_script(item["create"]["init"])]
                    else:
                        config.init_script = [load_script(script_obj) for script_obj in item["create"]["init"]]
                else:
                    config.init_script = []
            else:
                config.image = self.docker_config["localhost"] + "/default"
            if "start" in item:
                config.start = load_script(item["start"])
            evaluation = item["evaluation"]
            if "match" in evaluation:
                if type(evaluation["match"]) is str:
                    config.match = {
                        "answer": evaluation["match"],
                        "strip": True
                    }
                else:
                    config.match = evaluation["match"]
            elif "check" in evaluation:
                if type(evaluation["check"]) is not list:
                    config.check = [load_script(evaluation["check"])]
                else:
                    config.check = [load_script(script_obj) for script_obj in evaluation["check"]]
            else:
                raise ValueError("check or match must exist.")
            if "check" in evaluation and "example" in evaluation:
                config.example_script = load_script(evaluation["example"])
            configs.append(config)
        return configs

    def __init__(self, **kwargs):
        # TODO: load config here
        self.match_problem: bool = kwargs.pop("match_problem", True)
        self.check_problem: bool = kwargs.pop("check_problem", True)
        self.round_limit: int = kwargs.pop("round_limit", 3)
        self.data_config = kwargs.pop("data_config", None)
        if not self.data_config:
            raise ValueError("data_config must be set")
        self.docker_config = kwargs.pop("docker_config", None)
        if not self.docker_config:
            raise ValueError("docker_config must be set")
        configs: List[dict[str, Any]] = []
        matches = []
        for item in self.data_config["files"]:
            path = item["problem_file"]
            for file in glob.glob(path):
                if file.endswith(".json") or file.endswith(".jsonl"):
                    matches.append({
                        "problem_file": file,
                        "script_dir": item["script_dir"]
                    })
        self.data_config["files"] = matches
        for item in self.data_config["files"]:
            problem_file, problem_dir = item["problem_file"], item["script_dir"]
            single_file_configs = self._load_configs(problem_file, problem_dir)
            single_file_check_configs = []
            single_file_match_configs = []
            for idx, config in enumerate(single_file_configs):
                if config.check:
                    single_file_check_configs.append({"file": problem_file, "config": config, "index": idx})
                elif config.match:
                    single_file_match_configs.append({"file": problem_file, "config": config, "index": idx})
            print("Load %s, %d problems, %d check problems, %d match problems." % (problem_file, len(single_file_configs), len(single_file_check_configs), len(single_file_match_configs)))
            if self.match_problem:
                configs.extend(single_file_match_configs)
            if self.check_problem:
                configs.extend(single_file_check_configs)
        self.problem_configs = configs

        super().__init__(**kwargs)

    def metric(self, prediction: List[Dict], target: List[None]):
        files = []
        for item in self.data_config["files"]:
            file = item["problem_file"]
            if file.endswith(".json") or file.endswith(".jsonl"):
                if file in self.data_config["ignore"]:
                    continue
                file_configs = [config for config in prediction if config["file"] == file]
                print("File:", file, "Total:", len(file_configs), "Pass:", len([config for config in file_configs if "result" in config and config["result"]]))
                files.append({
                    "file": file,
                    "total": len(file_configs),
                    "pass": len([config for config in file_configs if "result" in config and config["result"]]),
                    "wrong": len([config for config in file_configs if "result" not in config or not config["result"]]),
                })
        overall = {
            "total": len(prediction),
            "pass": len([config for config in prediction if "result" in config and config["result"]]),
        }
        return {
            "files": files,
            "overall": overall,
        }

    @property
    def metrics(self) -> Dict[str, Callable[[Dict, None], Any]]:
        return {
            "score": self.metric,
        }

    def get_data(self) -> Dataset:
        ret = Dataset()
        for item in self.problem_configs:
            ret.append(DataPiece(item, None))
        return ret

    def predict_single(self, session: Session, data_item: Dict):
        config = data_item["config"]
        file = data_item["file"]
        index_in_file = data_item["index"]
        error_message = None
        container = Container(config.image)
        try:
            result = self._judge(session, config, container)
        except Exception as e:
            error_message = e
            result = False
        try:
            container.__del__()
        except:
            pass
        return {
            "history": session.history,
            "result": result,
            "error": error_message,
            "file": file,
            "index_in_file": index_in_file,
        }

    def _judge(self, session: Session, config: JudgeConfig, container: Container):
        if config.init_script:
            for script in config.init_script:
                container.execute_independent(script)
        if config.start:
            container.execute(config.start[1])

        def get_answer():
            session.inject({
                "role": "user",
                "content": """You are an assistant that will act like a person, I'will play the role of linux(ubuntu) operating system. Your goal is to implement the operations required by me or answer to the question proposed by me. For each of your turn, you should take exact one of the two actions: "bash" or "commit". You should print a json format: {"thought": "Your thoughts to the problem and current action.", "action": str(either "bash" or "commit"), "content": str(For bash, this is the bash script you want to execute. For commit, this is the final answer to the question of the user. If no need to commit an answer, just make "content": null)}\nIf the output is too long, I will truncate it. The truncated output is not complete. You have to deal with the truncating problem by yourself. You could write a script to accomplish what you want. Attention, your bash code should not contain any input operation.\n\nNow, my problem is:\n\n""" + config.description
            })

            for _ in range(self.round_limit):
                try:
                    root = session.action()
                    print(root)
                except Exception as e:
                    # print("Error", str(e), traceback.format_exc(), sep=" | ")
                    return
                if "action" not in root or root["action"] not in ["bash", "commit"]:
                    # print("Error", "Invalid Action Field", traceback.format_exc(), sep=" | ")
                    return

                action = root["action"]
                content = root["content"]
                if action == "commit":
                    return content
                elif action == "bash":
                    result = container.execute(content).output.decode('utf-8')
                    if len(result) > 800:
                        result = result[:780] + "\n[truncated because the output is too long]"
                    session.inject({
                        "role": "user",
                        "content": "The output of the OS:\n\n" + result
                    })
        answer = get_answer()

        if isinstance(answer, str) and config.match and config.match["strip"]:
            answer = answer.strip()

        if config.match:
            if "answer" in config.match:
                return answer == config.match["answer"]
            elif "regex" in config.match:
                return re.search(config.match["regex"], answer) is not None
        elif config.check:
            params = [str(answer)]
            for script in config.check:
                if script is None:
                    script = config.example_script
                response = container.execute_independent(script, *params)
                # print("OUTPUT", response.output.decode("utf-8"))
                # print("RETURN", response.exit_code)
                if response.exit_code != 0:
                    return False
                params.append(response.output.decode("utf-8"))
            return True
        else:
            raise Exception("Invalid evaluation_type in config")
