import requests


if __name__ == '__main__':
    print(requests.post("http://localhost:9999/api/v1/internlm/call", json={
        "messages": [
            {"role": "user", "content": "Hello!"},
            {"role": "assistant", "content": "Hi."},
            {"role": "user", "content": "Introduce yourself"}
        ]
    }).json())
