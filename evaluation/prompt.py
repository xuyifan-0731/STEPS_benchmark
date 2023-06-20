from enum import Enum
from typing import AnyStr, Optional, List, Dict
import string

def normalize_answer(s):
    """Lower text and remove punctuation, articles and extra whitespace."""

    def white_space_fix(text):
        return " ".join(text.split())

    def remove_punc(text):
        exclude = set(string.punctuation)
        return "".join(ch for ch in text if ch not in exclude)

    def lower(text):
        return text.lower()

    if isinstance(s,int):
        return s
    return white_space_fix(remove_punc(lower(s)))

def number_to_uppercase_word(number):
    # 0->A 1->B ...
    number = number + 1
    offset = ord('A') - 1
    result = ""
    while number > 0:
        remainder = number % 26
        if remainder == 0:
            result = 'Z' + result
            number = number // 26 - 1
        else:
            letter = chr(offset + remainder)
            result = letter + result
            number = number // 26
    return result

class PromptBase:
    label_dict: Dict = {"0":"A","0":"A"}
    background_prompt: Dict = {"en":"Please answer the questions based on the following information: {background} \n",
                "cn":"请根据以下信息回答问题：{background} \n"}
    question_prompt: Dict = {"en":"Question:{question} \n",
                "cn":"问题:{question} \n"}
    before_choice_prompt: Dict = {"en":"options: \n",
                "cn":"选项： \n"}
    choice_prompt: Dict = {"en":"{label}:{choice} \n",
                "cn":"{label}:{choice} \n"}
    after_choice_prompt: Dict = {"en": "Answer: \n",
                                  "cn": "回答：\n"}
    sum_instruction: Dict = {"en":"Article: {question} \n",
                "cn":"文章:{question} \n"}
    sum_instruction_before_article: Dict = {"en": "TL;DR: \n",
                             "cn": "请总结以上文章的内容： \n"}
    math_cot_prompt: Dict = {
        "en": "let's think step by step",
        "cn": "让我们一步一步地解决这个问题"
    }

    
class PromptGenerate():
    prompt_label: str
    background: str
    question: str
    choices: List[str]
    language: str

    def __init__(self, label, language = "en"):
        self.prompt_label = label
        self.language = language
        assert self.language == "en" or self.language == "cn", "only support en and cn currently"
        self.prompt_template = PromptBase
        
    def get_input(self,item):
        assert item.get("question") != None, "question missing"
        self.question = item.get("question")
        prompt = ""
        if item.get("background"):
            self.background = item.get("background")
            prompt += self.prompt_template.background_prompt[self.language].format(background=self.background)

        if self.prompt_label == "MUL" or self.prompt_label == "NLI":
            prompt = prompt + self.prompt_template.question_prompt[self.language].format(question=self.question)
            assert item.get("choices") != None, "choices missing"
            self.choices = item.get("choices")
            prompt = prompt + self.prompt_template.before_choice_prompt[self.language]
            for idx,choice in enumerate(self.choices):
                prompt = prompt + self.prompt_template.choice_prompt[self.language].format(label = number_to_uppercase_word(idx), choice = choice)
            prompt = prompt +self.prompt_template.after_choice_prompt[self.language]
        if self.prompt_label == "QA":
            prompt = prompt + self.prompt_template.question_prompt[self.language].format(question=self.question)
            prompt = prompt + self.prompt_template.after_choice_prompt[self.language]
        if self.prompt_label == "SUM":
            prompt = prompt + self.prompt_template.sum_instruction[self.language].format(question=self.question)
            prompt = prompt + self.prompt_template.sum_instruction_before_article[self.language]
        cot = item.get("cot", None)
        if cot == "default":
            prompt += self.prompt_template.math_cot_prompt[self.language]
        elif cot:
            prompt += cot
        return prompt

    def get_answer(self,item):
        assert item.get("answer") != None, "answer missing"
        self.answer = item.get("answer")
        if self.prompt_label == "MUL" or self.prompt_label == "NLI":
            if isinstance(self.answer, int):
                if self.answer < 0:
                    self.answer = len(item.get("choices")) + self.answer
                return [item.get("choices")[self.answer],number_to_uppercase_word(self.answer)]
            if isinstance(self.answer, str):
                assert self.answer in item.get("choices"),"the answer should be one of the choices"
                return [self.answer, number_to_uppercase_word(item.get("choices").index(self.answer))]
            if isinstance(self.answer, List):
                answer_list = []
                for answer_int in self.answer:
                    if isinstance(answer_int, str):
                        answer_list.append(answer_int)
                    else:
                        if answer_int < 0:
                            answer_int = len(item.get("choices")) + answer_int
                        answer_list.append(item.get("choices")[answer_int])
                        answer_list.append(number_to_uppercase_word(answer_int))
                return answer_list

        else:
            if isinstance(self.answer, str):
                return [self.answer]
            return self.answer


    def get_choices(self, item):
        if self.prompt_label == "MUL" or self.prompt_label == "NLI":
            assert item.get("choices") != None, "choices missing"
            self.choices = item.get("choices")
            choice_list = []
            for idx, choice in enumerate(self.choices):
                choice_list.append(choice)
            return choice_list
                


