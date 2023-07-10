import jsonlines
import os

##第一步、加载文件，获取文件路径以及标签
dir_path = r"D:\Users\XuYifan\Documents\GitHub\LLM-benchmark\tasks\mmlu\data\\"
allpath = []
lllables = []


def get_lableandwav(path, dir):
    dirs = os.listdir(path)
    for a in dirs:
        #print(a)
        #print(os.path.isfile(path + "/" + a))
        if os.path.isfile(path + "/" + a):
            allpath.append(dirs)
            if dir != "":
                lllables.append(dir)
        else:
            get_lableandwav(str(path) + "/" + str(a), a)
        ##循环遍历这个文件夹

    return allpath, lllables

[allpath, lllables] = get_lableandwav(dir_path, "")
for path, file in zip(lllables,allpath[0]):
    with jsonlines.open(dir_path + path + "\\" + file) as f,jsonlines.open(dir_path + path + "\\" + file.replace("json","jsonl"),'a') as f1:
        for line in f:
            f1.write({"question":line['inputs_pretokenized'],"choices":line['choices_pretokenized'],"answer":line["label"],"label": "MMLU"})
    os.remove(dir_path + path + "\\" + file)
