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


class Agent:
    def __init__(self) -> None:
        pass

    def create_session(self) -> Session:
        return Session(self.inference)

    def inference(self, history: List[dict]) -> str:
        raise NotImplementedError


class LocalAgent(Agent):
    def __init__(self, url, parameters) -> None:
        super().__init__()
        self.url = url
        self.parameters = parameters

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
