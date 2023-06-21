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
import yaml
from typing import List, Dict, Any, Optional, Union, Tuple, Callable, Type, TypeVar

import time
import importlib
import argparse

from os.path import join, isdir, isfile, relpath
from glob import glob

from evaluation import BaseConfig, DEFAULT_CLASS, print_rank_0, AgentConfig
"""
TODO
    Load Agent by:
    agent = AgentConfig.create_agent_from_yaml("agents/do_nothing_agent.yaml")

"""


def add_evaluation_specific_args(parser):
    """Arguments for evaluation"""
    group = parser.add_argument_group("evaluation", "Evaluation configurations")

    # Task
    group.add_argument("--task", nargs="+", default=[], help="All task config to evaluation")
    group.add_argument("--model", type=str, default="ChatGPT")
    group.add_argument("--data-path", type=str, required=True, help="Data dir path for all tasks")
    group.add_argument("--save-prediction", action='store_true')
    return parser


def find_all_tasks(all_task_config_path):
    tasks = []
    for task in all_task_config_path:
        if isdir(task):
            tasks += [relpath(path, ".") for path in glob(join(task, "**/*.yaml"), recursive=True)]
        elif isfile(task):
            tasks.append(task)
    return tasks


def evaluate_all_tasks(data_path, model, all_task_config_path, task_classes):
    for config_path, task_class in zip(all_task_config_path, task_classes):
        config = task_class.config_class().from_yaml_file(config_path)
        config.path = join(data_path, config.path)
        task = task_class(model, config=config)
        task.evaluate()


def initialize(extra_args_provider):
    parser = argparse.ArgumentParser(add_help=False)
    extra_args_provider(parser)
    args = parser.parse_args()
    return args


def main():
    args = initialize(extra_args_provider=add_evaluation_specific_args)

    tasks = find_all_tasks(args.task)

    task_classes = []
    print_rank_0("> Loading task configs")

<<<<<<< Updated upstream
    for task_config_path in tasks:
        config = BaseConfig.from_yaml_file(task_config_path)
        if config.module:
            path = ".".join(config.module.split(".")[:-1])
            module = importlib.import_module(path)
            class_name = config.module.split(".")[-1]
            task_class = getattr(module, class_name)
            task_classes.append(task_class)
        else:
            task_classes.append(DEFAULT_CLASS[config.type])
        print_rank_0(f"    Task {config.name} loaded from config {task_config_path}")
    print_rank_0(f"> Successfully load {len(task_classes)} task{'s' if len(task_classes) > 1 else ''}")

    model = args.model
    # model, tokenizer = initialize_model_and_tokenizer(args)
    # model = ModelForEvaluation(model, args.position_encoding_2d)

    start = time.time()
    evaluate_all_tasks(args.data_path, model, tasks, task_classes)
    print_rank_0(f"Finish {len(task_classes)} task{'s' if len(task_classes) > 1 else ''} in {time.time() - start:.1f}s")

=======
    agent = YAMLConfig.create_from_yaml(args.agent)

    start = time.time()
    evaluate_all_tasks(tasks, agent)
    print_rank_0(f"Finish {len(tasks)} task{'s' if len(tasks) > 1 else ''} in {time.time() - start:.1f}s")
>>>>>>> Stashed changes

if __name__ == "__main__":
    main()
