import time
import multiprocessing as mp
import requests


def request(_):
    for i in range(10):
        requests.post("http://localhost:9998/api/v1/chatglm_6b_v2/call", json={
            "messages": [
                {"role": "user", "content": "Hello!"},
                {"role": "assistant", "content": "Hi."},
                {"role": "assistant", "content": "Introduce yourself"}
            ]
        })


def main():
    with mp.Pool(10) as pool:
        start = time.time()
        pool.map(request, range(10))
        end = time.time()
    print("Time:", end - start)


if __name__ == '__main__':
    main()
