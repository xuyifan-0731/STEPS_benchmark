import requests

def chatgpt_call(history, prompt, system=None, lan='en'):
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
    
    resp = requests.post(
        "http://40.74.217.35:10001/api/openai/chat-completion", 
        json = {
            "model": "gpt-3.5-turbo",
            "messages": message,
            #"tempareture": 0.9
        },
        timeout=50
    )
    
    if resp.status_code != 200:
        return ''
    
    output = resp.json()["choices"][0]["message"]["content"]
    
    return output