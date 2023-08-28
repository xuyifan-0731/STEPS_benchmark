import os
from typing import Union, List, Tuple, Dict, Callable, Any
from copy import deepcopy

import json
from src.agent import Agent, Session
from src.task import Task, Dataset, Session, DataPiece
from .utils import zero, zeroCot, few, prompt_scai, equiv
from collections import defaultdict
from .post_process import parse_math_answer


class ScibenchTask(Task[Dict, str, Dict]):
    @property
    def metrics(self) -> Dict[str, Callable[[List[str], List[Dict]], float]]:
        def evaluate(results, targets):
            dict = defaultdict(list)
            for result, target in zip(results, targets):
                model_output = parse_math_answer(result)
                res_equiv = equiv(model_output, target["answer"], target["unit"])
                #try:
                    #res_equiv = equiv(model_output, target["answer"], target["unit"])
                #except:
                    #res_equiv = False
                if res_equiv:
                    dict[target["source"]].append(1)
                else:
                    dict[target["source"]].append(0)
            results = {"overall":0}
            all_results = []
            for k,v in dict.items():
                results[k] = sum(v) / len(v) * 100
                all_results.append(sum(v) / len(v) * 100)
            if len(all_results) > 0:
                results["overall"] = sum(all_results) / len(all_results)
            print(results)
            return results
        return {"result":evaluate}

    def __init__(self, name=None, workers=1, datapath=None, type="zero", **kwargs):
        super().__init__(name=name, workers=workers, **kwargs)
        self.datapath = datapath
        self.type = type
        assert type in ["zero","zeroCot","zero_sys"], "type not supported, only support zero,zeroCot,zero_sys"


    def get_data(self) -> Dataset[Dict, Dict]:
        data = Dataset()
        sys_prompt=prompt_scai.sys_cal_box2
        files = ["atkins", "calculus","chemmc","class","diff","fund","matter","quan","stat","thermo"]
        for file in files:
            c = 0
            with open("{}/{}.json".format(self.datapath, file), encoding='utf-8') as json_file:
                problems=json.load(json_file)
                for problem_data in problems:
                    problem_text=problem_data["problem_text"]+" The unit of the answer is "+problem_data["unit"]+"."
                    messages=self.get_message(sys_prompt, problem_text)
                    prompt = ""
                    for message in messages:
                        prompt = prompt + message["content"]
                    item = DataPiece(
                        {"input":prompt},
                        {"answer":problem_data["answer_number"],"unit":problem_data["unit"],"source":problem_data["source"]}
                    )
                    data.append(item)    
        return data
        
    def predict_single(self, session: Session, data_item: Dict):
        result = session.action({"role": "user", "content": data_item['input']})
        return result
    
    def get_message(self, sys_prompt, problem_text):
        if "zero" in self.type and "Cot" not in self.type:
            return zero(sys_prompt, problem_text)
        if "zero" in self.type and "Cot" in self.type:
            return zeroCot(sys_prompt, problem_text)
        
class ScibenchTask_cot(ScibenchTask):
    def evaluate(self, agent: Agent) -> Dict[str, Any]:
        print(f"Evaluating task '{self.name}' ...")
        data = self.get_data()
        inputs = data.get_inputs()
        targets = data.get_targets()
        results = self.predict_all(agent, inputs)
        '''
        extract_inputs = []
        for input_item, result_item in zip(inputs,results):
            try:
                if result_item is None:
                    result_item = ""
                extract_inputs.append({"input":input_item["input"] + result_item + "Therefore, the answer is by stating \"The answer is therefore \\boxed{[ANSWER]}.\""})
            except:
                extract_inputs.append({"input":input_item["input"] + "" + "Therefore, the answer is by stating \"The answer is therefore \\boxed{[ANSWER]}.\""})
        results = self.predict_all(agent, extract_inputs)'''
        result_dict = {}

        for metric in self.metrics:
            result_dict[metric] = self.metrics[metric](results, targets)
        print(f"Task '{self.name}' evaluation finished. The results are saved in '{self.get_output_dir()}'")
        self.save_runs_all(inputs, results, targets, result_dict)
        return result_dict