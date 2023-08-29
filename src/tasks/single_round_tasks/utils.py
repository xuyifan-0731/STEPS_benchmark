import re

def find_first_capital_letter(item):
    try:
        text = item["text"]
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
    # print(item["text"])
    print(item["raw_answer"][-50:])
    print(matches)
    
    if matches:
        return matches[-1], False
    else:
        return item, True