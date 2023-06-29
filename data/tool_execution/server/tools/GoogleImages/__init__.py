from serpapi import api

def q1(image, key):
    res = api({
        'engine': 'google_images',
        'q': image
    })
    return res['images_results'][0][key]

def calling(input: dict) -> str:
    return q1(input["image"],input["key"])