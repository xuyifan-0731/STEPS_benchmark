from src.task import Task, Dataset, DataPiece, Session
from .ast_eval_hf import eval_hf
from .ast_eval_tf import eval_tf
from .ast_eval_th import eval_th
import json, os
from functools import partial

class Apibench(Task):
    
    def __init__(self, **configs):
        self.data_path = configs['data_path']
        super().__init__(**configs)
    
    def _calculate(self, hub, split, eval_fun, outputs, targets):
        tag = f'{hub}_{split}'
        llm_response = [{'text': output, 'question_id': target['question_id']} for output, target in zip(outputs, targets) if target['tag'] == tag]
        
        api_dataset = os.path.join(self.data_path, 'api', f'{hub}_api.jsonl')
        apibench = os.path.join(self.data_path, 'apibench', f'{hub}_eval.json')
        
        acc, hall = eval_fun(api_dataset, apibench, llm_response)
        
        return acc, hall
        
    
    @property
    def metrics(self):
        metric = {}
        for hub, eval_fun in [('huggingface', eval_hf), ('tensorflowhub', eval_tf), ('torchhub', eval_th)]:
             for split in ['0_shot', 'bm25', 'gpt_index', 'oracle']:
                tag = f'{hub}_{split}'
                metric[tag] = partial(self._calculate, hub, split, eval_fun)
        
        return metric
    
    def get_data(self):
        data = Dataset()
        
        for hub in ['huggingface', 'tensorflowhub', 'torchhub']:
            for split in ['0_shot', 'bm25', 'gpt_index', 'oracle']:
                testset = f'questions_{hub}_{split}.jsonl'
                for itemline in open(os.path.join(self.data_path, 'question', hub, testset)).readlines():
                    item = json.loads(itemline)
                    datapiece = DataPiece(item['text'], {'tag': f'{hub}_{split}', 'question_id': item['question_id']})
                    data.append(datapiece)
                    
        return data

    def predict_single(self, session, data_item):
        return session.action({"role": "user", "content": data_item})