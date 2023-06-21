import requests

def claude_call(history, prompt, system=None, lan='en'):
    message = []
    if system:
        message.append({
            "role": "user",
            "content": system
        })
        if lan == 'en':
            message.append({
                "role": "assistant",
                "content": "Okay, I will play the game with you according to the rules."
            })
        else:
            message.append({
                "role": "assistant",
                "content": "好的，我会按照规则和你进行游戏"
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
        "http://40.74.217.35:10002/api/claude/completion", 
        json={
            "model": "claude-v1.3",
            "messages": message
        },
        timeout=50
    )
    
    if resp.status_code != 200:
        return ''
    
    output = resp.json()['completion']
    
    return output

if __name__ == "__main__":
    print(claude_call([], 'hello'))