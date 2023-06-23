import os
import json
import jsonlines
import time
from glob import glob
from os.path import join, relpath
from collections import defaultdict
from typing import Dict, Tuple
import numpy as np

from src.task import Task, Session
from src.tasks.single_round_tasks.configs import BaseConfig
from src.utils import print_rank_0
from src.agent import Agent, Session
from src.tasks.single_round_tasks.dataset import GenerationTaskDataset
from src.tasks.single_round_tasks.metrics import DEFAULT_METRICS


class SingleRoundTask(Task[str, int]):
    def __init__(self, **kwargs):
        super().__init__(kwargs.get("name"), kwargs.get("workers", 1))
        self.config = BaseConfig.from_dict(kwargs)
        self.file_groups = self.get_file_groups()

    def get_file_groups(self):
        pattern_group = {}
        if isinstance(self.config.file_pattern, str):
            pattern_group["all"] = self.config.file_pattern
        else:
            pattern_group = self.config.file_pattern
        return {
            name: [
                relpath(path, start=self.config.path)
                for path in sorted(glob(join(self.config.path, pattern), recursive=True))
            ]
            for name, pattern in pattern_group.items()
        }

    def evaluate(self, agent: Agent):
        start = time.time()
        print_rank_0("\n")
        print_rank_0(f"{self.config}")
        print_rank_0(f"Evaluating task {self.config.name}:")

        result_dict_all = {}

        for group_name, filelist in self.file_groups.items():
            print_rank_0(f"    Evaluating group {group_name}:")

            result_dict_group = {}
            for file in filelist:
                dataset = self.build_dataset(file) 
                prediction = [""] * len(dataset)        
                inputs = [piece[0]["text"] for piece in dataset]
                results = self.predict_all(agent, inputs)
                
                if self.config.save_prediction: # first save and evaluate 
                    self.save_prediction_to_file(file, results, dataset.data, agent.name)
                
                try:
                    ## evaluation
                    result_dict = {}
                    for key, metric in self.metrics.items():
                        metric_result = metric(prediction, dataset.data, self.config)
                        if isinstance(metric_result,dict):
                            for sub_key, sub_metric in metric_result.items():
                                result_dict[sub_key] = sub_metric
                        else:
                            result_dict[key] = metric_result

                    if self.config.save_evaluation:
                        result_dict["length"] = len(dataset)
                        self.save_evaluation_to_file(file, result_dict, agent.name)
                    
                    result_dict_group[file] = (result_dict, len(dataset))

                    self.report_single_metrics(file, result_dict)
                except Exception as e:
                    print(f"error in evaluation {file} : {e}")
                    result_dict = {}
                    result_dict["error"] = f"error in evaluation {file} : {e}"
                    if self.config.save_evaluation:
                        result_dict["length"] = len(dataset)
                        self.save_evaluation_to_file(file, result_dict, agent.name)

            result_dict_all[group_name] = result_dict_group

        print_rank_0(f"Evaluation results of task {self.config.name}:")

        for group_name, result_dict_group in result_dict_all.items():
            self.report_group_metrics(group_name, result_dict_group)
        self.report_overall_metrics(
            {k: v for result_dict_group in result_dict_all.values() for k, v in result_dict_group.items()},
        )

        print_rank_0(f"Finish task {self.config.name} in {time.time() - start:.1f}s.")
    
    def build_dataset(self, relative_path):
        return GenerationTaskDataset(os.path.join(self.config.path, relative_path), self.config)

    def save_prediction_to_file(self, file, prediction, data, agent_name):
        file = ".".join(file.split(".")[:-1])
        filename = os.path.join("outputs", self.config.name, agent_name, "prediction", f"{agent_name}.{file}.predict.jsonl")
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        with jsonlines.open(filename, "w") as file:
            for item, org_data in zip(prediction, data):
                output_data = org_data[0]
                output_data["prediction"] = item
                file.write(output_data)
    
    def save_evaluation_to_file(self, file, res_dict, agent_name):
        file = ".".join(file.split(".")[:-1])
        filename = os.path.join("outputs", self.config.name, agent_name, "evaluation", f"{agent_name}.{file}.evaluate.json")
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        with open(filename, "w", encoding="utf-8") as f:
            f.write(json.dumps(res_dict, indent=2))
            f.close()

    def report_single_metrics(self, file: str, result_dict: Dict[str, float]):
        output_str = f"        Finish {file}"
        for key, value in result_dict.items():
            output_str += f", {key} = {value:.3f}"
        print_rank_0(output_str)

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

    def report_overall_metrics(self, result_dict_all: Dict[str, Tuple[Dict[str, float], int]]):
        pass

    def predict_single(self, session: Session, data_item: str) -> str:
        return session.action({"role": "user", "content": data_item})

    @property
    def metrics(self):
        return DEFAULT_METRICS