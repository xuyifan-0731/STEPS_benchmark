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

from src import YAMLConfig, print_rank_0, Task, Agent


def parse_args():
    parser = argparse.ArgumentParser(add_help=False)
    group = parser.add_argument_group("evaluation", "Evaluation configurations")
    group.add_argument("--task", nargs="+", required=True, help="All task config(s) to load")
    group.add_argument("--agent", type=str, required=True, help="Agent config to load")
    args = parser.parse_args()
    return args


def find_all_task_files(all_task_config_path):
    print(type(all_task_config_path), all_task_config_path)
    tasks = []
    for task in all_task_config_path:
        if isdir(task):
            tasks += [relpath(path, ".") for path in glob(join(task, "**/*.yaml"), recursive=True)]
        elif isfile(task):
            tasks.append(task)
        else:
            print(f"'{task}' is not a valid file or directory, ignored.")
    return tasks


def evaluate_all_tasks(tasks: List[Task], agent: Agent):
    for task in tasks:
        task.evaluate(agent)


def main():
    args = parse_args()

    task_files = find_all_task_files(args.task)
    tasks = []

    print("> Loading task configs")
    for task_config_path in task_files:
        task = YAMLConfig.create_from_yaml(task_config_path)
        print(f"    Task '{task.name}' loaded from config {task_config_path}")
        tasks.append(task)
    print(f"> Successfully load {len(tasks)} task{'s' if len(tasks) > 1 else ''}")

    agent = YAMLConfig.create_from_yaml(args.agent)
    # model, tokenizer = initialize_model_and_tokenizer(args)
    # model = ModelForEvaluation(model, args.position_encoding_2d)

    start = time.time()
    evaluate_all_tasks(tasks, agent)
    print_rank_0(f"Finish {len(tasks)} task{'s' if len(tasks) > 1 else ''} in {time.time() - start:.1f}s")


if __name__ == "__main__":
    main()
