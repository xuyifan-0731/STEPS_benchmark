import os
import re
import jsonlines
import random
import torch

from typing import List, Union
from abc import ABC, abstractmethod

from .configs import BaseConfig, GenerationTaskConfig
from .prompt import create_prompt_generator

from copy import deepcopy

class EvaluationDataset(torch.utils.data.Dataset, ABC):
    """
    Jsonlines of {
        "text": context
        "choices": [choice_id1,...], if not None, len(target) == 1
        "label": If generation task -1, else [0, len(choices))
    }
    If [MASK] not in context, will append [MASK] after text
    """

    def __init__(self, path: Union[str, List[str]], model, **config):
        self.path = path if isinstance(path, list) else [path]
        self.model = model
        self.config = config
        self.label_list = ["SUM","QA","MUL","NLI"]
        self.label = None

        self.data = []
        for p in self.path:
            self.process_single_file(p)
            
        if self.config.shot > 0:
            self.few_shot(self.config.shot)

    @property
    def has_collate_fn(self) -> bool:
        return False

    def collate_fn(self, samples):
        return None
    
    def few_shot(self, shots):
        assert shots < self.__len__(), "number of shots should lower than size of your dataset"
        tmp_data = []
        for data in self.data:
            tmp = deepcopy(data) # sample everytime so can't modify self.data
            examples = random.sample(self.data, self.config.shot)
            prompt = data[0]["text"]
            for example in examples:
                prompt = example[0]["text"] + "\n" + example[0]["targets"][0] + "\n" + prompt
                prompt = self.cut_exceed_length(prompt)
            tmp[0]["text"] = prompt
            tmp_data.append(tmp)
        self.data = tmp_data
            
    def process_single_file(self, path):
        with jsonlines.open(os.path.join(path), "r") as file:
            for line in file:
                self.data.append(self.process_single_item(line))
            
                
    @abstractmethod
    def process_single_item(self, item, **kwargs) -> List[dict]:
        pass
    
    def cut_exceed_length(self, text):
        if self.config.language == "en":
            if len(text.split(" ")) > self.config.max_length:
                length = len(text.split(" "))
                text = " ".join(text.split(" ")[length - self.config.max_length: ])
        elif self.config.language == "cn" or self.config.language == "zh":
            if len(text) > self.config.max_length:
                text = text[len(text) - self.config.max_length: ]
        return text

    def __len__(self):
        return len(self.data)


class GenerationTaskDataset(EvaluationDataset):
    config: GenerationTaskConfig
    def create_prompt(self, template: str, values: dict) -> str:
        keys = re.findall(r"{(.*?)}", template)
        for key in keys:
            if key in values:
                template = template.replace("{" + key + "}", str(values[key]))
        return template

    def process_single_item(self, item, **kwargs):
        instruction = item.get("instruction", "")
        item["cot"] = self.config.cot
        if item.get("label") in self.label_list:
            self.label = item.get("label")
            id_ = item.get("id") # save id
            prompt_generate = create_prompt_generator(item.get("label"), self.config.language)
            input = prompt_generate.generate_prompt(item)
            targets = prompt_generate.get_answer(item)
            if self.label == "MUL" or self.label == "NLI":
                choices = prompt_generate.get_choices(item)
                return [{"id": id_, "text": instruction + input, "targets": targets, "choices":choices, **kwargs}]
        else:
            input = item.get("input")
            if item.get("targets"):
                targets = item.get("targets")
            if item.get("answer"):
                targets = item.get("answer")
            assert not (item.get("targets") and item.get("answer")),'targets and answer should not be in dataset simultaneously. Chose one of these as your answer.'
            if self.config.prompt is not None:
                input = self.create_prompt(self.config.prompt, item)
            cot = item.get("cot", None)
            if cot == "default":
                input += self.prompt_template.math_cot_prompt[self.language]
            elif cot:
                input += cot
        assert input is not None, "Error: question or input does not exist, check your jsonl key"
        input = self.cut_exceed_length(input)
        return [{"text": instruction + input, "targets": targets, **kwargs}]

    @property
    def has_collate_fn(self) -> bool:
        return False

    def __getitem__(self, idx):
        item = self.data[idx]
        return item
