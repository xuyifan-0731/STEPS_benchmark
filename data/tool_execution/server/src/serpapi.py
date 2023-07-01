import requests
from rouge import Rouge
import os


def api(params: dict):
    params['api_key'] = os.environ['SERPAPI_KEY']
    res = requests.get(url='https://serpapi.com/search.json', params=params)
    if res.status_code == 200:
        return res.json()
    else:
        raise Exception('error occur during request api')


class Compare:

    @staticmethod
    def exact(answer, target, strip=True):
        if strip:
            target = str(target).strip()
            answer = str(answer).strip()
        if target == answer:
            return 1
        else:
            return 0

    @staticmethod
    def cover(answer, target, strip=True):
        if strip:
            target = str(target).strip()
            answer = str(answer).strip()
        if target in answer:
            return 1
        else:
            return 0

    @staticmethod
    def fmeasure(answer, target, strip=True):
        if strip:
            target = str(target).strip()
            answer = str(answer).strip()
        if len(target) == 0 or len(answer) == 0:
            return 0
        rouge = Rouge()
        scores = rouge.get_scores(answer, target)
        return scores[0]['rouge-l']['f']

    @staticmethod
    def number_range(answer, target, allow_lower_bound=0.95, allow_upper_bound=1.05):
        try:
            target = float(target)
            answer = float(answer)
            if answer >= target * allow_lower_bound and answer <= target * allow_upper_bound:
                return 1
            else:
                return 0
        except:
            return 0


# This is an example comparison code
def example_compare(data, answer):
    res = api({
        'engine': 'google_finance',
        'q': data["stock"]
    })
    target = res['markets']['futures'][0][data["key"]]
    return Compare.number_range(answer, target)
