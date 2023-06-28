from src.agent import Agent
from typing import List, Dict, Any, Optional, Union, Tuple, Callable, Type, TypeVar
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


class ChatGLM_6b_v2(Agent):
    def __init__(self, url, name=None, **kwargs) -> None:
        super().__init__(name)
        self.url = url
        self.parameters = kwargs

    def inference(self, history: List[dict]) -> str:
        headers = {
            'Authorization': 'key-Z1rbNzO7YtPVHFhI',
            'Content-Type': 'application/json'
        }
        resp = requests.post(self.url, json={
            "messages": history,
            **self.parameters
        }, headers=headers)
        if resp.status_code != 200:
            raise Exception(f"Invalid status code {resp.status_code}:\n\n{resp.text}")
        try:
            return json.loads(resp.text).get("result", "ERROR")
        except:
            raise Exception(f"Invalid response:\n\n{resp.text}")