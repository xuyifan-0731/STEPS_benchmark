import json
import re

import requests


class Agent:
    def message(self, msg: str):
        # handle user message to agent
        raise NotImplementedError

    def act(self) -> dict:
        # expect agent's response
        raise NotImplementedError