import requests

def bloomz_7b1_mt_call(history, prompt, system=None, lan='en'):
    message = []
    
    if system:
        if lan == 'en':
            input_history = [system, "Okay, I will play the game with you according to the rules."] + input_history
        else:
            input_history = [system, "好的，我会按照规则和你进行游戏"] + input_history
    
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
        "http://166.111.5.162:39999/api/v1/bloomz-7b1-mt/call", 
        json = {
            "messages": message,
        },
        headers = {
            "Authorization": "key-9g7Hc9kO8u2ABT6y"
        },
        timeout=50
    )
    
    if resp.status_code != 200:
        return ''
    
    output = resp.json()['result']
    
    return output

if __name__ == '__main__':
    print(bloomz_7b1_mt_call([], 'Hello'))