import re

def find_first_capital_letter(item):
    try:
        text = item["raw_answer"]
        choices = item["choices"]
        letter_set = [chr(65+i) for i in range(len(choices))] # legal choices
        for c in text.replace(" ","")[0]:
            if c in letter_set:
                return c, False
        return item, True
    except:
        return item, True
    
def extract_text_inside_brackets(item):
    matches = re.findall(r'\{(.*?)\}', item["raw_answer"])    
    if matches:
        return matches[-1], False
    else:
        return item, True
    

def extract_text_inside_brackets_MUL(item):

    matches = re.findall(r'\{(.*?)\}', item["raw_answer"])
    last_line = item["raw_answer"].strip().split('\n')[-1]

    option_range = [chr(65 + i) for i in range(len(item['choices']))]
    option_str = "".join(option_range)

    if matches:
        last_match = matches[-1].replace(" ", "").replace("[", "").replace("]", "")
        if len(last_match) > 0 and last_match[0] in option_str:
            return last_match[0], False

    last_line_match = re.search(r'答案选项是\s*([' + option_str + '])', last_line.replace(" ",""))
    if last_line_match and last_line_match.group(1) in option_str:
        return last_line_match.group(1), False
    
    last_line_match = re.search(r'The choice is therefore\s*([' + option_str + '])', last_line.replace(" ",""))
    if last_line_match and last_line_match.group(1) in option_str:
        return last_line_match.group(1), False
    
    return item, True

def extract_text_QA(item):
    text = item["raw_answer"].strip()
    pattern = r'答案是(.+?)(。|$)'
    matches =  re.findall(pattern, text)
    if matches:
        return matches[-1][0], False
    pattern = r'The answer is therefore(.+?)(。|$)'
    matches =  re.findall(pattern, text)
    if matches:
        return matches[-1][0], False
    #last_line_match = re.search(r'The choice is therefore\s*([' + option_str + '])', last_line.replace(" ",""))
    #if last_line_match and last_line_match.group(1) in option_str:
        #return last_line_match.group(1), False
    
    return item, True