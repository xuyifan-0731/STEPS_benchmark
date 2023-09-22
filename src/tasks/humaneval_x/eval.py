import os
from typing import Union, List, Tuple, Dict, Callable
from copy import deepcopy

from src.agent import Session
from src.task import Task, Dataset, Session, DataPiece

from .utils import cleanup_code, parse_code_from_chat, stream_jsonl, process_extra_prompt
from .evaluator.evaluate import evaluate_functional_correctness, check_samples

map_lang_prefix = {
    'cpp': 'C++:\n',
    'js': 'JavaScript:\n',
    'python': 'Python:\n',
    'java': 'Java:\n',
    'go': 'Go:\n',
}
map_name_prefix = {
    'cpp': 'C++',
    'js': 'JavaScript',
    'python': 'Python',
    'java': 'Java',
    'go': 'Go',
}

def metrics(results, targets) :
    samples = []
    for result, target in zip(results, targets):
        sample = deepcopy(target)
        sample['generation'] = result
        samples.append(sample)
    return evaluate_functional_correctness(samples, k=[1])['pass@1']

def check_valid(results, targets) :
    samples = []
    for result, target in zip(results, targets):
        sample = deepcopy(target)
        sample['generation'] = result
        samples.append(sample)
    return check_samples(samples, k=[1])