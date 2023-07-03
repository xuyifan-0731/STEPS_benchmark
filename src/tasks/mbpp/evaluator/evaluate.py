import numpy as np

from typing import *
from tqdm.auto import tqdm
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed

from .metric import estimate_pass_at_k
from .execution import check_correctness

def process_humaneval_test(sample):
    tests = sample["test_list"]
    test_setup = sample["test_setup"]
    code = sample["generation"]

    test_string = code.strip() + '\n' + test_setup.strip() + '\n' + '\n'.join(tests)
    return test_string

def evaluate_functional_correctness(
        samples,
        n_workers: int = 32,
        timeout: float = 500.0,
        k: List[int] = [1, 10, 100],
):
    with ThreadPoolExecutor(max_workers=n_workers) as executor:

        futures = []
        completion_id = Counter()
        n_samples = 0
        results = defaultdict(list)

        print("Reading samples...")
        for sample in tqdm(samples):
            task_id = sample["task_id"]
            # tmp_dir_ = os.path.join(tmp_dir, lang, "evaluation")
            sample["task_id"] = task_id
            sample["test_code"] = process_humaneval_test(sample)
            if sample["test_code"] is None:
                continue
            if "completion_id" in sample:
                completion_id_ = sample["completion_id"]
            else:
                completion_id_ = completion_id[task_id]
            args = (task_id, sample, timeout, completion_id_)
            future = executor.submit(check_correctness, *args)
            futures.append(future)
            completion_id[task_id] += 1
            n_samples += 1

        print(completion_id)

        print("Running test suites...")
        for future in tqdm(as_completed(futures), total=len(futures)):
            result = future.result()
            results[result["task_id"]].append((result["completion_id"], result))

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
    return pass_at_k
