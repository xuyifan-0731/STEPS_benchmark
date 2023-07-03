from serpapi import api

def calling(input: dict) -> str:
    params = {
        "engine": "home_depot",
        "q": input['q'],
    }

    search = api(params)
    products = search["products"]

    s = ''
    for i in products:
        s += "The product id of product in position {} is {}. ".format(i['position'], i['product_id'])
        s += "The title of product in position {} is {}. ".format(i['position'], i['title'])
        s += "The link of product in position {} is {}. ".format(i['position'], i['link'])
        s += "The rating of product in position {} is {}. ".format(i['position'], i['rating'])
        s += "The price of product in position {} is {}. \n".format(i['position'], i['price'])
    return s