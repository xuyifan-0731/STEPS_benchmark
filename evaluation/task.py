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
from concurrent.futures import ThreadPoolExecutor

from typing import Dict, Callable, Type, Tuple, List, Any
from abc import ABC, abstractmethod
from glob import glob
from os.path import join, relpath
from collections import defaultdict

from .configs import BaseConfig, GenerationTaskConfig, LanguageModelTaskConfig, MultiChoiceTaskConfig
from .dataset import EvaluationDataset, GenerationTaskDataset
from .utils import print_rank_0
from .metrics import DEFAULT_METRICS
# from .model_api import get_model_api
from .agent import Agent, Session


class BaseTask(ABC):
    config: BaseConfig
    file_groups: Dict[str, List[str]]

    @classmethod
    def config_class(cls) -> Type[BaseConfig]:
        return BaseConfig

    @property
    def metrics(self) -> Dict[str, Callable]:
        return {metric: DEFAULT_METRICS[metric] for metric in self.config.metrics}

    def __init__(self, model, tokenizer, config: BaseConfig):
        self.model_name = model
        self.model = get_model_api(model, config.workers)
        self.tokenizer = []
        self.config = config
        self.config.model_name = self.model_name
        self.config.metrics = list(self.metrics.keys())

        self.file_groups = self.get_file_groups()
        self.save_prediction = config.save_prediction
        self.save_evaluation = config.save_evaluation

    def save_prediction_to_file(self, file, prediction, data):
        pass

    def save_evaluation_to_file(self, res_dict):
        pass

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



    def evaluate(self):
        agent = self.get_agent()
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
                prediction = self.predict_all(dataset, agent)

                if self.save_prediction:  # first save and evaluate
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

                    if self.save_evaluation:
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
        self.report_overall_metrics(
            {k: v for result_dict_group in result_dict_all.values() for k, v in result_dict_group.items()},
        )

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

    def report_overall_metrics(self, result_dict_all: Dict[str, Tuple[Dict[str, float], int]]):
        pass

    @abstractmethod
    def predict_all(self, dataset) -> List[Any]:
        pass

    @abstractmethod
    def predict_single(self, item) -> List[Any]:
        pass

    @abstractmethod
    def build_dataset(self, relative_path: str) -> EvaluationDataset:
        pass

    @abstractmethod
    def get_agent(self):
        pass

class GenerationTask(BaseTask, ABC):
    config: GenerationTaskConfig

    @classmethod
    def config_class(cls):
        return GenerationTaskConfig

    def build_dataset(self, relative_path):
        return GenerationTaskDataset(join(self.config.path, relative_path), self.model, self.config)

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

    def __init__(self, model, tokenizer=[], config=[]):
        super(GenerationTask, self).__init__(model, tokenizer, config)

    def predict_single_batch(self, batch) -> List[List[int]]:
        import pdb
        pdb.set_trace()
        output = self.model.generate_text(batch)
        return output


class SingleRoundTask(GenerationTask, ABC):
    config: GenerationTaskConfig

    def __init__(self, model, tokenizer=[], config=[]):
        super(GenerationTask, self).__init__(model, tokenizer, config)

    def get_result_with_retry(self, prompt, session, retries=3, timeout=180):
        for attempt in range(retries):
            result = [None]
            timeout_event = threading.Event()

            def target():
                try:
                    message = {}
                    message["role"] = "user"
                    message["content"] = prompt

                    result[0] = self.get_api_result(prompt)
                except Exception as e:
                    print(f"Error occurred while fetching results for prompt: {e}")
                    result[0] = None
                finally:
                    timeout_event.set()

            worker = threading.Thread(target=target)
            worker.start()

            if not timeout_event.wait(timeout):
                print(f"Timeout occurred while fetching results for prompt (attempt {attempt + 1})")
            else:
                break

        return result[0]

    def predict_single(self, prompt, session):
        return self.get_result_with_retry(prompt, session, self.config.retries, self.config.timeout)

    def predict_all(self, dataset, agent):
        with ThreadPoolExecutor(max_workers=self.config.workers) as executor:
            threads = []
            results = [None] * len(dataset)

            for index, data in tqdm(enumerate(dataset)):
                prompt = data[0]["text"]
                session = agent.create_session()
                future = executor.submit(self.predict_single, prompt, session)
                threads.append((future, index))

            for future, index in threads:
                results[index] = future.result()

        return results

