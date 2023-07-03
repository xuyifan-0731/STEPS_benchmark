from serpapi import api
import json

def calling(input: dict) -> str:
    query = input['query']
    params = {
        'engine': 'google_shopping',
        'q': query
    }
    res = api(params)
    return json.dumps(res['shopping_results'])

if __name__ == '__main__':
    print(calling({"query": "Black Rifle Coffee Loyalty Roast, Light Roast, Ground Coffee, 12 oz"}))