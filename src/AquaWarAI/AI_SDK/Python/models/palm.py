import requests
import json

def palm_call(history, query, system=None, lan='en'):
    message = []
    input_history = [item for dialogue in history for item in dialogue]
    prompt = ''
    
    if system:
        prompt += system + '\n\n'
    
    chat_round = 1
    for ix, dialogue in enumerate(input_history):
        if ix % 2 == 0:
            prompt += f'## Round {chat_round} ##\nUser: {dialogue}\n\n'
        else:
            prompt += f'Assistant: {dialogue}\n\n'
            chat_round += 1
    
    prompt += f'## Round {chat_round} ##\nUser: {query}\n\nAssistant: '
    
    url = "http://40.74.217.35:10004/completion"
    
    payload = json.dumps({
        "model": "models/text-bison-001",
        "prompt": prompt,
        "temperature": 0.7,
        "max_output_tokens": 1024,
    })
    
    headers = {
        'Content-Type': 'application/json'
    }
    
    response = requests.request("POST", url, headers=headers, data=payload, timeout=50)
    
    if response.status_code != 200:
        return ''
    
    return response.text

if __name__ == '__main__':
    import time
    t = time.time()
    print(palm_call([], 'hello'))
    print(time.time() - t)