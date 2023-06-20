import os, json, sys, time, re, math, random, datetime, argparse, requests


def log(kwargs):
    time_now = datetime.datetime.now()
    log_path = "./logs/%s/%s.jsonl"%(time_now.strftime("%Y-%m-%d"), time_now.strftime("%H"))
    if not os.path.exists(os.path.dirname(log_path)):
        os.makedirs(os.path.dirname(log_path))
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(kwargs, ensure_ascii=False) + "\n")