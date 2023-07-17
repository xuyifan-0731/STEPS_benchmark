import openai
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
from typing import List, Callable
import dataclasses
from copy import deepcopy


class OpenAIChatCompletion(Agent):
    def __init__(self, api_args=None, **config):
        if not api_args:
            api_args = {}
        api_args = deepcopy(api_args)
        api_args["key"] = api_args.pop("key", None) or os.getenv('OPENAI_API_KEY')
        api_args["model"] = api_args.pop("model", None)
        if not api_args["key"]:
            raise ValueError("OpenAI API key is required, please assign api_args.key or set OPENAI_API_KEY environment variable.")
        if not api_args["model"]:
            raise ValueError("OpenAI model is required, please assign api_args.model.")
        self.api_args = api_args
        super.__init__(**config)

    def inference(self, history: List[dict]) -> str:
        history = json.loads(json.dumps(history))
        for h in history:
            if h['role'] == 'agent':
                h['role'] = 'assistant'

        resp = openai.ChatCompletion.create(
            messages=history,
            **self.api_args
        )

        return resp.json()["choices"][0]["message"]["content"]


class OpenAICompletion(Agent):
    def __init__(self, api_args=None, **config):
        if not api_args:
            api_args = {}
        api_args = deepcopy(api_args)
        api_args["key"] = api_args.pop("key", None) or os.getenv('OPENAI_API_KEY')
        api_args["model"] = api_args.pop("model", None)
        if not api_args["key"]:
            raise ValueError("OpenAI API key is required, please assign api_args.key or set OPENAI_API_KEY environment variable.")
        if not api_args["model"]:
            raise ValueError("OpenAI model is required, please assign api_args.model.")
        self.api_args = api_args
        super.__init__(**config)

    def inference(self, history: List[dict]) -> str:
        prompt = ""
        for h in history:
            role = 'Assistant' if h['role'] == 'agent' else h['role']
            content = h['content']
            prompt += f"{role}: {content}\n\n"
        prompt += 'Assistant: '

        resp = openai.Completion.create(
            prompt=prompt,
            **self.api_args
        )

        return resp.json()["choices"][0]["text"]