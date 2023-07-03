from serpapi import api

def calling(input: dict):
    res = api({
        'engine': 'yelp',
        "find_desc": input["place"],
        "find_loc": input["location"],
    })
    return res['organic_results'][0][input["key"]]