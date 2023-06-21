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

from src.utils import print_rank_0
from src.configs import SingleRoundConfig
from src.dataset import SingleRoundTaskDataset
from src.metrics import DEFAULT_METRICS
from src.agent import Agent, Session
from src.task import Task

class SingleRoundTask(Task[str, int]):
    def __init__(self, name, workers, **config):
        super().__init__(name, workers)
        self.config = SingleRoundConfig(**config)
        self.config.name = name
        self.config.workers = workers
        self.config.metrics = list(self.metrics.keys())
        self.file_groups = self.get_file_groups()
        self.model_name = ""

    @property
    def metrics(self) -> Dict[str, Callable]:
        return {metric: DEFAULT_METRICS[metric] for metric in self.config.metrics}

    def build_dataset(self, relative_path):
        return SingleRoundTaskDataset(join(self.config.datapath, relative_path), self.config)

    def get_file_groups(self):
        pattern_group = {}
        if isinstance(self.config.filepattern, str):
            pattern_group["all"] = self.config.filepattern
        else:
            pattern_group = self.config.filepattern
        return {
            name: [
                relpath(path, start=self.config.datapath)
                for path in sorted(glob(join(self.config.datapath, pattern), recursive=True))
            ]
            for name, pattern in pattern_group.items()
        }

    def evaluate(self, agent: Agent):
        self.model_name = agent.name
        start = time.time()
        print_rank_0("\n")
        print_rank_0(f"{self.config}")
        print_rank_0(f"Evaluating task '{self.name}' ...")
        result_dict_all = {}

        for group_name, filelist in self.file_groups.items():
            print_rank_0(f"    Evaluating group {group_name}:")

            result_dict_group = {}
            for file in filelist:
                dataset = self.build_dataset(file)
                prediction = self.predict_all(agent, dataset)

                if self.config.save_prediction:  # first save and evaluate
                    self.save_prediction_to_file(file, prediction, dataset.data)

                try:
                    ## evaluation
                    result_dict = {}
                    for key, metric in self.metrics.items():
                        metric_result = metric(prediction, dataset.data, self.config)
                        if isinstance(metric_result, dict):
                            for sub_key, sub_metric in metric_result.items():
                                result_dict[sub_key] = sub_metric
                        else:
                            result_dict[key] = metric_result

                    if self.config.save_evaluation:
                        result_dict["length"] = len(dataset)
                        self.save_evaluation_to_file(file, result_dict)

                    result_dict_group[file] = (result_dict, len(dataset))

                    self.report_single_metrics(file, result_dict)
                except Exception as e:
                    print(f"error in evaluation {file} : {e}")
                    traceback.print_exc()
                    result_dict = {}
                    result_dict["error"] = f"error in evaluation {file} : {e}"
                    if self.save_evaluation:
                        result_dict["length"] = len(dataset)
                        self.save_evaluation_to_file(file, result_dict)

            result_dict_all[group_name] = result_dict_group

        print_rank_0(f"Evaluation results of task {self.config.name}:")

        for group_name, result_dict_group in result_dict_all.items():
            self.report_group_metrics(group_name, result_dict_group)

        print_rank_0(f"Finish task {self.config.name} in {time.time() - start:.1f}s.")

    def report_single_metrics(self, file: str, result_dict: Dict[str, float]):
        output_str = f"        Finish {file}"
        for key, value in result_dict.items():
            output_str += f", {key} = {value:.3f}"
        print_rank_0(output_str)

    @staticmethod
    def calc_group_metrics(result_dict_group: Dict[str, Tuple[Dict[str, float], int]]):
        metrics_dict = defaultdict(lambda: [])
        weight = []
        for file, (result_dict, length) in result_dict_group.items():
            for key, value in result_dict.items():
                metrics_dict[key].append(value)
            weight.append(length)
        return {
            name: {
                "max": np.max(value),
                "median": np.median(value),
                "average": np.average(value, weights=weight),
            }
            for name, value in metrics_dict.items()
        }

    def report_group_metrics(self, group_name, result_dict_group: Dict[str, Tuple[Dict[str, float], int]], level=1):
        stats_dict = self.calc_group_metrics(result_dict_group)
        if len(stats_dict) == 1:
            name, stats = next(iter(stats_dict.items()))
            print_rank_0(
                "    " * level + f"Group {group_name} {name}: max = {stats['max']:.3f}, "
                f"median = {stats['median']:.3f}, average = {stats['average']:.3f}"
            )
        else:
            print_rank_0("    " * level + f"  Group {group_name}: ")
            for name, stats in stats_dict.items():
                print(
                    "    " * (level + 1) + f"Metric {name}: max = {stats['max']:.3f}, "
                    f"median = {stats['median']:.3f}, average = {stats['average']:.3f}"
                )

    def save_prediction_to_file(self, file, prediction, data):
        filename = os.path.join("outputs", self.config.name, self.model_name, "prediction",
                                f"{self.model_name}.{file}.predict.jsonl")
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        with jsonlines.open(filename, "w") as file:
            for item, org_data in zip(prediction, data):
                output_data = org_data[0]
                output_data["prediction"] = item
                file.write(output_data)

    def save_evaluation_to_file(self, file, res_dict):
        filename = os.path.join("outputs", self.config.name, self.model_name, "evaluation",
                                f"{self.model_name}.{file}.evaluate.json")
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        with open(filename, "w", encoding="utf-8") as f:
            f.write(json.dumps(res_dict, indent=2))
            f.close()
