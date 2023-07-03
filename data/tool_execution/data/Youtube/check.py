import json
from serpapi import Compare, api

data = {
    "query": "What's the link for youtube vedio LB Quartet - All The Things You Are (Jerome Kern)?",
    "additional_information": "Location of the user: Beijing\nCurrent Time: 2023-05-23 10:10:00",
    "q": "LB Quartet - All The Things You Are (Jerome Kern)",
    "key": "link",
    "tool_usage": [
        {
            "tool": "youtube",
            "input": {
                    "query": "LB Quartet - All The Things You Are (Jerome Kern)"
            }
        }
    ],
    "reasoning": "check_problem_exact"
}


def check_problem_exact(data: dict, answer: str) -> float:
    params = {
        'engine': 'youtube',
        'search_query': data['q']
    }
    res = api(params)
    return Compare.exact(res['video_results'][0][data['key']], answer)


def check_problem_f1(data: dict, answer: str) -> float:
    params = {
        'engine': 'youtube',
        'search_query': data['q']
    }
    res = api(params)
    return Compare.fmeasure(res['video_results'][0][data['key']], answer)
