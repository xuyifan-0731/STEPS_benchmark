import os
import json
import jsonlines
import re
import string
# from SwissArmyTransformer import get_tokenizer
from nltk.translate.bleu_score import sentence_bleu, SmoothingFunction
from src.tasks import SingleRoundTask

def word_bleu_score(reference, candidate):
    reference_tokens = list(reference)
    candidate_tokens = list(candidate)
    smoothie = SmoothingFunction().method4
    score = sentence_bleu([reference_tokens], candidate_tokens, smoothing_function=smoothie)
    return score

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

def find_first_capital_letter(doc):
    letter_set = [chr(65+i) for i in range(len(doc["choices"]))] # legal choices
    for c in doc["prediction"]:
        if c in letter_set:
            return c
    return ""

def get_answer(doc):
    first_letter = find_first_capital_letter(doc)

    if first_letter:
        doc["prediction"] = first_letter
    else:
        choices_bleu = []
        # second word bleu choose one answer
        for choice in doc.get("choices"):
            choice = normalize_answer(choice)
            choices_bleu.append(word_bleu_score(choice, doc["prediction"]))
        letter_map = {0:"A", 1:"B", 2:"C", 3:"D"}
        doc["prediction"] = letter_map[choices_bleu.index(max(choices_bleu))]

    return doc

class CEvalTask(SingleRoundTask):
    def save_prediction_to_file(self, file, data, agent_name):
        file = ".".join(file.split(".")[:-1])
        filename = os.path.join(self.get_output_dir(), agent_name, "prediction", f"{agent_name}.{file}.predict.jsonl")
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        with jsonlines.open(filename, "w") as file:
            for output_data in data:
                file.write(output_data)
            file.close()

    def save_overall_results(self, result_dict_all, cal_results, agent_name):
        fileroots = os.path.join(self.get_output_dir(), agent_name, "prediction")
        models = os.listdir(fileroots)
        os.makedirs(os.path.join(self.get_output_dir(), agent_name, "submit"), exist_ok=True)
        for model in models:
            data_dir = os.path.join(self.get_output_dir(), agent_name, "prediction", model)
            save_path = os.path.join(self.get_output_dir(), agent_name, "submit", model + ".json")
            files = os.listdir(data_dir)
            res = {}
            for file in files:
                class_ = "_".join(file.split('.')[-3].split("_")[:-1])
                res1 = {}
                cnt = 0
                with jsonlines.open(os.path.join(data_dir, file), "r") as f:
                    for doc in f:
                        doc = get_answer(doc)
                        res1[str(cnt)] = doc["prediction"]
                        if doc["prediction"] not in ["A", "B", "C", "D"]:
                            print("error")
                        cnt += 1
                    f.close()
                
                res[class_] = res1
            with open(save_path, "w") as f:
                f.write(json.dumps(res, indent=2))
                f.close()
                print(f"C-Eval submit results of {model} have been saved in file: {save_path}")
        

