from serpapi import api

def calling(input: dict):
    res = api({
        'engine': 'google_finance',
        'q': input["stock"]
    })
    if input["key"]=="price_movement":
        return res["summary"]["price_movement"]["movement"]
    else:
        return res["summary"][input["key"]]
