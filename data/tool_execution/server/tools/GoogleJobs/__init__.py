from serpapi import api

def calling(input: dict):
    res = api({
        'engine': 'google_jobs',
        'q': input["place"]+" "+input["job"]
    })
    res = res['jobs_results']
    res2 = []
    for r in res:
        res2.append(r[input["key"]])
    str = ""
    for r in res2:
        str+=r.strip(' ')
        str+=","
    str=str.strip(",")
    str+='.'
    return str
