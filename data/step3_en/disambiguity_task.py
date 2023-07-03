import re
import string
from nltk.translate.bleu_score import sentence_bleu, SmoothingFunction
from typing import *

import numpy as np


from evaluation import (
    GenerationTask,
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

def get_exact_match(answers1, answers2):
    if type(answers1)==list:
        if len(answers1)==0:
            return 0
        return np.max([get_exact_match(a, answers2) for a in answers1])
    if type(answers2)==list:
        if len(answers2)==0:
            return 0
        return np.max([get_exact_match(answers1, a) for a in answers2])
    return (normalize_answer(answers1) == normalize_answer(answers2))

def get_f1(answers, predictions, is_equal=get_exact_match):
    '''
    :answers: a list of list of strings
    :predictions: a list of strings
    '''
    assert len(answers)>0 and len(predictions)>0, (answers, predictions)
    occupied_answers = [False for _ in answers]
    occupied_predictions = [False for _ in predictions]
    for i, answer in enumerate(answers):
        for j, prediction in enumerate(predictions):
            if occupied_answers[i] or occupied_predictions[j]:
                continue
            em = is_equal(answer, prediction)
            if em:
                occupied_answers[i] = True
                occupied_predictions[j] = True
    assert np.sum(occupied_answers)==np.sum(occupied_predictions)
    a, b = np.mean(occupied_answers), np.mean(occupied_predictions)
    if a+b==0:
        return 0
    return 2*a*b/(a+b)

def _get_edits(tokens1, tokens2):
    allCommon = []
    while True:
        commons = list(set(tokens1) & set(tokens2))
        if len(commons)==0:
            break
        allCommon += commons
        for c in commons:
            ind1, ind2 = tokens1.index(c), tokens2.index(c)
            tokens1 = tokens1[:ind1]+tokens1[ind1+1:]
            tokens2 = tokens2[:ind2]+tokens2[ind2+1:]
    deleted = ["[DELETED]"+token for token in tokens1]
    added = ["[ADDED]"+token for token in tokens2]
    common = ["[FIXED]"+token for token in allCommon]
    return deleted+added #+common

def get_edits_f1(generated, promptQuestion, references):
    generated = generated.split(" ")
    promptQuestion = promptQuestion.split(" ")
    prediction = _get_edits(promptQuestion, generated)
    edit_f1 = 0
    for _question in references:
        _question = _question.split(" ")
        reference = _get_edits(promptQuestion, _question)
        # now compare the reference edits and predicted edits
        if len(reference)==len(prediction)==0:
            # rarely, reference has no edits after normalization
            # then, if the prediction also has no edits, it gets full score
            edit_f1 = 1
        elif len(reference)==0 or len(prediction)==0:
            # if only one of them has no edits, zero score
            edit_f1 = max(edit_f1, 0)
        else:
            # otherwise, compute F1 score between prediction and reference
            edit_f1 = max(edit_f1, get_f1(prediction, reference, is_equal=lambda x, y: x==y))
    return edit_f1


def get_context(text):
    pattern = r"(?<=\nContext:).*(?=\n)"
    matches = re.findall(pattern, text)
    if matches:
        last_match = matches[-1]
        return last_match
    else:
        print("error in making ambiguityQA input")
        return "no match"



class disambiguityQA(GenerationTask):
    @property
    def metrics(self) -> Dict[str, Callable]:
        return {"EDIT_F1": self.edit_f1}

    def edit_f1(self, predictions, ground_truths):
        edit_f1 = []
        for prediction, ground_truth in zip(predictions, ground_truths):
            prediction = normalize_answer(prediction)
            context = normalize_answer(get_context(ground_truth[0]["text"]))
            ground_truths = []
            for turth in ground_truth[0]["targets"]:
                ground_truths.append(normalize_answer(turth))
            edit_f1.append(get_edits_f1(prediction,context,ground_truths))
        edit_f1_score = np.mean(edit_f1)
        # 返回值可以是一个数，则该metric名称选用def metrics(self)中指定的名称
        # 也可以是一个字典，{key:float}形式返回多个子metrics
        return edit_f1_score

    