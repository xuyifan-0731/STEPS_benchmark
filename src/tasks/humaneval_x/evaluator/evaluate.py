import os
import numpy as np

from typing import *
from tqdm.auto import tqdm
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
import shutil

from .metric import estimate_pass_at_k
from .execution import check_correctness

LANGUAGE_NAME = {
    "cpp"   : "CPP",
    "go"    : "Go",
    "java"  : "Java",
    "js"    : "JavaScript",
    "python": "Python",
}

IMPORT_HELPER = {
    "python": [
        "import math",
        "import re",
        "import sys",
        "import copy",
        "import datetime",
        "import itertools",
        "import collections",
        "import heapq",
        "import statistics",
        "import functools",
        "import hashlib",
        "import numpy",
        "import numpy as np",
        "import string",
        "from typing import *",
        "from collections import *",
    ],
    "go"    : [
        "math",
        "strings",
        "fmt",
        "strconv",
        "time",
        "bytes",
        "regexp",
        "sort",
        "math/rand",
        "crypto/md5",
    ],
    "cpp"   : [
        "#include<stdlib.h>",
        "#include<algorithm>",
        "#include<math.h>",
        "#include<stdio.h>",
        "#include<vector>",
        "#include<string>",
        "#include<climits>",
        "#include<cstring>",
        "#include<iostream>",
    ],
}

def process_humaneval_test(sample):
    task_id = sample["task_id"]
    language = task_id.split("/")[0].lower()

    prompt = sample["prompt"]
    test = sample["test"]
    code = sample["generation"]

    # Pre-process for different languages
    try:
        if language == "python":
            code_ = []
            for line in code.split("\n"):
                if (len(line.strip()) > 0 and line[0] != ' ' and line[0] != '\t'):
                    break
                code_.append(line)
            code = "\n".join(code_)
            test_setup = "\n".join(IMPORT_HELPER["python"]) + "\n"
            test_string = test_setup + prompt + code + "\n" + test + "\n"
        elif language == "cpp":
            test_set_up = ""
            for s in IMPORT_HELPER["cpp"]:
                if s not in prompt:
                    test_set_up += s + "\n"
            test_string = test_set_up + "\n" + prompt + code + "\n" + test
        elif language == "java":
            test_string = prompt + code + "\n" + test
        elif language == "js" or language == "javascript":
            test_string = prompt + code + "\n" + test
        elif language == "go":
            import_string = sample["import"]
            prompt = prompt.replace(import_string, "")
            test = sample["test"]
            test_setup = sample["test_setup"]
            other_pkgs = []
            for pkg in IMPORT_HELPER["go"]:
                if pkg not in test_setup:
                    p = pkg.split("/")[-1]
                    if p + "." in code:
                        other_pkgs.append(f"\"{pkg}\"")
            if other_pkgs:
                import_other_pkgs = "import (\n" + "    ".join([p + "\n" for p in other_pkgs]) + ")"
                test_string = test_setup + "\n" + import_other_pkgs + "\n" + prompt + code + "\n" + test
            else:
                test_string = test_setup + "\n" + prompt + code + "\n" + test
        elif language == "rust":
            main = "\nfn main(){ \n } \n"
            declaration = sample["declaration"]
            test_string = main + declaration + prompt + code + test
    except:
        test_string = 'error'
    return test_string

def evaluate_functional_correctness(
        samples,
        tmp_dir: str = "src/tasks/humaneval_x/env",
        n_workers: int = 32,
        timeout: float = 3.0,
        k: List[int] = [1, 10, 100],
):
    with ThreadPoolExecutor(max_workers=n_workers) as executor:

        futures = []
        completion_id = Counter()
        n_samples = 0
        results = defaultdict(list)

        os.makedirs(os.path.join(tmp_dir, 'tmp'), exist_ok=True)
        print("Reading samples...")
        for sample in tqdm(samples):
            task_id = sample["task_id"]
            lang = task_id.split("/")[0].lower()
            if lang == "javascript":
                lang = "js"
            # tmp_dir_ = os.path.join(tmp_dir, lang, "evaluation")
            sample["task_id"] = task_id
            sample["test_code"] = process_humaneval_test(sample)
            if sample["test_code"] is None:
                continue
            if "completion_id" in sample:
                completion_id_ = sample["completion_id"]
            else:
                completion_id_ = completion_id[task_id]
            args = (task_id, sample, lang, timeout, tmp_dir, completion_id_)
            future = executor.submit(check_correctness, *args)
            futures.append(future)
            completion_id[task_id] += 1
            n_samples += 1

        # print(completion_id)

        print("Running test suites...")
        for future in tqdm(as_completed(futures), total=len(futures)):
            result = future.result()
            results[result["task_id"]].append((result["completion_id"], result))
        # shutil.rmtree(os.path.join(tmp_dir, 'tmp'))

    # Calculate pass@k.
    total, correct = [], []
    for result in results.values():
        passed = [r[1]["passed"] for r in result]
        total.append(len(passed))
        correct.append(sum(passed))
    total = np.array(total)
    correct = np.array(correct)

    ks = k
    pass_at_k = {f"pass@{k}": estimate_pass_at_k(total, correct, k).mean()
                    for k in ks if (total >= k).all()}
    print(pass_at_k)

    # print("Writing to: ", "out.jsonl")
    # fp = open("out.jsonl", 'w')
    # for res in results.values():
    #     for r in res:
    #         fp.write(json.dumps(r[1]) + "\n")
    return pass_at_k



def check_samples(
        samples,
        tmp_dir: str = "src/tasks/humaneval_x/env",
        n_workers: int = 32,
        timeout: float = 3.0,
        k: List[int] = [1, 10, 100],
):
    with ThreadPoolExecutor(max_workers=n_workers) as executor:

        futures = []
        completion_id = Counter()
        n_samples = 0
        results = defaultdict(list)

        os.makedirs(os.path.join(tmp_dir, 'tmp'), exist_ok=True)
        print("Reading samples...")
        for sample in tqdm(samples):
            task_id = sample["task_id"]
            lang = task_id.split("/")[0].lower()
            if lang == "javascript":
                lang = "js"
            # tmp_dir_ = os.path.join(tmp_dir, lang, "evaluation")
            sample["task_id"] = task_id
            sample["test_code"] = process_humaneval_test(sample)
            if sample["test_code"] is None:
                continue
            if "completion_id" in sample:
                completion_id_ = sample["completion_id"]
            else:
                completion_id_ = completion_id[task_id]
            args = (task_id, sample, lang, timeout, tmp_dir, completion_id_)
            future = executor.submit(check_correctness, *args)
            futures.append(future)
            completion_id[task_id] += 1
            n_samples += 1
        print(n_samples)

        # print(completion_id)
    return n_samples
