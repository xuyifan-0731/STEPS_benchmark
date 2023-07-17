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

from src import YAMLConfig, print_rank_0, Task, Agent, serialize


def parse_args():
    parser = argparse.ArgumentParser(add_help=False)
    group = parser.add_argument_group("evaluation", "Evaluation configurations")
    group.add_argument("--task", nargs="+", required=True, help="All task config(s) to load")
    group.add_argument("--agent", type=str, required=True, help="Agent config to load")
    group.add_argument("--output_dir", type=str, default="outputs", help="Output root directory")
    group.add_argument("--workers", type=int, default=1, help="Number of workers for evaluation")
    args = parser.parse_args()
    return args


def find_all_task_files(all_task_config_path) -> List[str]:
    # print(type(all_task_config_path), all_task_config_path)
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
        task.release()
        del task


def main():
    args = parse_args()
    create_time = datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
    output_root_dir = os.path.join(args.output_dir, create_time)
    if not os.path.exists(output_root_dir):
        os.makedirs(output_root_dir)

    task_files = find_all_task_files(args.task)
    tasks = []

    print("> Loading task configs")
    for task_config_path in task_files:
        task = YAMLConfig.create_from_yaml(task_config_path, {"output_root_dir": output_root_dir, "workers": args.workers})
        if not task.output_root_dir:
            task.output_root_dir = output_root_dir
        # task.workers = args.workers or task.workers
        print(f"    Task '{task.name}' loaded from config {task_config_path}")
        tasks.append(task)
    print(f"> Successfully load {len(tasks)} task{'s' if len(tasks) > 1 else ''}")

    agent = YAMLConfig.create_from_yaml(args.agent)
    # model, tokenizer = initialize_model_and_tokenizer(args)
    # model = ModelForEvaluation(model, args.position_encoding_2d)

    with open(os.path.join(output_root_dir, "configs.json"), "w") as f:
        json.dump({
            "args": args.__dict__,
            "command_line": sys.argv,
            "create_time": create_time,
            "output_root_dir": output_root_dir,
            "tasks": [{
                "class": str(type(task)),
                "fields": serialize(task.__dict__),
            } for task in tasks],
            "agent": {
                "class": str(type(agent)),
                "fields": serialize(agent.__dict__),
            },
        }, f, indent=4)

    start = time.time()
    evaluate_all_tasks(tasks, agent)
    print_rank_0(f"> Finish {len(tasks)} task{'s' if len(tasks) > 1 else ''} in {time.time() - start:.1f}s")


def test():
    output_dir = "outputs"
    workers = 30
    argstask = [r"configs/tasks/full/bbh.yaml"]
    argsagent = r"configs/agents/chatglm2-6b.yaml"
    create_time = datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
    output_root_dir = os.path.join(output_dir, create_time)
    if not os.path.exists(output_root_dir):
        os.makedirs(output_root_dir)

    task_files = find_all_task_files(argstask)
    tasks = []

    print("> Loading task configs")
    for task_config_path in task_files:
        task = YAMLConfig.create_from_yaml(task_config_path, {"output_root_dir": output_root_dir, "workers": workers})
        if not task.output_root_dir:
            task.output_root_dir = output_root_dir
        # task.workers = args.workers or task.workers
        print(f"    Task '{task.name}' loaded from config {task_config_path}")
        tasks.append(task)
    print(f"> Successfully load {len(tasks)} task{'s' if len(tasks) > 1 else ''}")

    agent = YAMLConfig.create_from_yaml(argsagent)
    # model, tokenizer = initialize_model_and_tokenizer(args)
    # model = ModelForEvaluation(model, args.position_encoding_2d)

    with open(os.path.join(output_root_dir, "configs.json"), "w") as f:
        json.dump({
            "command_line": sys.argv,
            "create_time": create_time,
            "output_root_dir": output_root_dir,
            "tasks": [{
                "class": str(type(task)),
                "fields": serialize(task.__dict__),
            } for task in tasks],
            "agent": {
                "class": str(type(agent)),
                "fields": serialize(agent.__dict__),
            },
        }, f, indent=4)

    start = time.time()
    evaluate_all_tasks(tasks, agent)
    print_rank_0(f"> Finish {len(tasks)} task{'s' if len(tasks) > 1 else ''} in {time.time() - start:.1f}s")
    

if __name__ == "__main__":
    test()
