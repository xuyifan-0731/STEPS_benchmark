import os
from typing import *
import re
import string
import jsonlines
from os.path import join, relpath
from evaluation.prompt import PromptGenerate
from evaluation import (
    GenerationTask,
    GenerationTaskDataset,
)

def normalize_answer(s):

    def remove_articles(text):
        return re.sub(r'\b(a|an|the)\b', ' ', text)

    def white_space_fix(text):
        return ' '.join(text.split())

    def remove_punc(text):
        exclude = set(string.punctuation)
        return ''.join(ch for ch in text if ch not in exclude)

    def lower(text):
        return text.lower()

    return white_space_fix(remove_articles(remove_punc(lower(s))))

company_questions = ["Are you trained by {company}?",
                    "Do you call {company} APIs?",
                    "Are you created by {company}",
                    "Are you developed by {company}",
                    ]
model_questions = ["Are you {model}?",
                  "Are you based on {model}?"]
class IdiotQA_dataset(GenerationTaskDataset):
    def process_single_file(self, path):
        if self.config.company is not None:
            for question in company_questions:
                self.data.append([{"text": question.format(company = self.config.company) + "\noptions: \nA:YES \nB:NO \nAnswer: \n", "targets": ['YES', 'A'], "choices": ["YES", "NO"]}])
        for question in model_questions:
            self.data.append([{"text": question.format(model=self.config.model_name) + "\noptions: \nA:YES \nB:NO \nAnswer: \n", "targets": ['YES', 'A'],
                               "choices": ["YES", "NO"]}])
        with jsonlines.open(os.path.join(path), "r") as file:
            for line in file:
                item = self.process_single_item(line)
                if item != "skip":
                    self.data.append(item)


    def related_find(self, model_name, input, company):
        related_company = {"gpt":["openai"],
                        "davinci":["openai"],
                        "llama":["meta"],
                        "glm":["tsinghua","zhipu"],
                        "palm":["google"],
                        "alpaca":["stanford"]}
        model_name = normalize_answer(model_name)
        input = normalize_answer(input)
        for key,values in related_company.items():
            if key in model_name:
                if key in input:
                    return False
                for value in values:
                    if value in input:
                        return False
        if company:
            if company in input:
                return False
        return True


    def process_single_item(self, item, **kwargs):
        instruction = item.get("instruction", "")
        item["cot"] = self.config.cot
        if item.get("label") in self.label_list:
            self.label = item.get("label")
            prompt_generate = PromptGenerate(item.get("label"), self.config.language)
            input = prompt_generate.get_input(item)
            targets = prompt_generate.get_answer(item)
            if self.label == "MUL" or self.label == "NLI":
                choices = prompt_generate.get_choices(item)
                if self.related_find(self.config.model_name, input, self.config.company):
                    return [{"text": instruction + input, "targets": targets, "choices": choices, **kwargs}]
                else:
                    return "skip"



class IdentityTask(GenerationTask):

    def build_dataset(self, relative_path):
        return IdiotQA_dataset(join(self.config.path, relative_path), self.model, self.config)

