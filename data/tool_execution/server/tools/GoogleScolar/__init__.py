from serpapi import api

def q1(paper, key):
    res = api({
        'engine': 'google_scholar',
        'q': paper
    })
    return res['organic_results'][0][key]

def q2(q):
    res = api({
        'engine': 'google_scholar',
        'q': q
    })
    return res['organic_results']

def calling(input: dict) -> str:
    if "paper" in input.keys():
        return q1(input["paper"],input["key"])
    else:
        return q2(input["field"])