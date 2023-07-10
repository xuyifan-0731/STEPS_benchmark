from src.agent import Agent
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
from typing import List, Dict, Any, Optional, Union, Tuple, Callable, Type, TypeVar

GPT_TURBO_SERVER_URL = os.environ.get("GPT_TURBO_SERVER_URL")
GPT_TURBO_SERVER_AUTHORIZATION = os.environ.get("GPT_TURBO_SERVER_AUTHORIZATION")
if GPT_TURBO_SERVER_URL is None or GPT_TURBO_SERVER_AUTHORIZATION is None:
    raise Exception("Please set environment variables GPT_TURBO_SERVER_URL and GPT_TURBO_SERVER_AUTHORIZATION")


class OpenAIChatCompletion(Agent):
    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.parameters = kwargs

    def inference(self, history: List[dict]) -> str:
        for _ in range(3):
            try:
                resp = requests.post(GPT_TURBO_SERVER_URL, json={
                    "messages": [{
                        "role": "user" if (item["role"] == "user") else "assistant",
                        "content": item["content"],
                    } for item in history],
                    "model": self.name,
                }, headers={
                    "Authorization": GPT_TURBO_SERVER_AUTHORIZATION,
                }, timeout=30)
                if resp.status_code != 200:
                    raise Exception(f"Invalid status code {resp.status_code}:\n\n{resp.text}")
                try:
                    return resp.json()["choices"][0]["message"]["content"]
                except:
                    raise Exception(f"Invalid response:\n\n{resp.text}")
            except:
                pass
        return ""
