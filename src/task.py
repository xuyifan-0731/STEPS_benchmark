'''
from .agent import Agent, Session


class TaskConfig:
    pass


class Task:
    def evaluate(self, agent: Agent):
        raise NotImplementedError

    def predict_all(self, agent: Agent, dataset):
        pass

    def predict_single(self, session: Session, data):
        raise NotImplementedError
'''

import os
import time
import json
import jsonlines
import traceback
import threading
import numpy as np
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor, as_completed

from typing import Dict, Callable, Type, Tuple, List, Any, Union, Iterable, Generic, TypeVar
from abc import ABC, abstractmethod
from glob import glob
from os.path import join, relpath
from collections import defaultdict
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

from .utils import print_rank_0
from .metrics import DEFAULT_METRICS
# from .model_api import get_model_api
from .agent import Agent, Session

T_INPUT = TypeVar('T_INPUT')
T_TARGET = TypeVar('T_TARGET')


class DataPiece(Generic[T_INPUT, T_TARGET]):
    def __init__(self, input: T_INPUT, target: T_TARGET):
        self.input = input
        self.target = target


class Dataset(Generic[T_INPUT, T_TARGET], List[DataPiece[T_INPUT, T_TARGET]]):
    def get_inputs(self) -> List[T_INPUT]:
        return [item.input for item in self]

    def get_targets(self) -> List[T_TARGET]:
        return [item.target for item in self]


class Task(Generic[T_INPUT, T_TARGET]):
    def __init__(self, name=None, workers=1):
        assert isinstance(workers, int)
        assert workers > 0
        self.name = name
        self.workers = workers

    def evaluate(self, agent: Agent):
        print_rank_0(f"Evaluating task '{self.name}' ...")
        data = self.get_data()
        inputs = data.get_inputs()
        targets = data.get_targets()
        results = self.predict_all(agent, inputs)
        result_dict = {}
        for metric in self.metrics:
            result_dict[metric] = self.metrics[metric](results, targets)
        print_rank_0(f"Task '{self.name}' evaluation results: {result_dict}")
        return result_dict

    def predict_all(self, agent: Agent, inputs: List[T_INPUT]) -> List:
        print(f"Start Predicting All ...")

        executor = ThreadPoolExecutor(self.workers)

        threads = []
        results = [None] * len(inputs)

        def call_wrap(data_item, index):
            try:
                result = self.predict_single(agent.create_session(), data_item)
            except:
                pass
            results[index] = result

        for idx, item in enumerate(inputs):
            future = executor.submit(call_wrap, item, idx)
            threads.append(future)

        with tqdm(total=len(inputs)) as pbar:
            for thread in as_completed(threads):
                pbar.update(1)

        return results

    @property
    def metrics(self) -> Dict[str, Callable[[List[T_INPUT], List[T_TARGET]], float]]:
        return {"EM": lambda outputs, targets: len([1 for o, t in zip(outputs, targets) if o == t]) / min(len(outputs), len(targets))}

    def get_data(self) -> Dataset[T_INPUT, T_TARGET]:
        raise NotImplementedError

    def predict_single(self, session: Session, data_item: T_INPUT):
        raise NotImplementedError
