from serpapi import api, Compare


def check_product_id(data: dict, answer: str) -> float:
    params = {
        "engine": "home_depot",
        "q": data['tool_usage'][0]['input']['q'],
    }
    search = api(params)
    products = search["products"]
    for item in products:
        if (answer.find(str(item["product_id"])) != -1):
            return 1
    return 0


def check_title(data: dict, answer: str) -> float:
    params = {
        "engine": "home_depot",
        "q": data['tool_usage'][0]['input']['q'],
    }
    search = api(params)
    products = search["products"]
    for item in products:
        if (answer.find(str(item["title"])) != -1):
            return 1
    return 0


def check_link(data: dict, answer: str) -> float:
    params = {
        "engine": "home_depot",
        "q": data['tool_usage'][0]['input']['q'],
    }
    search = api(params)
    products = search["products"]
    for item in products:
        if (answer.find(str(item["link"])) != -1):
            return 1
    return 0


def check_rating(data: dict, answer: str) -> float:
    params = {
        "engine": "home_depot",
        "q": data['tool_usage'][0]['input']['q'],
    }
    search = api(params)
    products = search["products"]
    for item in products:
        if (answer.find(str(item["rating"])) != -1):
            return 1
    return 0


def check_price(data: dict, answer: str) -> float:
    params = {
        "engine": "home_depot",
        "q": data['tool_usage'][0]['input']['q'],
    }
    search = api(params)
    products = search["products"]
    for item in products:
        if (answer.find(str(item["price"])) != -1):
            return 1
    return 0
