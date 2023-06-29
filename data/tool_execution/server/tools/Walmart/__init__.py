from serpapi import api
import json

def calling(input: dict) -> str:
    query = input['query']
    params = {
        'engine': 'walmart',
        'query': query
    }
    res = api(params)
    return json.dumps(res['organic_results'])