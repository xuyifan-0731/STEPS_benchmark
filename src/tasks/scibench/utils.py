import os
import numpy as np
import operator
import argparse
import json
import math
from . import prompt_scai
from .post_process import parse_math_answer


def few(sys, problem, problem_eg, exp_eg, answer_eg, unit_eg, Cot):
    if sys !="":
        
        messages=[{"role": "system", "content": sys}]
    else:
        messages=[]
    for idx in range(len(problem_eg)):
        question_input = "Problem {}.   ".format(idx + 1) + problem_eg[idx] + "\n"
        if Cot:
            question_output = "Explanation for Problem {}:   ".format(idx + 1) + exp_eg[idx] + "\n" + "The answer is \\boxed{"+ answer_eg[idx]+"} "+unit_eg[idx]
        else: 
            question_output = "The answer is \\boxed{"+ answer_eg[idx]+"} "+unit_eg[idx]
        
        messages += [
                {"role": "user", "content": question_input},
                {"role": "assistant", "content": question_output},
            ]
    test_question= "Problem {}.   ".format(len(problem_eg) + 1) + problem + "\n" 
    messages+=[
            {"role": "user", "content": test_question}
          ]
    return messages

def zero(sys, problem, stage=1, exp=""):
    if sys !="":
        
        messages=[{"role": "system", "content": sys}]
    else:
        messages=[]
    test_question= "Q: " + problem + "\n" + "A: The answer is"
    messages+=[
            {"role": "user", "content": test_question}
          ]
    return messages

def equiv(model_output, answer, unit):
    model_output=model_output.replace(',', '')
    try:
        first=math.isclose(float(model_output.strip()), float(answer.strip()), abs_tol=0.1)
    except:
        first=False
    try: 
        model=model_output.strip().split()[0]
        second=math.isclose(float(model), float(answer.strip()), abs_tol=0.1)
    except:
        second=False
    if first or second:
        return True
    return False

def get_eg(file):
    count=0
    problem=[]
    exp=[]
    answer=[]
    unit=[]
    with open("../dataset/original/{}_sol.json".format(file), encoding='utf-8') as json_file:
        problems=json.load(json_file)
        for problem_data in problems:
                count+=1
                if count>5:
                    break
                problem_text=problem_data["problem_text"]+" The unit of the answer is "+problem_data["unit"]+"."
                problem.append(problem_text)
                exp.append(problem_data["solution"])
                answer.append(problem_data["answer_number"])
                unit.append(problem_data["unit"])
    return problem, exp, answer,unit

def zeroCot(sys, problem, stage=1, exp=""):
    if sys !="":
        
        messages=[{"role": "system", "content": sys}]
    else:
        messages=[]
    if stage==1:
        test_question = "Q: " + problem + "\n" + "A: Let's think step by step."
        
    if stage==2:
        test_question = "Q: " + problem + "\n" + "A: Let's think step by step."+exp+"Therefore, the answer is"
    messages+=[
            {"role": "user", "content": test_question}
          ]
    return messages

def equiv(model_output, answer, unit):
    model_output=model_output.replace(',', '')
    try:
        first=math.isclose(float(model_output.strip()), float(answer.strip()), abs_tol=0.1)
    except:
        first=False
    try: 
        model=model_output.strip().split()[0]
        second=math.isclose(float(model), float(answer.strip()), abs_tol=0.1)
    except:
        second=False
    if first or second:
        return True
    return False