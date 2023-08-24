import argparse
import json
import time
import requests
import os, json, sys, time, re, math, random, datetime, argparse, requests
from typing import List, Dict, Any

from fastchat.model.model_adapter import get_conversation_template
from src.agent import Agent

# import TimeoutException
from requests.exceptions import Timeout, ConnectionError


class APIAgent(Agent):
    """This agent is a test agent, which does nothing. (return empty string for each action)"""

    def __init__(self, model_name, temperature=0, max_new_tokens=32, top_p=0, **kwargs) -> None:
        self.model_name = model_name
        self.temperature = temperature
        self.max_new_tokens = max_new_tokens
        self.top_p = top_p
        print(self.max_new_tokens)
        super().__init__(**kwargs)

    def inference(self, history: List[dict]) -> str:
        for _ in range(3):
            try:
                time.sleep(0.2)
                url = 'http://180.184.39.132:9629/call_api'
                headers = {'Content-Type': 'application/json; charset=utf-8'}
                msg = {
                    "messages": [[{
                        "role": "user" if (item["role"] == "user") else "assistant",
                        "content": item["content"],
                    } for item in history]],
                    "model": self.model_name,
                }
                resp = requests.post(url, headers=headers, data=json.dumps(msg), timeout=120)
                if resp.status_code != 200:
                    raise Exception(f"Invalid status code {resp.status_code}:\n\n{resp.text}")
                try:
                    return resp.json()["data"][0]
                except:
                    raise Exception(f"Invalid response:\n\n{resp.text}")
            except:
                pass
        return ""

class APIAgent_claude(Agent):
    """This agent is a test agent, which does nothing. (return empty string for each action)"""

    def __init__(self, model_name, temperature=0, max_new_tokens=32, top_p=0, **kwargs) -> None:
        self.model_name = model_name
        self.temperature = temperature
        self.max_new_tokens = max_new_tokens
        self.top_p = top_p
        print(self.max_new_tokens)
        super().__init__(**kwargs)

    def inference(self, history: List[dict]) -> str:
        for _ in range(3):
            try:
                time.sleep(0.2)
                url = 'http://40.74.217.35:10015/api/chat'
                headers = {"content-type": "application/json; charset=utf-8"}
                msg = {
                    "messages": [{
                        "role": "user" if (item["role"] == "user") else "assistant",
                        "content": item["content"],
                    } for item in history],
                    "model": self.model_name,
                    "max tokens": 256,
                }
                resp = requests.post(url, headers=headers, data=json.dumps(msg), timeout=120)
                if resp.status_code != 200:
                    raise Exception(f"Invalid status code {resp.status_code}:\n\n{resp.text}")
                try:
                    return resp.text
                except:
                    raise Exception(f"Invalid response:\n\n{resp.text}")
            except:
                pass
        return ""

class APIAgent_completion(Agent):
    """This agent is a test agent, which does nothing. (return empty string for each action)"""

    def __init__(self, model_name, temperature=0, max_new_tokens=32, top_p=0, **kwargs) -> None:
        self.model_name = model_name
        self.temperature = temperature
        self.max_new_tokens = max_new_tokens
        self.top_p = top_p
        print(self.max_new_tokens)
        super().__init__(**kwargs)

    def inference(self, history: List[dict]) -> str:
        for _ in range(3):
            try:
                time.sleep(0.2)
                url = 'http://40.74.217.35:10015/api/completion'
                headers = {"content-type": "application/json; charset=utf-8"}
                msg = {
                    "prompt": history[-1]["content"],
                    "model": self.model_name,
                    "max_tokens": 256,
                }
                resp = requests.post(url, headers=headers, data=json.dumps(msg), timeout=120)
                if resp.status_code != 200:
                    raise Exception(f"Invalid status code {resp.status_code}:\n\n{resp.text}")
                try:
                    return resp.text
                except:
                    raise Exception(f"Invalid response:\n\n{resp.text}")
            except:
                pass
        return ""
