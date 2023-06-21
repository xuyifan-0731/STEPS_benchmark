import time
import json
import requests

def gpt4_call(history, prompt, system=None, lan='en'):
    message = []
    if system:
        message.append({
            "role": "system",
            "content": system
        })
    
    for ix, chat in enumerate(history):
        message.append({
            "role": "user",
            "content": chat[0]
        })
        message.append({
            "role": "assistant",
            "content": chat[1]
        })
    
    message.append({
        "role": "user",
        "content": prompt
    })
    
    try:
        resp = requests.post(
            "http://40.74.217.35:10010/api/openai/chat-completion", 
            json = {
                "model": "gpt-4",
                "messages": message,
            },
            timeout=200
        )
    except:
        return ''
    
    if resp.status_code != 200:
        return ''
    
    output = resp.json()["choices"][0]["message"]["content"]
    
    return output


if __name__ == "__main__":
    print(gpt4_call([], 'hello'))

