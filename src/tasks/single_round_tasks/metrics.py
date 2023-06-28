import jsonlines
import math
import string
from rouge import Rouge
from rouge_chinese import Rouge as Rouge_chinese
import jieba
import numpy as np
from bert_score import BERTScorer
from typing import List
from collections import defaultdict
from nltk.translate.bleu_score import sentence_bleu, SmoothingFunction

import re


def normalize_answer(s):
    """Lower text and remove punctuation, articles and extra whitespace."""

    def remove_articles(text):
        return re.sub(r"\b(a|an|the)\b", " ", text)

    def white_space_fix(text):
        return " ".join(text.split())

    def remove_punc(text):
        exclude = set(string.punctuation)
        return "".join(ch for ch in text if ch not in exclude)

    def lower(text):
        return text.lower()

    if len(s) < 3:
        return white_space_fix(remove_punc(lower(s)))
    return white_space_fix(remove_articles(remove_punc(lower(s))))

def word_bleu_score(reference, candidate):
    reference_tokens = list(reference)
    candidate_tokens = list(candidate)
    smoothie = SmoothingFunction().method4
    score = sentence_bleu([reference_tokens], candidate_tokens, smoothing_function=smoothie)
    return score

def bleu_score(predictions, ground_truths, config):
    # for short reference add weights?
    bleu = []
    smoothing = SmoothingFunction()
    for prediction, ground_truth in zip(predictions, ground_truths):
        if not isinstance(prediction, str):
            print(f"Return error {prediction}")
            continue
        if config.language == "en":
            prediction = normalize_answer(prediction).split()
            ground_truths = []
            for turth in ground_truth[0].get("targets"):
                ground_truths.append(normalize_answer(turth).split())
        else:
            prediction = list(jieba.cut(normalize_answer(prediction)))
            ground_truths = []
            for turth in ground_truth[0].get("targets"):
                ground_truths.append(list(jieba.cut(normalize_answer(turth))))
        bleu.append(sentence_bleu(ground_truths, prediction, smoothing_function=smoothing.method1))
    bleu_score = np.mean(bleu)
    return bleu_score

def bert_score_metric(predictions, ground_truths, config):
    bert_score_result = []
    scorer = BERTScorer(lang=config.language, rescale_with_baseline=True)
    for prediction, ground_truth in zip(predictions, ground_truths):
        if not isinstance(prediction, str):
            print(f"Return error {prediction}")
            continue
        prediction = normalize_answer(prediction)
        ground_truths = []
        for turth in ground_truth[0].get("targets"):
            ground_truths.append(normalize_answer(turth))
        bert_score_result.append(scorer.score([prediction], ground_truths)[2].item())
    bert_score_result_score = np.mean(bert_score_result)
    return bert_score_result_score

def rouge_score(predictions, ground_truths, config):
    if config.language == "en":
        rouge = Rouge()
    else:
        rouge = Rouge_chinese()
    rouge_1_list = []
    rouge_2_list = []
    rouge_l_list = []
    for prediction, ground_truth in zip(predictions, ground_truths):
        if not isinstance(prediction, str):
            print("Return error")
            continue
        prediction = normalize_answer(prediction)
        ground_truths = []
        if config.language  == "en":
            for turth in ground_truth[0].get("targets"):
                if len(turth) > 1:
                    ground_truths.append(normalize_answer(turth))
                else:
                    ground_truths.append(turth)
        else:
            prediction = ' '.join(jieba.cut(prediction))
            for turth in ground_truth[0].get("targets"):
                if len(turth) > 1:
                    ground_truths.append(' '.join(jieba.cut(normalize_answer(turth))))
                else:
                    ground_truths.append(' '.join(jieba.cut(turth)))
        rouge_1 = 0
        rouge_2 = 0
        rouge_l = 0
        for truth in ground_truths:
            try:
                rouge_1 = max(rouge_1, rouge.get_scores(truth, prediction)[0]['rouge-1']["f"])
            except:
                pass
            try:
                rouge_2 = max(rouge_2, rouge.get_scores(truth, prediction)[0]['rouge-2']["f"])
            except:
                pass
            try:
                rouge_l = max(rouge_l, rouge.get_scores(truth, prediction)[0]['rouge-l']["f"])
            except:
                pass
        rouge_1_list.append(rouge_1)
        rouge_2_list.append(rouge_2)
        rouge_l_list.append(rouge_l)

    rouge_1 = np.mean(rouge_1_list)
    rouge_2 = np.mean(rouge_2_list)
    rouge_l = np.mean(rouge_l_list)

    return {"ROUGE-1": rouge_1, "ROUGE-2": rouge_2, "ROUGE-L": rouge_l}


def acc_for_multi(predictions, ground_truths, config):
    acc = 0
    tt = len(predictions)
    if tt == 0:
        return 0
    smoothing = SmoothingFunction()
    idx = 0
    is_qa = False
    if ground_truths[0][0].get("choices") == None:
        print("Acc means choices acc in multi-choices type tasks and EM in qa task.")
        is_qa = True
    for prediction, ground_truth in zip(predictions, ground_truths):
        idx = idx + 1
        if not isinstance(prediction, str):
            print("Return error")
            continue
        is_correct = False       
        prediction = normalize_answer(prediction)
        for exact_answer in ground_truth[0]['targets']:
            if prediction == normalize_answer(exact_answer) or prediction in normalize_answer(exact_answer):
                acc = acc + 1
                is_correct = True
                break
        if is_qa:
            continue
        if is_correct:
            continue
        choices_bleu = []
        for choice in ground_truth[0].get("choices"):
            choice = normalize_answer(choice)
            choices_bleu.append(word_bleu_score(choice, prediction))

        correct_index = ground_truth[0]['choices'].index(ground_truth[0]['targets'][0])
        if choices_bleu.index(max(choices_bleu)) == correct_index:
            acc = acc + 1

    return acc / tt


def calculate_perplexity(loss: List[float], data):
    return math.exp(min(20, np.sum(loss) / data[0]["num_original_tokens"]))


def special_for_dataset(predictions, examples):
    print("Metrics not found, maybe dataset special metric or metric name error")
    return True

def evaluate_file(file, save_path, metrics=["BLEU", "ROUGE", "ACC"]):
    docs = []
    predictions = []
    empty_count = 0
    with jsonlines.open(file, "r") as f:
        for doc in f:
            if isinstance(doc["targets"], str):
                doc["targets"] = [doc["targets"]]
            if isinstance(doc["targets"], int): # allow answer to be int for MUL 
                doc["targets"] = [str(doc["targets"])]
            if not doc["prediction"] or doc["targets"] == []:
                empty_count += 1
                continue
            docs.append([doc])
            predictions.append(doc["prediction"])
    eval_res = {
        "length": len(docs),
    }
    print(f"empty prediction or answer in {file}: {empty_count} in total")
    for metric in metrics:
        res = DEFAULT_METRICS[metric](predictions, docs)
        if isinstance(res, dict):
            eval_res.update(**res)
        else:
            eval_res[metric] = res
    import json
    with open(save_path, "w", encoding="utf-8") as f:
        f.write(json.dumps(eval_res, indent=2))
        f.close()


DEFAULT_METRICS = defaultdict(lambda: special_for_dataset)
DEFAULT_METRICS.update(
    {
        "BLEU": bleu_score,
        "ROUGE": rouge_score,
        "ACC": acc_for_multi,
        "PPL": calculate_perplexity,
        "BERTScore": bert_score_metric,
    }
)

