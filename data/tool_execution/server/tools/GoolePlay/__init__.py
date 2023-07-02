from serpapi import api

def calling(input: dict) -> str:
    params = {
        "engine": "google_play",
        "store": input['store'],
        "hl": "en",
        "gl": "us",
    }
    print(params)
    search = api(params)
    results = search["organic_results"]
    s = ''
    for i in results:
        s += "The items in title {}: \n".format(i['title'])
        index = 0
        for j in i['items']:
            rating = '0'
            if('rating' in j):
                rating = j['rating']
            index += 1
            s += "index{}:\nproduct id: {}, ".format(index, j['product_id'])
            s += "title: {}, ".format(j['title'])
            s += "link: {}, ".format(j['link'])
            s += "rating: {}. \n".format(rating)
    return s
