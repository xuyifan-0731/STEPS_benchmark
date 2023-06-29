import os
from typing import *
from os.path import join, relpath
import numpy as np
import re
import string
from nltk.translate.bleu_score import sentence_bleu, SmoothingFunction
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

def word_bleu_score(reference, candidate):
    reference_tokens = list(reference)
    candidate_tokens = list(candidate)

    smoothie = SmoothingFunction().method4
    score = sentence_bleu([reference_tokens], candidate_tokens, smoothing_function=smoothie)
    return score

class IdiotQA_dataset(GenerationTaskDataset):
    def process_single_item(self, item, **kwargs):
        instruction = item.get("instruction", "")
        question = item.get("question")
        targets = item.get("golden_reply")
        good_replies = item.get("good_replies")
        bad_replies = item.get("bad_replies")
        input = self.cut_exceed_length(instruction + question)
        return [{"text": input, "targets": targets, "good-replies":good_replies, "bad-replies":bad_replies}]



class IdiotQATask(GenerationTask):
    @property
    def metrics(self) -> Dict[str, Callable]:
        return {"truthfulQA_metric": self.IdiotQA_metric}

    def build_dataset(self, relative_path):
        return IdiotQA_dataset(join(self.config.path, relative_path), self.model, self.config)

    def IdiotQA_metric(self, predictions, ground_truths):
        overlap_metric = []
        acc = []
        for prediction, ground_truth in zip(predictions, ground_truths):
            prediction = normalize_answer(prediction)
            golden_answer = normalize_answer(ground_truth[0]["targets"])
            overlap_metric.append(word_bleu_score(prediction,golden_answer))
            max = 0
            is_acc = 0
            for choose in ground_truth[0]["good-replies"]:
                if choose == None:
                    continue
                if word_bleu_score(normalize_answer(choose),prediction) > max:
                    max = word_bleu_score(normalize_answer(choose),prediction)
                    is_acc = 1
            for choose in ground_truth[0]["bad-replies"]:
                if choose == None:
                    continue
                if word_bleu_score(normalize_answer(choose),prediction) > max:
                    max = word_bleu_score(normalize_answer(choose),prediction)
                    is_acc = 0
            acc.append(is_acc)
        acc = np.mean(acc)
        overlap_metric = np.mean(overlap_metric)
        # 返回值可以是一个数，则该metric名称选用def metrics(self)中指定的名称
        # 也可以是一个字典，{key:float}形式返回多个子metrics
        return {"acc":acc,"bleu":overlap_metric}
