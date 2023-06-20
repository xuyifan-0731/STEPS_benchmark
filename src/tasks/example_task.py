from src.task import Task, Dataset, DataPiece, Session
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


class ExampleTask(Task[str, int]):
    def __init__(self, name=None, workers=1, count=100, range_min=0, range_max=100):
        super().__init__(name, workers)
        self.count = count
        self.range_min = range_min
        self.range_max = range_max

    def get_data(self) -> Dataset[str, int]:
        data = Dataset()
        for _ in range(self.count):
            x = random.randint(self.range_min, self.range_max)
            y = random.randint(self.range_min, self.range_max)
            data.append(DataPiece("Your answer should only contain the integer number (without comma), for example, for a question 'what is the answer of 5000 + 5000?', your should print only '10000'. Now, answer the question: What is the answer of {} + {}?".format(x, y), x + y))
        return data

    def predict_single(self, session: Session, data_item: str) -> str:
        return session.action({"role": "user", "content": data_item})
