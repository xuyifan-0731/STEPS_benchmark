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

    def action(self, extend_messages: list[dict] = None) -> str:
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
    def __init__(self, name=None) -> None:
        self.name = name
        pass

    def create_session(self) -> Session:
        return Session(self.inference)

    def inference(self, history: List[dict]) -> str:
        raise NotImplementedError
