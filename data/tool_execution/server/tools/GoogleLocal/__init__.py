from serpapi import api

def q1(place, key):
    res = api({
        'engine': 'google_local',
        'q': place
    })
    return res['local_results'][0][key]


def q2(location, place):
    res = api({
        'engine': 'google_local',
        'q': location + ' ' + place
    })
    return res['local_results']


def q3(location, place, key):
    res = api({
        'engine': 'google_local',
        'q': location + ' ' + place
    })
    res = res['local_results']
    res2 = []
    for r in res:
        if key in r.keys():
            res2.append(r[key])
        else:
            res2.append('NaN')
    return res2

def calling(input: dict) -> str:
    if not "location" in input.keys():
        return q1(input["place"],input["key"])
    elif not "key" in input.keys():
        return q2(input["location"],input["place"])
    else:
        return q3(input["location"],input["place"],input["key"])

if __name__ == '__main__':
    print(api({'engine': 'google_local','q': "The Hot House Tavern"})["local_results"][0])
    #print(calling({"place": "Flushing Hospital Medical Center", "key":"address"}))