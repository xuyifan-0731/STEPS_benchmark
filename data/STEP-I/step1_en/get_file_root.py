import os

def get_jsonl_files(folder_path):
    jsonl_files = {}
    for root, dirs, files in os.walk(folder_path):
        for file in files:
            if file.endswith(".jsonl"):
                file_path = os.path.join(root, file)
                relative_path = os.path.relpath(file_path, folder_path)
                save_file = "\t"+relative_path.replace("\\",".").replace(".jsonl","")
                jsonl_files[save_file] = " \"" + "**/" + relative_path.replace("\\","/") + "\""
    return jsonl_files

# 指定文件夹路径
folder_path = "data"

# 获取所有jsonl文件的相对路径
jsonl_files = get_jsonl_files(folder_path)

# 打印结果
for file, relative_path in jsonl_files.items():
    print(f"{file}: {relative_path}")
