import os

from typing import Union, List, Tuple, Dict, Callable
from src.agent import Session

from src.task import Task, Dataset, Session, DataPiece
from src.agent import Agent
from src import print_rank_0

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

class HumanEvalXTranslationTask(Task[InputType, str]):    
    @property
    def metrics(self) -> Dict[str, Callable[[List[InputType], List[str]], float]]:
        return None        

    def __init__(self, name=None, workers=1, src_lang=None, tgt_lang=None, num_samples=None, datapath=None):
        super().__init__(name, workers)
        self.src_lang = src_lang
        self.tgt_lang = tgt_lang
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
    
    def predict_single(self, session: Session, data_item: InputType):
        result = session.action({"role": "user", "content": data_item[1]})
        result = parse_code_from_chat(result, data_item[2], self.language)
        result = cleanup_code(result, self.language)
        return result
    
    def evaluate(self, agent: Agent):
        print_rank_0(f"Evaluating task '{self.name}' ...")
        data = self.get_data()
        inputs = data.get_inputs()
        targets = data.get_targets()
        results = self.predict_all(agent, inputs)

        samples = []
        for i, result in enumerate(results):
            sample = {
                "task_id": inputs[i][0],
                "prompt": inputs[i][2],
                "generation": result,
                "test": targets[i],
                "declaration": inputs[i][3],
                "import": inputs[i][4],
                "test_setup": inputs[i][5],
            }
            samples.append(sample)

        result_dict = evaluate_functional_correctness(samples)
        print_rank_0(f"Task '{self.name}: {self.src_lang} -> {self.tgt_lang}' evaluation results: {result_dict}")
        return result_dict
