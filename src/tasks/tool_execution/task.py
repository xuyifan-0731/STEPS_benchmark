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
from .tool_server import create_server_process
from .tool_client import ToolClient


class ToolEvaluationData:
    def __init__(self, config, check_function_module=None) -> None:
        self.config = config
        assert isinstance(config, dict)
        assert "query" in config and "tool_usage" in config
        self.query = config["query"]
        self.additional_information = config.get("additional_information", None)
        self.reasoning = None
        reasoning_function_name = config.get("reasoning", None)
        if reasoning_function_name and check_function_module:
            # from check_function_module get the function
            self.reasoning = getattr(check_function_module, reasoning_function_name)
            # make sure the function is like check_problem_1(data: dict, answer: str) -> float
            assert isinstance(self.reasoning, Callable)
            assert self.reasoning.__code__.co_argcount == 2
            assert self.reasoning.__code__.co_varnames[0] == "data"
            assert self.reasoning.__code__.co_varnames[1] == "answer"

        self.tool_usage = config["tool_usage"]  # list[{"tool": str, "input": dict}]

    def get_max_stage(self):
        if self.reasoning:
            return 3
        else:
            return 2


class ToolPrediction:
    session: Session
    query: str
    additional_information: str = None
    choosing: str = None
    calling: dict = None
    reasoning: str = None
    message: str = ""

    def __init__(self, session: Session, query: str, addtional_information: str = None) -> None:
        self.session = session
        self.query = query
        self.additional_information = addtional_information

    def get_json(self):
        return {
            "query": self.query,
            "additional_information": self.additional_information,
            "choosing": self.choosing,
            "calling": self.calling,
            "reasoning": self.reasoning,
            "history": self.session.history,
            "message": self.message
        }


