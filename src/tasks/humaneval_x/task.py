import os
from typing import Union, List, Tuple, Dict, Callable
from copy import deepcopy

from src.agent import Session
from src.task import Task, Dataset, Session, DataPiece

from .utils import cleanup_code, parse_code_from_chat, stream_jsonl, process_extra_prompt
from .evaluator.evaluate import evaluate_functional_correctness

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

class HumanEvalXTask(Task[Dict, str, Dict]):
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

    def __init__(self, name=None, workers=1, num_samples=None, datapath=None, **kwargs):
        super().__init__(name=name, workers=workers, **kwargs)
        self.num_samples = num_samples
        self.datapath = datapath

    def get_data(self) -> Dataset[Dict, Dict]:
        # (
        #     { "input", "prompt" }
        #     {
        #         "task_id",
        #         "prompt",
        #         "test"
        #         "declaration"
        #         "import",
        #         "test_setup",
        #     },
        # )
        raise NotImplementedError

class HumanEvalXGenerationTask(HumanEvalXTask):
    def __init__(self, name=None, workers=1, language=None, num_samples=None, datapath=None, **kwargs):
        super().__init__(name, workers, num_samples, datapath, **kwargs)
        self.language = language

    def get_data(self) -> Dataset[Dict, Dict]:
        data = Dataset()
        for task in stream_jsonl(os.path.join(self.datapath, f"{self.language}.jsonl.gz")):
            item = DataPiece(
                { 'input': f"You are an expert {map_name_prefix[self.language]} programmer, and you should complete the following function: \n" + process_extra_prompt(task['prompt'], self.language), 'prompt': task['prompt']},
                { k: task.get(k, '') for k in ['task_id', 'prompt', 'test', 'declaration', 'import', 'test_setup'] },
            )
            for _ in range(self.num_samples):
                data.append(item)
        return data
    
    def predict_single(self, session: Session, data_item: Dict):
        result = session.action({"role": "user", "content": data_item['input']})
        result = parse_code_from_chat(result, data_item['prompt'], self.language)
        result = cleanup_code(result, self.language)
        return result

class HumanEvalXTranslationTask(HumanEvalXTask):
    def __init__(self, name=None, workers=1, src_lang=None, tgt_lang=None, num_samples=None, datapath=None, **kwargs):
        super().__init__(name, workers, num_samples, datapath, **kwargs)
        self.src_lang = src_lang
        self.tgt_lang = tgt_lang

    def get_data(self) -> Dataset[Dict, Dict]:
        data = Dataset()
        tasks_src = list(stream_jsonl(os.path.join(self.datapath, f"{self.src_lang}.jsonl.gz")))
        tasks_tgt = list(stream_jsonl(os.path.join(self.datapath, f"{self.tgt_lang}.jsonl.gz")))
        for task_src, task_tgt in zip(tasks_src, tasks_tgt):
            model_input = f"Translate the following code from {map_name_prefix[self.src_lang]} to {map_name_prefix[self.tgt_lang]}\n" \
                            + map_lang_prefix[self.src_lang] \
                            + task_src['declaration'] + "\n" \
                            + task_src["canonical_solution"].rstrip() + "\n" \
                            + map_lang_prefix[self.tgt_lang] \
                            + task_tgt['declaration']
            item = DataPiece(
                { 'input': model_input, 'prompt': task_tgt['prompt'] },
                { k: task_tgt.get(k, '') for k in ['task_id', 'prompt', 'test', 'declaration', 'import', 'test_setup'] },
            )
            for _ in range(self.num_samples):
                data.append(item)
        return data
    
    def predict_single(self, session: Session, data_item: Dict):
        result = session.action({"role": "user", "content": data_item['input']})
        result = parse_code_from_chat(result, data_item['prompt'], self.language)
        result = cleanup_code(result, self.tgt_lang)
        return result
