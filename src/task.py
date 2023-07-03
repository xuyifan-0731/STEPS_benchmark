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

# from .utils import print_rank_0
# from .model_api import get_model_api
from .agent import Agent, Session
from .utils import serialize


T_INPUT = TypeVar('T_INPUT')
T_OUTPUT = TypeVar('T_OUTPUT')
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


class Task(Generic[T_INPUT, T_OUTPUT, T_TARGET]):
    def __init__(self, **kwargs):
        self.name = kwargs.pop("name", None)
        self.workers = kwargs.pop("workers", 1)
        self.category = kwargs.pop("category", None)
        self.src = kwargs.pop("src", None)
        self.output_root_dir = None
        assert isinstance(self.workers, int) and self.workers > 0
        assert isinstance(self.name, str)
        if kwargs:
            for key in kwargs:
                print(f"Warning: Unknown argument '{key}' for the task.")

    def release(self):
        pass

    def evaluate(self, agent: Agent) -> Dict[str, Any]:
        print(f"Evaluating task '{self.name}' ...")
        data = self.get_data()
        inputs = data.get_inputs()
        targets = data.get_targets()
        results = self.predict_all(agent, inputs)
        result_dict = {}
        for metric in self.metrics:
            result_dict[metric] = self.metrics[metric](results, targets)
        print(f"Task '{self.name}' evaluation finished. The results are saved in '{self.get_output_dir()}'")
        self.save_runs_all(inputs, results, targets, result_dict)
        return result_dict

    def predict_all(self, agent: Agent, inputs: List[T_INPUT]) -> List[T_OUTPUT]:
        print(f"Start Predicting All ...")

        executor = ThreadPoolExecutor(self.workers)

        threads = []
        results = [None] * len(inputs)

        def call_wrap(data_item, index):
            try:
                result = self.predict_single(agent.create_session(), data_item)
                self.save_single(index, data_item, result)
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

    def save_single(self, index: int, input: T_INPUT, output: T_OUTPUT):
        save_obj = {
            "index": index,
            "input": serialize(input),
            "output": serialize(output)
        }
        if not os.path.exists(self.get_output_dir()):
            os.makedirs(self.get_output_dir())
        with open(os.path.join(self.get_output_dir(), "generation.jsonl"), "a", encoding="utf-8") as f:
            f.write(json.dumps(save_obj) + "\n")

    def save_runs_all(self, inputs: List[T_INPUT], outputs: List[T_OUTPUT], targets: List[T_TARGET], metrics: Dict[str, Any] = None):
        if not os.path.exists(self.get_output_dir()):
            os.makedirs(self.get_output_dir())
        for idx, (input, output, target) in enumerate(zip(inputs, outputs, targets)):
            save_obj = {
                "index": idx,
                "input": serialize(input),
                "output": serialize(output),
                "target": serialize(target)
            }
            with open(os.path.join(self.get_output_dir(), "runs.jsonl"), "a", encoding="utf-8") as f:
                f.write(json.dumps(save_obj) + "\n")
        self.save_metrics_all(metrics)

    def save_metrics_all(self, metrics: Dict[str, Any]):
        if not os.path.exists(self.get_output_dir()):
            os.makedirs(self.get_output_dir())
        with open(os.path.join(self.get_output_dir(), "results.json"), "w", encoding="utf-8") as f:
            f.write(json.dumps(metrics, indent=4))

    def get_output_dir(self) -> str:
        """
            Default output directory is: outputs/{time_str}/{name or category}
        """
        if not self.output_root_dir:
            self.output_root_dir = "outputs/%s" % datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
        return os.path.join(self.output_root_dir, self.category or self.name or "default")

    @property
    def metrics(self) -> Dict[str, Callable[[List[T_OUTPUT], List[T_TARGET]], Any]]:
        return {"EM": lambda outputs, targets: len([1 for o, t in zip(outputs, targets) if o == t]) / min(len(outputs), len(targets))}

    def get_data(self) -> Dataset[T_INPUT, T_TARGET]:
        raise NotImplementedError

    def predict_single(self, session: Session, data_item: T_INPUT) -> T_OUTPUT:
        raise NotImplementedError
