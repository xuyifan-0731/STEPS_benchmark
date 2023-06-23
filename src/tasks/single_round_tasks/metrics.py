from types import resolve_bases
import jsonlines
import re
import math
import string
import functools
from rouge import Rouge
from rouge_chinese import Rouge as Rouge_chinese
import jieba
import numpy as np
from bert_score import BERTScorer
from typing import List
from collections import Counter
from collections import defaultdict
# from SwissArmyTransformer import get_tokenizer
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
        # 选择题经常是短选项，因此使用字母计算bleu。后续可考虑改成glm token F1 score
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
        # "PPL": calculate_perplexity,
        # "BERTScore": bert_score_metric,
    }
)

if __name__ == "__main__":
    hypothesis = "###刚刚发声，A股这种情况十分罕见！大聪明逆市抄底330亿，一篇研报引爆全球，市场逻辑生变？"
    print(list(jieba.cut(hypothesis)))
    hypothesis = ' '.join(jieba.cut(hypothesis))

    reference = "刚刚过去的这个月，美股总市值暴跌了将近6万亿美元（折合人民币超过40万亿），这背后的原因可能不仅仅是加息这么简单。最近瑞士信贷知名分析师Zoltan Polzsar撰写了一篇极其重要的文章，详细分析了现有世界秩序的崩坏本质以及美国和西方将要采取的应对策略。在该文中，Zoltan Polzsar直指美国通胀的本质和其长期性。同期，A股市场亦出现了大幅杀跌的情况。"
    reference = ' '.join(jieba.cut(reference))

    rouge = Rouge_chinese()
    scores = rouge.get_scores(hypothesis, reference)

    print(scores)

