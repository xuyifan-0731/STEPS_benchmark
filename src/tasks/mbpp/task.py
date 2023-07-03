import os
from typing import Union, List, Tuple, Dict, Callable
from copy import deepcopy

from src.agent import Session
from src.task import Task, Dataset, Session, DataPiece

from .utils import stream_jsonl
from .evaluator.evaluate import evaluate_functional_correctness

class MBPPTask(Task[str, str, Dict]):
    @property
    def metrics(self) -> Dict[str, Callable[[List[str], List[Dict]], float]]:
        def evaluate(results, targets):
            samples = []
            for result, target in zip(results, targets):
                sample = deepcopy(target)
                sample['generation'] = result
                samples.append(sample)
            return evaluate_functional_correctness(samples, k=[1])['pass@1']
        return {'pass@1': evaluate}

    def __init__(self, name=None, workers=1, num_samples=None, datapath=None, **configs):
        super().__init__(name=name, workers=workers, **configs)
        self.num_samples = num_samples
        self.datapath = datapath

    def get_data(self) -> Dataset[str, Dict]:
        # (
        #     "model_input",
        #     (
        #         "task_id",
        #         "test_setup",
        #         "test_list"
        #     ),
        # )
        prompt_template = "You are an expert Python programmer, and here is your task: {prompt} Your code should pass these tests:\n{tests}\nWrite a response that appropriately completes the task:\n"
        
        dataset = Dataset()
        data = list(stream_jsonl(self.datapath))
        demo = [l for l in data[:10] if l['task_id'] in [2, 3, 4]]
        demo = [(prompt_template.format(prompt=l['text'], tests='\n'.join(l['test_list'])) + l['code']).strip() + '\n\n' for l in demo]
        demo = ''.join(demo)

        # data_test = data[10:510]
        data_test = data[310:410]
        for task in data_test:
            item = DataPiece(
                demo + prompt_template.format(prompt=task['text'], tests='\n'.join(task['test_list'])),
                {
                    "task_id": task['task_id'], 
                    "test_setup": task['test_setup_code'],
                    "test_list": task['test_list'] + task['challenge_test_list']
                },
            )
            for _ in range(self.num_samples):
                dataset.append(item)
        return dataset

    def predict_single(self, session: Session, data_item: str):
        result = session.action({"role": "user", "content": data_item})
        md_pos = result.find('```')
        if md_pos != -1:
            result = result[:md_pos]
        md_pos = result.find('You are an')
        if md_pos != -1:
            result = result[:md_pos]
        return result
