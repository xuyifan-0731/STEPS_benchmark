from serpapi import api
import json

def calling(input: dict) -> str:
    query = input['query']
    params = {
        'engine': 'youtube',
        'search_query': query
    }
    res = api(params)
    return json.dumps(res['video_results'])
