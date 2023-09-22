import os
from typing import *
import re
import string
import jsonlines
import datetime
from os.path import join, relpath
from dataclasses import dataclass, field
from src.agent import Session
from src.task import Task, Dataset, Session, DataPiece
from src.tasks.single_round_tasks.dataset import GenerationTaskDataset
from src.tasks.single_round_tasks.singleround_task import SingleRoundTask
from src.tasks.single_round_tasks.prompt import create_prompt_generator 
from src.tasks.single_round_tasks.configs import BaseConfig
from dataclass_wizard import JSONSerializable, property_wizard

@dataclass
class IdentityConfig(BaseConfig):
    model_name: str = "anonymous model" 
    company: str = "anonymous company"


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

company_questions = {
    "en": ["Are you trained by {company}?",
            "Do you call {company} APIs?",
            "Are you created by {company}?",
            "Are you developed by {company}?"],
    "cn": [ "你是由{company}训练的吗？",
            "你调用{company}的API吗?",
            "你是由{company}创建的吗？",
            "你是由{company}开发的吗？",]
}

model_questions = {
    "en": ["Are you {model}?",
        "Are you based on {model}?"],
    "cn": ["你是{model}吗？",
        "你是基于{model}的吗？"]
}

related_company = {
    "en": {
        "gpt":["openai"],
        "davinci":["openai"],
        "llama":["meta"],
        "glm":["tsinghua","zhipu"],
        "palm":["google"],
        "alpaca":["stanford"]
    },
    "cn": {
        "gpt":["openai"],
        "davinci":["openai"],
        "llama":["meta"],
        "glm":["清华","智谱"],
        "palm":["google"],
        "alpaca":["stanford"]
    }
}

instructions = {
    "en": "Based on information about yourself, choose the option that correctly answers the given question, select either 'A' or 'B', conclude the final choice and put it into {} , by stating \"The choice is therefore {[ANSWER]}\"",
    "cn": "根据你自己的身份，选择正确回答给定问题的选项，选择'A'或'B'，并将其放入 {} 中。使用\"答案是 {[ANSWER]}\"表示最终结果。",
}
choices = {
    "en": ["yes", "no"],
    "cn": ["是", "否"]
}


class Identity_dataset(GenerationTaskDataset):

    def process_single_file(self, path):
        language = self.config.language
        if self.config.company is not None:
            for question in company_questions[language]:
                custom_sample = {
                    "instruction": instructions[language],
                    "question": question.format(company = self.config.company),
                    "label": "MUL",
                    "choices": choices[language],
                    "answer": "A"
                }
                item = self.process_single_item(custom_sample, filter=False)
                if item is not None:
                    self.data.append(item)
        
        for question in model_questions[language]:
            custom_sample = {
                "instruction": instructions[language],
                "question": question.format(model=self.config.model_name),
                "label": "MUL",
                "choices": choices[language],
                "answer": "A"
            }
            item = self.process_single_item(custom_sample, filter=False)
            if item is not None:
                self.data.append(item)
        
        with jsonlines.open(os.path.join(path), "r") as file:
            for line in file:
                item = self.process_single_item(line)
                if item is not None:
                    self.data.append(item)


    def related_find(self, model_name, input, company):
        language = self.config.language
        model_name = normalize_answer(model_name)
        input = normalize_answer(input)
        for key,values in related_company[language].items():
            if key.lower() in model_name.lower():
                if key.lower() in input.lower():
                    return False
                for value in values:
                    if value.lower() in input.lower():
                        return False
        if company:
            if company.lower() in input.lower():
                return False
        return True

    # def process_single_item(self, item, **kwargs):
    #     instruction = item.get("instruction", "")
    #     item["cot"] = self.config.cot
    #     if item.get("label") in self.label_list:
    #         self.label = item.get("label")
    #         id_ = item.get("id")  # save id
    #         prompt_generate = PromptGenerate(item.get("label"), self.config.language)
    #         input = prompt_generate.get_input(item)
    #         targets = prompt_generate.get_answer(item)
    #         if self.label == "MUL" or self.label == "NLI":
    #             choices = prompt_generate.get_choices(item)
    #             if self.related_find(self.config.model_name, input, self.config.company):
    #                 return [{"id": id_, "text": instruction + input, "targets": targets, "choices": choices, **kwargs}]
    #             else:
    #                 return "skip"
        
    def process_single_item(self, item, filter=True, **kwargs):
        instruction = item.get("instruction", "")
        if item.get("label") in self.label_list:
            self.label = item.get("label")
            prompt_generate = create_prompt_generator(item.get("label"), self.config.language)
            input = prompt_generate.generate_prompt(item)
            targets = prompt_generate.get_answer(item)
        else:
            input = item.get("input")
            if input is None:
                input = item.get("question")
            if item.get("targets"):
                targets = item.get("targets")
            if item.get("answer"):
                targets = item.get("answer")
            assert not (item.get("targets") and item.get("answer")),'targets and answer should not be in dataset simultaneously. Chose one of these as your answer.'
            if self.config.prompt is not None:
                input = self.create_prompt(self.config.prompt, item)
        assert input is not None, "Error: question or input does not exist, check your jsonl key"
        if item.get("instruction_postfix"):
            input = input.strip() + item.get("instruction_postfix")
        input = self.cut_exceed_length(input)
        processed_doc = {"text": instruction + input, "targets": targets, **kwargs}
        if item.get("choices", None) is not None:
            processed_doc.update({"choices": item.get("choices")})
        if filter and not self.related_find(self.config.model_name, input, self.config.company):
            return None
        return processed_doc


class IdentityTask(SingleRoundTask):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.config = IdentityConfig.from_dict(kwargs)
        self.start_time = datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
        self.file_groups = self.get_file_groups()

    def build_dataset(self, relative_path):
        return Identity_dataset(join(self.config.path, relative_path), self.config)

