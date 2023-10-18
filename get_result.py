import os
import re
import json
import jsonlines
import traceback
import pandas as pd
import os
import shutil
from collections import defaultdict
from nltk.translate.bleu_score import sentence_bleu, SmoothingFunction

file = "steps_22"



def word_bleu_score(reference, candidates):
    max = 0
    model = "None"
    for candidate in candidates:
        reference_tokens = list(reference)
        candidate_tokens = list(candidate)
        smoothie = SmoothingFunction().method4
        score = sentence_bleu([reference_tokens], candidate_tokens, smoothing_function=smoothie)
        if score > max:
            max = score
            model = candidate
    return model

def filter_max_records(record_list):
    grouped_records = defaultdict(list)

    # 根据 "model_name", "source", "dataset" 进行分组
    for record in record_list:
        key = (record.get("model_name"), record.get("source"), record.get("dataset"))
        grouped_records[key].append(record)

    filtered_records = []

    # 在每一组里面，找到值最大或键最多的记录
    for group in grouped_records.values():
        max_record = None
        for record in group:
            #if "chatglm2-12b" in record["model_name"] and record["dataset"] == "ape_210k_zh":
                #print(1)
            if max_record is None:
                max_record = record
            else:              
                if len(record.keys()) != len(max_record.keys()):
                    max_record = record if len(record.keys()) > len(max_record.keys()) else max_record
                else:
                    for key in set(record.keys()) - {"model_name", "source", "dataset"}:
                        if key in max_record:
                            if record[key] > max_record[key]:
                                max_record = record
                        else:
                            max_record = record if record[key] > 0 else max_record

        filtered_records.append(max_record)

    return filtered_records

def merge_dicts(dict_list):
    merged_dict = {}
    for d in dict_list:
        if not d:
            continue
        for key, value in d.items():
            if key in merged_dict:
                merged_dict[key].append(value)
            else:
                merged_dict[key] = [value]
    return merged_dict

def dict_to_excel(merged_dict, excel_path):
    df = pd.DataFrame(merged_dict)
    # print(df.to_string(index=False))
    df.to_excel(excel_path, index=False, engine='openpyxl')
    

def get_single_round(path):
    try:
        results = []
        config_path = os.path.join(path,"configs.json")
        with open(config_path,"r") as f:
            model_name = json.loads(f.read())["agent"]["fields"]["name"]

        files = os.listdir(path)
        for file in files:
            result_path = os.path.join(path,file,model_name,"results.json")
            if os.path.isfile(result_path):
                with open(result_path,"r") as f:
                    file = json.loads(f.read())
                    for k,v in file["calculate"]["groups"].items():
                        dataset_name = k
                        source = result_path.replace(path,"").split("/")[1]
                        result = {"model_name":model_name,"source":source, "dataset":dataset_name}
                        for metric,v2 in v.items():
                            result[metric] = v2["fine_grained_average"]
                        results.append(result)
        return results
    except Exception as e:
        print(path,e)
        return False


output_file = os.listdir(file)

result_dict = {
    "single_round": get_single_round
}

def get_result_single_round(dataset = "single_round"):
    dict_list = []
    for file_name in output_file:
        filepath = os.path.join(file,file_name)
        output = result_dict[dataset](filepath)
        if not output:
            continue
        dict_list.extend(output)
    dict_list = filter_max_records(dict_list)
    dict_to_excel(dict_list, f'results_excel/output_{dataset}.xlsx')


def merge_result():
    output = pd.read_excel("results_excel/output_single_round.xlsx")
    df_output = pd.DataFrame()
    df_metric = pd.read_excel("metrics.xlsx")
    metric = df_metric.set_index(['source', 'dataset'])['metric'].to_dict()
    dataset_set = set()
    for idx,record in output.iterrows():
        model = record["model_name"]
        if "struct" in record["source"]:
            continue
        
        key = (record["source"], record["dataset"])
        if not metric.get(key):
            continue
        metric_select = metric.get(key)
        result = record.get(metric_select)
        df_output = df_output._append({"model":model,"source":key[0],"dataset":key[1],"metric":metric_select,"result":result,"length":record.get("length")},ignore_index = True)
        dataset_set.add(key)
    df_output.to_excel("output.xlsx")

get_result_single_round()
merge_result()