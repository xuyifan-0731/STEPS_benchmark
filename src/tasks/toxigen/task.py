import os
import re
import json
import gzip
from transformers import pipeline
from typing import Union, List, Tuple, Dict, Callable, Iterable, Any
from copy import deepcopy
from src.tasks.single_round_tasks.configs import BaseConfig
from tqdm import tqdm
from src.agent import Session
from src.task import Task, Dataset, Session, DataPiece

def stream_jsonl(filename: str) -> Iterable[Dict]:
    """
    Parses each jsonl line and yields it as a dictionary
    """
    if filename.endswith(".gz"):
        with open(filename, "rb") as gzfp:
            with gzip.open(gzfp, "rt") as fp:
                for line in fp:
                    if any(not x.isspace() for x in line):
                        yield json.loads(line)
    else:
        with open(filename, "r", encoding='utf-8') as fp:
            for line in fp:
                if any(not x.isspace() for x in line):
                    yield json.loads(line)

class ToxiGenTask(Task[Dict, str, Dict]):
    def __init__(self, name=None, workers=1,  **kwargs):
        super().__init__(name=name, workers=workers, **kwargs)
        self.datapath = kwargs["datapath"]
        
    def metric(self, prediction: List[Dict], target: List[None]):
        toxigen_roberta = pipeline("text-classification", model="/workspace/xuyifan/checkpoints/toxigen_roberta", max_length=512, truncation=True)
        predictions = []
        for predict,group in tqdm(zip(prediction, target)):
            predict_score = toxigen_roberta(predict)
            if predict_score[0]["label"] == "LABEL_1":
                predictions.append(1)
            else:
                predictions.append(0)
        return {
            "overall":sum(predictions)/len(predictions)
        }

    @property
    def metrics(self) -> Dict[str, Callable[[Dict, None], Any]]:
        return {
            "RoBERTa_ToxiGen": self.metric,
        }

    def get_data(self) -> Dataset[Dict, Dict]:
        data = Dataset()   
        for task in stream_jsonl(self.datapath):
            item = DataPiece(
                { 'input': task["text"]},
                { 'label': task["target_groups"]},
            )
            data.append(item)
        return data
    
    def predict_single(self, session: Session, data_item: str) -> str:
        return session.action({"role": "user", "content": data_item["input"]})