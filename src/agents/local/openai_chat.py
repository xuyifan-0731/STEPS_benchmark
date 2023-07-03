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


class OpenAIChatCompletion(Agent):
    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.parameters = kwargs

    def inference(self, history: List[dict]) -> str:
        for _ in range(3):
            try:
                resp = requests.post("http://40.74.217.35:10011/api/openai/chat-completion", json={
                    "messages": [{
                        "role": "user" if (item["role"] == "user") else "assistant",
                        "content": item["content"],
                    } for item in history],
                    "model": self.name,
                }, headers={
                    "Authorization": "a8a730b7731f8c93be4b32228cfea7ed"
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
