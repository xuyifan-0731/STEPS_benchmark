import argparse
import json

import requests
import os, json, sys, time, re, math, random, datetime, argparse, requests
from typing import List, Dict, Any

from fastchat.model.model_adapter import get_conversation_template
from src.agent import Agent
from requests.exceptions import Timeout

class FastChatAgent(Agent):
    """This agent is a test agent, which does nothing. (return empty string for each action)"""

    def __init__(self, model_name, controller_address=None, worker_address=None, temperature=0, max_new_tokens=32, **kwargs) -> None:
        if controller_address is None and worker_address is None:
            raise ValueError("Either controller_address or worker_address must be specified.")
        self.controller_address = controller_address
        self.worker_address = worker_address
        self.model_name = model_name
        self.temperature = temperature
        self.max_new_tokens = max_new_tokens
        super().__init__(**kwargs)

    def inference(self, history: List[dict]) -> str:
        if self.worker_address:
            worker_addr = self.worker_address
        else:
            controller_addr = self.controller_address
            # ret = requests.post(controller_addr + "/refresh_all_workers")
            # ret = requests.post(controller_addr + "/list_models")
            # print(ret.json())
            # models = ret.json()["models"]
            # models.sort()
            # print(f"Models: {models}")
            # ret = requests.post(
            #     controller_addr + "/get_worker_address", json={"model": self.model_name}
            # )
            worker_addr = controller_addr
            # print(f"worker_addr: {worker_addr}")
        if worker_addr == "":
            # print(f"No available workers for {self.model_name}")
            return
        conv = get_conversation_template(self.model_name)
        for history_item in history:
            role = history_item["role"]
            content = history_item["content"]
            if role == "user":
                conv.append_message(conv.roles[0], content)
            elif role == "agent":
                conv.append_message(conv.roles[1], content)
            else:
                raise ValueError(f"Unknown role: {role}")
        conv.append_message(conv.roles[1], None)
        prompt = conv.get_prompt()
        headers = {"User-Agent": "FastChat Client"}
        gen_params = {
            "model": self.model_name,
            "prompt": prompt,
            "temperature": self.temperature,
            "max_new_tokens": self.max_new_tokens,
            "stop": conv.stop_str,
            "stop_token_ids": conv.stop_token_ids,
            "echo": False,
        }
        
        max_attempts = 3
        timeout = 120.0
        attempt = 0

        while attempt < max_attempts:
            try:
                response = requests.post(
                    controller_addr + "/worker_generate_stream",
                    headers=headers,
                    json=gen_params,
                    stream=True,
                    timeout=120.0  # This is your timeout value in seconds
                )
                break
            except Timeout:
                print("The request timed out, retrying...")
                attempt += 1

        if attempt == max_attempts:
            print("Maximum number of attempts reached, the request has failed due to timeout.")
            return "None"
        text = ""
        for line in response.iter_lines(decode_unicode=False, delimiter=b"\0"):
            if line:
                text = json.loads(line)["text"]
        return text

