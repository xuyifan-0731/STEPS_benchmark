from serpapi import api

def calling(input: dict) -> str:
    params = {
        "engine": "ebay",
        "_nkw": input['_nkw'],
    }

    search = api(params)
    result = search["organic_results"][0]
    print(result)
    if(not('raw' in result['price'])):
        result['price']['raw'] = result['price']['to']['raw']
    if(not('seller' in result)):
        result['seller'] = {"username": 'None'}

    s = ''
    s += "product title: {}, ".format(result['title'])
    s += "product link: {}, ".format(result['link'])
    s += "condition: {}, ".format(result['condition'])
    s += "price: {}, ".format(result['price']['raw'])
    s += "seller: {}. ".format(result['seller']['username'])
    return s
