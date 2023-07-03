from src.agent import Agent
import os, json, sys, time, re, math, random, datetime, argparse, requests
from typing import List, Dict, Any, Optional, Union, Tuple, Callable, Type, TypeVar

class LocalAgent(Agent):
    def __init__(self, url, **kwargs) -> None:
        super().__init__(**kwargs)
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
