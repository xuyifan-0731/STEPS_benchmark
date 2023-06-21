import requests

MODEL_REQUEST_URL = "http://localhost:8001/completion/stream"

def chatglm_call(history, query, system=None, lan='ch'):
    
    headers = {
        "CHARSET": "utf-8",
        "Authorization": "85577713-4c52-48bd-bf65-57112ce337d2",
        "Content-Type": "application/json"
    }
    
    input_history = [item for dialogue in history for item in dialogue]

    if system:
        if lan == 'en':
            input_history = [system, "Okay, I will play the game with you according to the rules."] + input_history
        else:
            input_history = [system, "好的，我会按照规则和你进行游戏"] + input_history

    prompt = ''
    chat_round = 1
    for ix, dialogue in enumerate(input_history):
        if ix % 2 == 0:
            prompt += f'##第 {chat_round} 轮##\n问：{dialogue}\n\n'
        else:
            prompt += f'答：{dialogue}\n\n'
            chat_round += 1
    
    prompt += f'##第 {chat_round} 轮##\n问：{query}\n\n答：'

    args = {
        "top_p": 0.7,
        "temperature": 0.5,
        "prompt": prompt,
        "seed": 42,
    }
    
    response = requests.request("POST", MODEL_REQUEST_URL, headers=headers, json=args)

    ans = []
    for line in response.iter_lines():
        ans.append(line.decode("utf-8"))
    finish_idx, meta_idx = -1, -1
    for i in range(len(ans) - 1, -1, -1):
        if ans[i] == "event: finish":
            finish_idx = i
            break
    for i in range(finish_idx + 1, len(ans)):
        if ans[i].startswith("meta: {\"model_version\":\"qa-glm-v"):
            meta_idx = i
    res = []
    for i in range(finish_idx + 2, meta_idx):
        res.append(ans[i][6:])

    return "\n".join(res)

if __name__ == '__main__':
    print(chatglm_call([], '你好'))