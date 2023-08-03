import os
import json
import jsonlines
import time
from glob import glob
from os.path import join, relpath
from collections import defaultdict
from typing import Any, Dict, Tuple
import numpy as np
import datetime

from src.task import Task, Session
from src.tasks.single_round_tasks.configs import BaseConfig
from src.utils import print_rank_0, JsonEncoder
from src.agent import Agent, Session
from src.tasks.single_round_tasks.dataset import GenerationTaskDataset
from src.tasks.single_round_tasks.metrics import DEFAULT_METRICS


class SingleRoundTask(Task[str, str, str]):
    def __init__(self, **kwargs):
        self.config = BaseConfig.from_dict(kwargs)
        self.start_time = datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
        super().__init__(**kwargs)
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
                inputs = [piece["text"] for piece in dataset]
                raw_results = self.predict_all(agent, inputs)

                # first stage: get model predictions
                for data, raw_result in zip(dataset.data, raw_results):
                    data["raw_answer"] = raw_result
                    data["prediction"] = raw_result

                # second stage: extract answer
                if self.config.extract_answer == True:
                    extract_inputs = [dataset.construct_extract_prompt(item) for item in dataset]
                    results = self.predict_all(agent, extract_inputs)
                    for data, result in zip(dataset.data, results):
                        if data["raw_answer"].strip()[0] in ["A","B","C","D"]:
                            data["prediction"] = data["raw_answer"].strip()[0]
                        else:
                            data["prediction"] = result

                if self.config.save_prediction:  # first save and evaluate
                    self.save_prediction_to_file(file, dataset.data, agent.name)

                try:
                    # evaluation
                    result_dict = {}
                    predictions = [dat["prediction"] for dat in dataset.data]
                    for key, metric in self.metrics.items():
                        metric_result = metric(predictions, dataset.data, self.config)
                        if isinstance(metric_result, dict):
                            for sub_key, sub_metric in metric_result.items():
                                result_dict[sub_key] = sub_metric
                        else:
                            result_dict[key] = metric_result

                    if self.config.save_evaluation:
                        result_dict["length"] = len(dataset)
                        self.save_evaluation_to_file(file, result_dict, agent.name)

                    result_dict["length"] = len(dataset)
                    result_dict_group[file] = result_dict

                    self.report_single_metrics(file, result_dict)
                except Exception as e:
                    print(f"error in evaluation {file} : {e}")
                    result_dict = {}
                    result_dict["error"] = f"error in evaluation {file} : {e}"
                    if self.config.save_evaluation:
                        self.save_evaluation_to_file(file, result_dict, agent.name)

            result_dict_all[group_name] = result_dict_group

        print_rank_0(f"Evaluation results of task {self.config.name}:")

        cal_results = {"groups": {}}
        for group_name, result_dict_group in result_dict_all.items():
            group_metrics = self.report_group_metrics(group_name, result_dict_group)
            cal_results["groups"][group_name] = group_metrics

        overall_metrics = self.report_overall_metrics(result_dict_all)
        cal_results["overall"] = overall_metrics
        self.save_overall_results(result_dict_all, cal_results, agent.name)

        print_rank_0(f"Finish task {self.config.name} in {time.time() - start:.1f}s.")

        # change cal_results into a json object (only containing basic types, list, or dict, with no numpy types)
        return json.loads(json.dumps(cal_results, cls=JsonEncoder))

    def build_dataset(self, relative_path):
        return GenerationTaskDataset(os.path.join(self.config.path, relative_path), self.config)

    def save_prediction_to_file(self, file, data, agent_name):
        file = ".".join(file.split(".")[:-1])
        filename = os.path.join(self.get_output_dir(), agent_name, "prediction", f"{agent_name}.{file}.predict.jsonl")
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        with open(filename, "w") as file:
            for output_data in data:
                json.dump(output_data, file, ensure_ascii=False)
                file.write('\n')

    def save_evaluation_to_file(self, file, res_dict, agent_name):
        file = ".".join(file.split(".")[:-1])
        filename = os.path.join(self.get_output_dir(), agent_name, "evaluation", f"{agent_name}.{file}.evaluate.json")
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        with open(filename, "w", encoding="utf-8") as f:
            f.write(json.dumps(res_dict, indent=2))
            f.close()

    def save_overall_results(self, result_dict_all, cal_results, agent_name):
        results_all = {"calculate": cal_results, "results": result_dict_all}
        filename = os.path.join(self.get_output_dir(), agent_name, "results.json")
        with open(filename, "w", encoding="utf-8") as f:
            f.write(json.dumps(results_all, cls=JsonEncoder, indent=2))
            f.close()

    def report_single_metrics(self, file: str, result_dict: Dict[str, float]):
        output_str = f"        Finish {file}"
        for key, value in result_dict.items():
            output_str += f", {key} = {value:.3f}"
        print_rank_0(output_str)

    @staticmethod
    def calc_group_metrics(result_dict_group: Dict[str, Dict[str, Any]]):
        metrics_dict = defaultdict(lambda: [])
        weight = []
        for file, result_dict in result_dict_group.items():
            for key, value in result_dict.items():
                metrics_dict[key].append(value)
            weight.append(result_dict["length"])
        return {
            name: {
                "max": np.max(value),
                "median": np.median(value),
                "fine_grained_average": np.average(value, weights=weight),
                "coarse_grained_average": np.average(value)
            }
            for name, value in metrics_dict.items()
        }

    def report_group_metrics(self, group_name, result_dict_group: Dict[str, Dict[str, Any]], level=1):
        stats_dict = self.calc_group_metrics(result_dict_group)
        if len(stats_dict) == 1:
            name, stats = next(iter(stats_dict.items()))
            print_rank_0(
                "    " * level + f"Group {group_name} {name}: max = {stats['max']:.3f}, "
                f"median = {stats['median']:.3f}, fine_grained_average = {stats['fine_grained_average']:.3f}, "
                f"coarse_grained_average = {stats['coarse_grained_average']:.3f}"
            )
        else:
            print_rank_0("    " * level + f"  Group {group_name}: ")
            for name, stats in stats_dict.items():
                print(
                    "    " * (level + 1) + f"Group {group_name} {name}: max = {stats['max']:.3f}, "
                    f"median = {stats['median']:.3f}, fine_grained_average = {stats['fine_grained_average']:.3f}, "
                    f"coarse_grained_average = {stats['coarse_grained_average']:.3f}"
                )
        return stats_dict

    @staticmethod
    def calc_overall_metrics(result_dict_all: Dict[str, Dict[str, Dict[str, Any]]]):
        metrics_dict = defaultdict(lambda: [])
        weight = []
        for group_name, result_dict_group in result_dict_all.items():
            for file, result_dict in result_dict_group.items():
                for key, value in result_dict.items():
                    metrics_dict[key].append(value)
                weight.append(result_dict["length"])
        return {
            name: {
                "max": np.max(value),
                "median": np.median(value),
                "fine_grained_average": np.average(value, weights=weight),
                "coarse_grained_average": np.average(value)
            }
            for name, value in metrics_dict.items()
        }

    def report_overall_metrics(self, result_dict_all: Dict[str, Tuple[Dict[str, float], int]]):
        stats_dict = self.calc_overall_metrics(result_dict_all)
        for name, stats in stats_dict.items():
            print_rank_0(
                f"Overall {name} : max = {stats['max']:.3f}, "
                f"median = {stats['median']:.3f}, fine_grained_average = {stats['fine_grained_average']:.3f}, "
                f"coarse_grained_average = {stats['coarse_grained_average']:.3f}"
            )
        return stats_dict

    def predict_single(self, session: Session, data_item: str) -> str:
        return session.action({"role": "user", "content": data_item})

    @property
    def metrics(self):
        return DEFAULT_METRICS
