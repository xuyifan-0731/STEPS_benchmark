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


class PromptTemplate:
    def __init__(self, language):
        self.language = language

    def background_prompt(self, background):
        raise NotImplementedError

    def question_prompt(self, question):
        raise NotImplementedError

    def before_choice_prompt(self):
        raise NotImplementedError

    def choice_prompt(self, label, choice):
        raise NotImplementedError

    def after_choice_prompt(self):
        raise NotImplementedError


class EnglishPromptTemplate(PromptTemplate):
    def __init__(self):
        super().__init__("en")

    def background_prompt(self, background):
        return f"Please answer the questions based on the following information: {background} \n"

    def question_prompt(self, question):
        return f"Question:{question} \n"

    def before_choice_prompt(self):
        return "options: \n"

    def choice_prompt(self, label, choice):
        return f"{label}:{choice} \n"

    def after_choice_prompt(self):
        return "Answer: \n"

    def sum_instruction(self, question):
        return f"Article: {question} \n"

    def sum_instruction_before_article(self):
        return "TL;DR: \n"

    def mul_extract_prompt(self, question, answer, len):
        start_choice = "A"
        end_choice = chr(65+(len-1)%26)
        return f"Question: {question} \nAnswer: {answer} \nAmong {start_choice} to {end_choice}, the answer is "

    def qa_extract_prompt(self, question, answer):
        return f"Question: {question} \nAnswer: {answer} \nTherefore, the answer is "


class ChinesePromptTemplate(PromptTemplate):
    def __init__(self):
        super().__init__("cn")

    def background_prompt(self, background):
        return f"请根据以下信息回答问题：{background} \n"

    def question_prompt(self, question):
        return f"问题:{question} \n"

    def before_choice_prompt(self):
        return "选项： \n"

    def choice_prompt(self, label, choice):
        return f"{label}:{choice} \n"

    def after_choice_prompt(self):
        return "回答：\n"

    def sum_instruction(self, question):
        return f"文章: {question} \n"

    def sum_instruction_before_article(self):
        return "请总结以上文章的内容： \n"
    
    def mul_extract_prompt(self, question, answer, len):
        start_choice = "A"
        end_choice = chr(65+(len-1)%26)
        return f"问题：{question}\n回答： {answer}\n在 {start_choice} 到 {end_choice} 这几个选项中，正确答案是"

    def qa_extract_prompt(self, question, answer):
        return f"问题：{question}\n回答： {answer}\n因此，正确答案是"



class PromptGenerate:
    def __init__(self, prompt_label, prompt_template):
        self.prompt_label = prompt_label
        self.prompt_template = prompt_template

    def generate_prompt(self, item):
        raise NotImplementedError

    def get_background(self, item):
        background = item.get("background")
        if background:
            return self.prompt_template.background_prompt(background)
        return ""

    def get_question(self, item):
        question = item.get("question")
        assert question is not None, "Question missing"
        return self.prompt_template.question_prompt(question)

    def get_choices(self, item):
        choices = item.get("choices")
        if choices is not None:
            choice_list = self.prompt_template.before_choice_prompt()
            for idx, choice in enumerate(choices):
                choice_list += self.prompt_template.choice_prompt(number_to_uppercase_word(idx), choice)
            return choice_list
        return ""

    def get_answer(self, item):
        answer = item.get("answer")
        assert answer is not None, "Answer missing"
        return answer

    def combine_prompt(self, background, question, choices):
        return f"{background}{question}{choices}{self.prompt_template.after_choice_prompt()}"

class QAPromptGenerate(PromptGenerate):
    def __init__(self, prompt_template):
        super().__init__("QA", prompt_template)

    def generate_prompt(self, item):
        background = self.get_background(item)
        question = self.get_question(item)
        prompt = self.combine_prompt(background, question, "")
        return prompt

class SUMPromptGenerate(PromptGenerate):
    def __init__(self, prompt_template):
        super().__init__("SUM", prompt_template)

    def generate_prompt(self, item):
        assert item.get("question") is not None, "question missing"
        question = item.get("question")
        prompt = ""

        if item.get("background"):
            background = item.get("background")
            prompt += self.prompt_template.background_prompt(background)

        # Process the SUM type of prompts
        prompt += self.prompt_template.sum_instruction(question)
        prompt += self.prompt_template.sum_instruction_before_article()

        return prompt



class MULPromptGenerate(PromptGenerate):
    def __init__(self, prompt_template):
        super().__init__("MUL", prompt_template)

    def generate_prompt(self, item):
        background = self.get_background(item)
        question = self.get_question(item)
        choices = self.get_choices(item)
        assert choices != "", "Choices missing"
        prompt = self.combine_prompt(background, question, choices)
        return prompt

    def get_answer(self, item):
        answer = super().get_answer(item)
        if isinstance(answer, int):
            if answer < 0:
                answer = len(item.get("choices")) + answer
            return [item.get("choices")[answer], number_to_uppercase_word(answer)]
        if isinstance(answer, str):
            assert answer in item.get("choices"), "The answer should be one of the choices"
            return [answer, number_to_uppercase_word(item.get("choices").index(answer))]
        if isinstance(answer, list):
            answer_list = []
            for answer_int in answer:
                if isinstance(answer_int, str):
                    answer_list.append(answer_int)
                else:
                    if answer_int < 0:
                        answer_int = len(item.get("choices")) + answer_int
                    answer_list.append(item.get("choices")[answer_int])
                    answer_list.append(number_to_uppercase_word(answer_int))
            return answer_list

class NLIPromptGenerate(PromptGenerate):
    def __init__(self, prompt_template):
        super().__init__("NLI", prompt_template)

    # Implement the specific prompt generation for NLI
    # ...

class ExtractGenerate(PromptGenerate):
    def __init__(self, prompt_template):
        super().__init__("EXT", prompt_template)

    def generate_prompt(self, item):
        question = item.get("text", None)
        answer = item.get("raw_answer", None)
        assert(question is not None)
        assert(answer is not None)
        choices = item.get("choices", None)
        if choices is None:
            return self.prompt_template.qa_extract_prompt(question, answer)
        else:
            return self.prompt_template.mul_extract_prompt(question, answer, len(choices))
        

def create_prompt_generator(prompt_label, language):
    # Map the language to corresponding PromptTemplate
    language_template_map = {
        "en": EnglishPromptTemplate,
        "cn": ChinesePromptTemplate
    }

    # Map the prompt_label to corresponding PromptGenerate subclass
    prompt_label_map = {
        "QA": QAPromptGenerate,
        "SUM": SUMPromptGenerate,
        "MUL": MULPromptGenerate,
        "NLI": MULPromptGenerate,
        "EXT": ExtractGenerate,
    }

    assert language in language_template_map, "Unsupported language"
    assert prompt_label in prompt_label_map, "Unsupported prompt label"

    prompt_template_class = language_template_map[language]
    prompt_generate_class = prompt_label_map[prompt_label]

    prompt_template = prompt_template_class()
    prompt_generate = prompt_generate_class(prompt_template)

    return prompt_generate
'''

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
                
'''

