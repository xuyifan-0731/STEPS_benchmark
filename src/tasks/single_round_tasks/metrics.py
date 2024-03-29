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
# from bert_score import BERTScorer
from typing import List
from collections import Counter
from collections import defaultdict
import re
# from SwissArmyTransformer import get_tokenizer
from nltk.translate.bleu_score import sentence_bleu, SmoothingFunction

def extract_text_QA(text):
    pattern = r'答案是(.+?)(。|$)'
    matches =  re.findall(pattern, text)
    if matches:
        return matches[-1][0]
    pattern = r'The answer is therefore(.+?)(。|$)'
    matches =  re.findall(pattern, text)
    if matches:
        return matches[-1][0]
    return text

def normalize_answer(s):
    """Lower text and remove punctuation, articles and extra whitespace."""

    def remove_articles(text):
        return re.sub(r"\b(a|an|the)\b", " ", text)

    def white_space_fix(text):
        return " ".join(text.split())

    def remove_punc(text):
        exclude = set(string.punctuation)
        exclude.add("：")
        return "".join(ch for ch in text if ch not in exclude)

    def lower(text):
        return text.lower()

    if len(s) < 3:
        return extract_text_QA(white_space_fix(remove_punc(lower(s))))
    return extract_text_QA(white_space_fix(remove_articles(remove_punc(lower(s)))))

def word_bleu_score(reference, candidate):
    reference_tokens = list(reference)
    candidate_tokens = list(candidate)
    smoothie = SmoothingFunction().method4
    score = sentence_bleu([reference_tokens], candidate_tokens, smoothing_function=smoothie)
    return score

def calculate_f1(As, B):
    max_score = 0
    for A in As:
        set_A = set(A)
        set_B = set(B)
        common = len(set_A.intersection(set_B))
        precision = common / len(set_A) if len(set_A) > 0 else 0
        recall = common / len(set_B) if len(set_B) > 0 else 0
        f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
        max_score = max(max_score,f1)
    
    return max_score

def bleu_score(predictions, ground_truths, config):
    # for short reference add weights?
    bleu = []
    f1 = []
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
        f1.append(calculate_f1(ground_truths, prediction))
    bleu_score = np.mean(bleu)
    f1_score = np.mean(f1)
    return {"BLEU": bleu_score, "F1": f1_score}


def bert_score_metric(predictions, ground_truths, config):
    return 0
    '''
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
    '''

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

def find_first_capital_letter_raw(doc):
    letter_set = [chr(65+i) for i in range(len(doc["choices"]))] # legal choices
    for c in doc["raw_answer"]:
        if c in letter_set:
            return c
    return ""

def find_first_number(prediction):
    # remove , in number
    prediction = prediction.replace(",", "").strip()
    match = re.search(r'(\d*\.?\d+)%?', prediction)
    if match:
        number_str = match.group(1)
        if match.group().endswith('%'):
            return str(float(number_str) / 100)
        else:
            return number_str
    else:
        return ""

def re_extract_last_sentence(prediction, re_extractor):
    prediction = prediction.strip().lower()
    match = re.search(re_extractor, prediction)
    if match:
        answer = match.group(0)
        answer = answer.strip().split("\n")[0]
        answer = answer.split(".")[0]
        answer = answer.replace("\"", "")
        return answer
    else:
        answer = ""
    return answer

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
        if prediction is None:
            continue
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
        if first_letter in [chr(i) for i in range(65,91)][:len(ground_truth.get("choices"))]:
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
        if prediction is None:
            continue
        # first get first number
        first_number = find_first_number(prediction)
        # print(f"targets: ", ground_truth["targets"][0], " extract: ", first_number)
        if isinstance(ground_truth['targets'],list):
            ground_truth = ground_truth['targets'][0]
        else:
            ground_truth = ground_truth['targets']
        try:
            answer = eval(first_number)
            if "%" in ground_truth:
                ground_truth = eval(ground_truth.replace("%",""))/100
            else:
                ground_truth = eval(ground_truth)
            if math.isclose(answer, ground_truth, abs_tol=0.001):  
                acc += 1
        except:
            if first_number == ground_truth or prediction == ground_truth:
                acc += 1
    
    return acc / tt


def acc_for_general_short_cloze(predictions, ground_truths, config=None):
    '''
    calculate accuracy for general short cloze: Exact Match
    '''
    acc_prefic = 0
    acc_in = 0
    tt = len(predictions)
    if tt == 0:
        return 0
    for prediction, ground_truth in zip(predictions, ground_truths):
        if prediction is None:
            continue
        normal_prediction = normalize_answer(prediction)
        if not normal_prediction: # fix {}][] bad cases in BBH word sorting
            normal_prediction = prediction
        for exact_answer in ground_truth['targets']:
            if normal_prediction == normalize_answer(exact_answer) or normal_prediction.startswith(normalize_answer(exact_answer)):
                acc_prefic += 1
                break
        for exact_answer in ground_truth['targets']:
            if normalize_answer(exact_answer) in normal_prediction:
                acc_in += 1
                break
        
    return {"ACC-prefix": acc_prefic / tt, "ACC-in": acc_in / tt }

def acc_for_re_extraction(predictions, ground_truths, config=None):
    '''
    calculate accuracy for general short cloze: Exact Match
    '''
    extract_template = re.compile(config.extract_template)
    acc = 0
    tt = len(predictions)
    if tt == 0:
        return 0
    for prediction, ground_truth in zip(predictions, ground_truths):
        normal_prediction = re_extract_last_sentence(prediction, extract_template)
        if not normal_prediction:
            normal_prediction = prediction
        for exact_answer in ground_truth['targets']:
            if normal_prediction == exact_answer.strip().lower():
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
        "EM": acc_for_general_short_cloze,
        "RE": acc_for_re_extraction,
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
    "ACC": acc
}

if __name__ == "__main__":
    '''
    pattern = "(?<=the answer is ).*"
    extract_template = re.compile(pattern)
    text = "sdajsdal sdjai sdk therefore, the answer is (A))d, \nis it right?"
    print(re_extract_last_sentence(text, extract_template))'''