class ToolExecution(Task[int, str]):
    def _load_glob_data(self, glob_dir):
        configs = []
        for dir_path in glob.glob(glob_dir):
            # if 'check.py' exists, import that module
            check_file_path = os.path.join(dir_path, "check.py")
            check_module = None
            if os.path.exists(check_file_path):
                spec = importlib.util.spec_from_file_location("check_function_module", check_file_path)
                check_module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(check_module)

            # check if data.json exists
            if not os.path.exists(os.path.join(dir_path, "data.json")):
                continue
            with open(os.path.join(dir_path, "data.json"), "r", encoding="utf-8") as f:
                data = json.load(f)
                for item in data:
                    configs.append(ToolEvaluationData(item, check_module))

        return configs

    def __init__(
        self, name=None, workers=1,
        tool_root_dir="data/tool_execution/server", host="0.0.0.0", port=10001,
        data_paths="data/tool_execution/data/*",
        max_stage=3,
    ):
        super().__init__(name, workers)
        self.tool_server_process = create_server_process(tool_root_dir, host, port)
        self.tool_pool = ToolClient("http://%s:%d" % (host, port))
        self.configs = [
            (ToolEvaluationData(config) if isinstance(config, dict) else config)
                for config in self._load_glob_data(data_paths)
        ]
        self.max_stage = max_stage
        assert max_stage <= 3 and max_stage > 0 
        for config in self.configs:
            for tool_usage in config.tool_usage:
                # print(tool_usage["tool"])
                assert tool_usage["tool"] in self.tool_pool
        
        

    @property
    def metrics(self) -> Dict[str, Callable[[List[ToolPrediction], List[ToolEvaluationData]], float]]:
        return {"EM": lambda outputs, targets: len([1 for o, t in zip(outputs, targets) if o == t]) / min(len(outputs), len(targets))}

    def get_data(self) -> Dataset[ToolEvaluationData, ToolEvaluationData]:
        ret = Dataset()
        for item in self.configs:
            ret.append(DataPiece(item, item))
        return ret

    def predict_single(self, session: Session, data_item: ToolEvaluationData):
        result = ToolPrediction(session, data_item.query, data_item.additional_information)
        for _ in range(0, 3):
            try:
                if self.max_stage < 1:
                    return result
                if not self.tool_choosing(result, data_item):
                    return result
            except Exception as e:
                # import traceback
                # traceback.print_exc()
                # continue
                pass
            break
        else:
            return result
        
        if result.choosing not in [tool_usage["tool"] for tool_usage in data_item.tool_usage]:
            return result
        
        for _ in range(0, 3):
            try:
                if self.max_stage < 2:
                    return result
                if not self.tool_calling(result):
                    return result
            except Exception as e:
                # import traceback
                # traceback.print_exc()
                # continue
                pass
            break
        else:
            return result
        
        flag = False
        for tool_usage in data_item.tool_usage:
            if tool_usage["tool"] == result.choosing and tool_usage == result.calling:
                flag = True
                break
        if not flag:
            # result.calling = None
            return result
        
        for _ in range(0, 3):
            try:
                if self.max_stage < 3:
                    return result
                if not self.reasoning(result):
                    return result
            except Exception as e:
                pass
            break
        else:
            return result

    def tool_choosing(self, result: ToolPrediction, config: ToolEvaluationData) -> bool:
        """
        Input: session, query, target_choosing
        Output: correct, tool_choosing_result
        """
        session = result.session
        instruction = "Please choose a tool to solve the problem from the following list:\n\n%s\n\nYou should strictly follow the format:\n\nChoose Tool: [Name of the tool].\n\nFor example:\n\nChoose Tool: %s.\n\nThe problem is: %s\n\n%s" % (

            "\n".join(["%s: %s" % (tool.name, tool.description) for tool in self.tool_pool.values()]), random.choice([tool.name for tool in self.tool_pool.values()]),
            result.query, f"The additional information of the user: {result.additional_information}" if result.additional_information else "",
        )

        session.inject({"role": "user", "content": instruction})
        resp = session.action()
        # resp = re.findall(r"Choose Tool: (.*)\.", resp)

        # if len(resp) != 1:
        #     return False

        # resp = resp[0].strip()
        # for tool in self.tool_pool.values():
        #     if tool.name == resp:
        #         result.choosing = tool.name
        #         return True

        # all correct tools
        correct_tools = set()
        for tool in config.tool_usage:
            correct_tools.add(tool["tool"])

        # all tools in the response
        resp_tools = set()
        for tool in self.tool_pool.values():
            if tool.name in resp:
                resp_tools.add(tool.name)

        # check if the response is a subset of the correct tools
        if len(resp_tools) > 0 and resp_tools.issubset(correct_tools):
            result.choosing = resp_tools.pop()
            return True

        return False
    
    def tool_calling(self, result: ToolPrediction) -> bool:
        """ 
        Input: session, tool, target_parameters
        Output: correct, tool_usage_result
        """
        session = result.session
        resps = session.action(
            {"role": "user", "content": "Now, please use %s to solve the problem. You should print a json format to call the tool.\nThe document of the tool is shown below.\n\n%s" %
             (result.choosing, self.tool_pool[result.choosing].full_documentation)})
        # To find a json format
        resp = re.findall(r"\{.*\}", resps, re.DOTALL)
        # print("======\n%s\n-------\n%s\n======" % (resps, resp))

        # print(resp)

        if len(resp) == 0:
            return False

        for item in resp:
            try:
                # print("~~~~\n%s\n~~~~" % item)
                ret = json.loads(item)
                # print("~~ OK ~~\n%s\n~~~~" % item)
                break
            except:
                return False
        else:
            return False
        if not isinstance(ret, dict):
            return False

        result.calling = ret
        return True
    
    def reasoning(self, result: ToolPrediction) -> bool:
        """ 
        Input: session, target_reasoning
        Output: correct, tool_reasoning_result
        """
        session = result.session
        # calling:
        try:
            cal = self.tool_pool[result.choosing](result.calling["input"])
            if len(cal) > 1000:
                cal = cal[:900] + " ...... " + cal[-50:]
        except Exception as e:
            cal = "Error occurs when calling the tool: %s" % str(e)
        resp = session.action({"role": "user", "content": "Return of the tool: \n\n%s\n\nNow, based on your tool choosing and calling, please tell me the final answer of the problem." % cal})
        result.reasoning = resp
        return True