import os

from typing import Union, List, Tuple, Dict, Callable
from src.agent import Session

from src.task import Task, Dataset, Session, DataPiece

from .utils import cleanup_code, parse_code_from_chat, stream_jsonl, process_extra_prompt
from .evaluator.evaluate import evaluate_functional_correctness

InputType = Tuple[str, str, str, str, str, str]

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

class HumanEvalXTask(Task[InputType, str]):    
    @property
    def metrics(self) -> Dict[str, Callable[[List[InputType], List[str]], float]]:
        def evaluate(results, targets):
            samples = []
            for i, result in enumerate(results):
                sample = {k: result[k] for k in ['task_id', 'prompt', 'generation', 'declaration', 'import', 'test_setup']}
                sample['test'] = targets[i]
                samples.append(sample)
            return evaluate_functional_correctness(samples, k=[1])['pass@1']
        return {'pass@1': evaluate}

    def __init__(self, name=None, workers=1, num_samples=None, datapath=None):
        super().__init__(name, workers)
        self.num_samples = num_samples
        self.datapath = datapath

    def get_data(self) -> Dataset[InputType, str]:
        # (
        #     (
        #         "task_id",
        #         "model_input",
        #         "prompt",
        #         "declaration"
        #         "import",
        #         "test_setup",
        #     ),
        #     "test"
        # )
        raise NotImplementedError
    
    def predict_single(self, session: Session, data_item: InputType):
        result = session.action({"role": "user", "content": data_item[1]})
        # result = parse_code_from_chat(result, data_item[2], self.language)
        result = cleanup_code(result, self.language)
        return {
            "task_id": data_item[0],
            "prompt": data_item[2],
            "generation": result,
            "declaration": data_item[3],
            "import": data_item[4],
            "test_setup": data_item[5],
        }

class HumanEvalXGenerationTask(HumanEvalXTask):
    def __init__(self, name=None, workers=1, language=None, num_samples=None, datapath=None):
        super().__init__(name, workers, num_samples, datapath)
        self.language = language

    def get_data(self) -> Dataset[InputType, str]:
        data = Dataset()
        for task in stream_jsonl(os.path.join(self.datapath, f"{self.language}.jsonl.gz")):
            item = DataPiece(
                (
                    task['task_id'], 
                    f"Complete the following function and do not add main function.\n" + process_extra_prompt(task['prompt'], self.language), 
                    task['prompt'],
                    task['declaration'],
                    task.get('import', ''),
                    task.get('test_setup', '')
                ), 
                task['test']
            )
            for _ in range(self.num_samples):
                data.append(item)
        return data
    
class HumanEvalXTranslationTask(HumanEvalXTask):
    def __init__(self, name=None, workers=1, src_lang=None, tgt_lang=None, num_samples=None, datapath=None):
        super().__init__(name, workers, num_samples, datapath)
        self.src_lang = src_lang
        self.tgt_lang = tgt_lang

    def get_data(self) -> Dataset[InputType, str]:
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
                (
                    task_tgt['task_id'], 
                    model_input,
                    task_tgt['prompt'],
                    task_tgt['declaration'],
                    task_tgt.get('import', ''),
                    task_tgt.get('test_setup', '')
                ), 
                task_tgt['test']
            )
            for _ in range(self.num_samples):
                data.append(item)
        return data