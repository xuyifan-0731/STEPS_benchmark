import requests


if __name__ == '__main__':
    model = "chatglm2-6b"
    url = "http://localhost:9998/api/v1/" + model
    requests.post(url + "/add", json={"device": "cuda:7"})
    print(requests.post(url + "/call", json={
        "messages": [
            {"role": "user", "content": "Hello!"},
            {"role": "assistant", "content": "Hi."},
            {"role": "user", "content": "Introduce yourself"}
        ]
    }).json())
