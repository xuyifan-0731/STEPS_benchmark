import os
import json
import numpy as np
from typing import *
from collections import defaultdict

from evaluation import (
    GenerationTask,
)

def calculate_variance(lst):
    n = len(lst)
    if n < 2:
        return 0

    mean = sum(lst) / n
    variance = sum((x - mean) ** 2 for x in lst) / (n - 1)
    return variance

class RobustnessTask(GenerationTask):
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
                "var": calculate_variance(value)
            }
            for name, value in metrics_dict.items()
        }

    def report_group_metrics(self, group_name, result_dict_group: Dict[str, Tuple[Dict[str, float], int]], level=1):
        stats_dict = self.calc_group_metrics(result_dict_group)
        if len(stats_dict) == 1:
            name, stats = next(iter(stats_dict.items()))
            print(
                "    " * level + f"Group {group_name} {name}: max = {stats['max']:.3f}, "
                f"median = {stats['median']:.3f}, average = {stats['average']:.3f}"
            )
        else:
            print("    " * level + f"  Group {group_name}: ")
            for name, stats in stats_dict.items():
                print(
                    "    " * (level + 1) + f"Metric {name}: max = {stats['max']:.3f}, "
                    f"median = {stats['median']:.3f}, average = {stats['average']:.3f}"
                )
        import pdb
        pdb.set_trace()
        print(1)
        output = {}
        for metric_name,values in stats_dict.items():
            output[f"{metric_name}_average"] = values["average"]
            output[f"{metric_name}_variance"] = values["var"]
        filename = os.path.join("outputs", self.config.name, self.model_name, "evaluation",
                                f"{self.model_name}.{group_name}.evaluate.json")
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        print(filename)
        with open(filename, "w", encoding="utf-8") as f:
            f.write(json.dumps(output, indent=2))
            f.close()

    def report_overall_metrics(self, result_dict_all: Dict[str, Tuple[Dict[str, float], int]]):
        metric_result = defaultdict(list)
        all_result = dict()
        for filename, metrics in result_dict_all.items():
            metrics = metrics[0]
            for metric, result in metrics.items():
                metric_result[metric].append(result)
        for metric_name, results in metric_result.items():
            if len(results) > 0:
                mean = sum(results)/len(results)
            else:
                mean = 0
            var = calculate_variance(results)
            all_result[f"{metric_name}_average"] = mean
            all_result[f"{metric_name}_variance"] = var

        output_str = f"        Finish robustness"
        for key, value in all_result.items():
            output_str += f", {key} = {value:.3f}"
        print(output_str)
        import pdb
        pdb.set_trace()
        filename = os.path.join("outputs", self.config.name, self.model_name, "evaluation",
                     f"{self.model_name}.robustness_result.evaluate.json")
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        print(filename)
        with open(filename, "w", encoding="utf-8") as f:
            f.write(json.dumps(all_result, indent=2))
            f.close()







