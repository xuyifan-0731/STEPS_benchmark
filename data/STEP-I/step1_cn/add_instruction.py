import os
import jsonlines

def recursive_listdir(path):
    file_list = []
    files = os.listdir(path)
    for file in files:
        file_path = os.path.join(path, file)

        if os.path.isfile(file_path):
            file_list.append(file)

    return file_list

path = r"D:\Users\XuYifan\Documents\GitHub\LLM-benchmark\tasks\basic-abilities\data\math"
files = recursive_listdir(path)

for file in files:
    with jsonlines.open(os.path.join(path,file)) as f,jsonlines.open(os.path.join(path,"rewrite",file),'a') as f1:
        for line in f:
            if line.get("instruction"):
                break
            else:
                line["instruction"] = "Solve the following math problems,let's think step by step: "
                f1.write(line)
