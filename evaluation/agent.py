from typing import List
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


from dataclass_wizard import YAMLWizard
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List, Dict


class Session:
    def __init__(self, model_inference, history=None) -> None:
        self.history: list[dict] = history or []
        self.model_inference = model_inference

    def inject(self, message: dict) -> None:
        assert isinstance(message, dict)
        assert "role" in message and "content" in message
        assert isinstance(message["role"], str)
        assert isinstance(message["content"], str)
        assert message["role"] in ["user", "agent"]
        self.history.append(message)

    def action(self, extend_messages=None) -> str:
        extend = []
        if extend_messages:
            if isinstance(extend_messages, list):
                extend.extend(extend_messages)
            elif isinstance(extend_messages, dict):
                extend.append(extend_messages)
            else:
                raise Exception("Invalid extend_messages")
        result = self.model_inference(self.history + extend)
        self.history.extend(extend)
        self.history.append({"role": "agent", "content": result})
        return result


class TaskType(Enum):
    MULTICHOICE = "mul"
    GENERATION = "gen"
    LANGUAGE_MODEL = "lm"
    OTHER = "other"


@dataclass
class AgentConfig(YAMLWizard):
    module: str = None  # Agent module
    parameters: dict = field(default_factory=dict)  # Agent parameters

    @classmethod
    def create_agent(cls, module, parameters={}) -> "Agent":
        path = ".".join(module.split(".")[:-1])
        mod = __import__(path, fromlist=[module.split(".")[-1]])
        return getattr(mod, module.split(".")[-1])(**parameters)

    @classmethod
    def create_agent_from_yaml(cls, yaml_path) -> "Agent":
        config = cls.from_yaml_file(yaml_path)
        return cls.create_agent(config.module, config.parameters)


class Agent:
    def __init__(self) -> None:
        pass

    def create_session(self) -> Session:
        return Session(self.inference)

    def inference(self, history: List[dict]) -> str:
        raise NotImplementedError


class LocalAgent(Agent):
    def __init__(self, url, **kwargs) -> None:
        super().__init__()
        self.url = url
        self.parameters = kwargs

    def inference(self, history: List[dict]) -> str:
        resp = requests.post(self.url, json={
            "messages": history,
            **self.parameters
        })
        if resp.status_code != 200:
            raise Exception(f"Invalid status code {resp.status_code}:\n\n{resp.text}")
        try:
            return resp.json()
        except:
            raise Exception(f"Invalid response:\n\n{resp.text}")


class DoNothingAgent(Agent):
    """This agent is a test agent, which does nothing. (return empty string for each action)"""

    def __init__(self) -> None:
        super().__init__()

    def inference(self, history: List[dict]) -> str:
        return ""
