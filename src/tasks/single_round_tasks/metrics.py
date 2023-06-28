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
import re
# from SwissArmyTransformer import get_tokenizer
from nltk.translate.bleu_score import sentence_bleu, SmoothingFunction



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
            for turth in ground_truth.get("targets"):
                ground_truths.append(normalize_answer(turth).split())
        else:
            prediction = list(jieba.cut(normalize_answer(prediction)))
            ground_truths = []
            for turth in ground_truth.get("targets"):
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
        for turth in ground_truth.get("targets"):
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
            for turth in ground_truth.get("targets"):
                if len(turth) > 1:
                    ground_truths.append(normalize_answer(turth))
                else:
                    ground_truths.append(turth)
        else:
            prediction = ' '.join(jieba.cut(prediction))
            for turth in ground_truth.get("targets"):
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

def find_first_capital_letter(doc):
    letter_set = [chr(65+i) for i in range(len(doc["choices"]))] # legal choices
    for c in doc["prediction"]:
        if c in letter_set:
            return c
    return ""

def find_first_number(prediction):
    # remove , in number
    prediction = prediction.replace(",", "").strip()
    match = re.search(r'\d*\.?\d+', prediction)
    if match:
        return match.group(0)
    else:
        return ""

def acc_for_multi_choices(predictions, ground_truths, config=None):
    '''
    calculate accuracy for multi choices 
    require ground_truth['targets'][0] to be Capital Letter such as A
    '''
    acc = 0
    tt = len(predictions)
    if tt == 0:
        return 0
    for prediction, ground_truth in zip(predictions, ground_truths):
        assert len(ground_truth['targets'][0]) == 1
        # first extract first capital letter
        is_correct = False
        first_letter = find_first_capital_letter(ground_truth)
        for exact_answer in ground_truth['targets']:
            if first_letter and first_letter == exact_answer:
                acc += 1
                is_correct = True
                break
        if is_correct:
            continue
        
        choices_bleu = []
        # second word bleu choose one answer
        for choice in ground_truth.get("choices"):
            choice = normalize_answer(choice)
            choices_bleu.append(word_bleu_score(choice, prediction))
        correct_index = (ord(ground_truth['targets'][0]) - 65) % len(choices_bleu)
        if choices_bleu.index(max(choices_bleu)) == correct_index:
            acc = acc + 1
        
    return acc / tt

def acc_for_math_short_cloze(predictions, ground_truths, config=None):
    '''
    calculate accuracy for math short cloze 
    require ground_truth['targets'][0] to be pure number such as 0.35
    '''
    acc = 0
    tt = len(predictions)
    if tt == 0:
        return 0
    for prediction, ground_truth in zip(predictions, ground_truths):
        # first get first number
        first_number = find_first_number(prediction)
        # print(f"targets: ", ground_truth["targets"][0], " model answer: ", prediction, " extract: ", first_number)
        if first_number == ground_truth['targets'][0] or prediction == ground_truth['targets'][0]:
            acc += 1
        
    return acc / tt

def acc_for_general_short_cloze(predictions, ground_truths, config=None):
    '''
    calculate accuracy for general short cloze: Exact Match
    '''
    acc = 0
    tt = len(predictions)
    if tt == 0:
        return 0
    for prediction, ground_truth in zip(predictions, ground_truths):
        normal_prediction = normalize_answer(prediction)
        if not normal_prediction: # fix {}][] bad cases in BBH word sorting
            normal_prediction = prediction
        for exact_answer in ground_truth['targets']:
            if normal_prediction == normalize_answer(exact_answer):
                acc += 1
                break
        
    return acc / tt

def acc(predictions, ground_truths, config):
    '''
    calculate accuracy for multi-choices and short-cloze
    post-process methods depends on config.acc_type
    '''
    acc_metrics = {
        "MUL": acc_for_multi_choices,
        "MATHQA": acc_for_math_short_cloze,
        "EM": acc_for_general_short_cloze
    }
    acc_type = config.acc_type
    if acc_type not in acc_metrics:
        print(f"invalid acc type: {acc_type}; using default EM")
        acc_type = "EM"
    return acc_metrics[acc_type](predictions, ground_truths, config)

def calculate_perplexity(loss: List[float], data):
    return math.exp(min(20, np.sum(loss) / data[0]["num_original_tokens"]))

def process_targets(doc):
    if "targets" not in doc:
        return None
    if isinstance(doc["targets"], str):
        return [doc["targets"]]
    if isinstance(doc["targets"], int): # allow answer to be int for MUL
        if doc.get("choices"):
            return [chr(65+doc["targets"]%len(doc.get("choices")))] 
        return [str(doc["targets"])]
    elif isinstance(doc["targets"], list):
        new_targets = []
        for tar in doc["targets"]:
            new_targets.append(str(tar))
        return new_targets

def evaluate_file(file, save_path, metrics=["BLEU", "ROUGE", "ACC"], config=None):
    docs = []
    predictions = []
    empty_count = 0
    with jsonlines.open(file, "r") as f:
        for doc in f:
            doc["targets"] = process_targets(doc)
            if not doc["prediction"] or doc["targets"] == []:
                empty_count += 1
                continue
            docs.append(doc)
            predictions.append(doc["prediction"])
    eval_res = {
        "length": len(docs),
    }
    print(f"empty prediction or answer in {file}: {empty_count} in total")
    for metric in metrics:
        res = DEFAULT_METRICS[metric](predictions, docs, config)
        if isinstance(res, dict):
            eval_res.update(**res)
        else:
            eval_res[metric] = res
    import json
    with open(save_path, "w", encoding="utf-8") as f:
        f.write(json.dumps(eval_res, indent=2))
        f.close()

DEFAULT_METRICS = {
    "BLEU": bleu_score,
    "ROUGE": rouge_score,
    "ACC": acc,
}

if __name__ == "__main__":
    # hypothesis = "###刚刚发声，A股这种情况十分罕见！大聪明逆市抄底330亿，一篇研报引爆全球，市场逻辑生变？"
    # print(list(jieba.cut(hypothesis)))
    # hypothesis = ' '.join(jieba.cut(hypothesis))

    # reference = "刚刚过去的这个月，美股总市值暴跌了将近6万亿美元（折合人民币超过40万亿），这背后的原因可能不仅仅是加息这么简单。最近瑞士信贷知名分析师Zoltan Polzsar撰写了一篇极其重要的文章，详细分析了现有世界秩序的崩坏本质以及美国和西方将要采取的应对策略。在该文中，Zoltan Polzsar直指美国通胀的本质和其长期性。同期，A股市场亦出现了大幅杀跌的情况。"
    # reference = ' '.join(jieba.cut(reference))

    # rouge = Rouge_chinese()
    # scores = rouge.get_scores(hypothesis, reference)

    # print(scores)

    data_file = "/data/share/leixy/STEPS_benchmark/outputs/gsm8k_en_zero_shot_cot/ChatGLM_6b_v2/prediction/ChatGLM_6b_v2.gsm8k_en.predict.jsonl"
    save_file = "test.json"
    evaluate_file(data_file, save_file, metrics=["ACC"])

