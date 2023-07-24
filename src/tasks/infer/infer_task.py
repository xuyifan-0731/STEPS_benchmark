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
from src.tasks.single_round_tasks.singleround_task import SingleRoundTask

class InferTask(SingleRoundTask):
    def evaluate(self, agent: Agent):
        start = time.time()
        print_rank_0("\n")
        print_rank_0(f"{self.config}")
        print_rank_0(f"Inferring task {self.config.name}:")

        for group_name, filelist in self.file_groups.items():
            print_rank_0(f"    Inferring group {group_name}:")
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
                        data["prediction"] = result

                if self.config.save_prediction:  # first save and evaluate
                    self.save_prediction_to_file(file, dataset.data, agent.name)