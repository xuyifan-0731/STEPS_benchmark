import re
import datetime
import time
from serpapi import Compare


def q1(data: dict, answer: str) -> float:
    # allow 10 minutes difference
    # find %Y-%m-%d %H:%M:%S in answer
    answer_times = re.findall(r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}', answer)
    time_now = datetime.datetime.now()
    for answer in answer_times:
        # check if answer is within 10 minutes of now
        answer_time = datetime.datetime.strptime(answer, "%Y-%m-%d %H:%M:%S")
        if abs((answer_time - time_now).total_seconds()) <= 600:
            return 1
    return 0


def q2(data: dict, answer: str) -> float:
    return float(Compare.cover(answer, datetime.datetime.now().strftime("%Y-%m-%d")))


def q3(data: dict, answer: str) -> float:
    # check if answer contains 10:00 the day after tomorrow
    target_time = datetime.datetime.strptime("10:00", "%H:%M")
    the_day_after_tomorrow = datetime.datetime.now() + datetime.timedelta(days=2)
    the_day_after_tomorrow = the_day_after_tomorrow.replace(hour=target_time.hour, minute=target_time.minute)
    return float(Compare.cover(answer, the_day_after_tomorrow.strftime("%Y-%m-%d %H:%M")))


def q4(data: dict, answer: str) -> float:
    # check if answer contains 10:00 the day after tomorrow
    target_time = datetime.datetime.strptime("22:00", "%H:%M")
    the_day_after_tomorrow = datetime.datetime.now() + datetime.timedelta(days=2)
    the_day_after_tomorrow = the_day_after_tomorrow.replace(hour=target_time.hour, minute=target_time.minute)
    return float(Compare.cover(answer, the_day_after_tomorrow.strftime("%Y-%m-%d %H:%M")))


def q5(data: dict, answer: str) -> float:
    # check if answer is in 2 days with %Y-%m-%d format
    target_time = datetime.datetime.now() + datetime.timedelta(days=2)
    return float(Compare.cover(answer, target_time.strftime("%Y-%m-%d")))
