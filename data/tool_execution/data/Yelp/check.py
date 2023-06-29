from serpapi import api


def Format(s: str):
    res = ""
    for c in s:
        check = ""
        check += c
        if check.isalnum():
            if check.isupper():
                check = check.lower()
            res += check
    return res


def match(ans: str, s: str):
    m = len(ans)
    n = len(s)
    res = 0
    dp = [[0]*(n+1) for _ in range(m + 1)]
    for i in range(1, m+1):
        for j in range(1, n+1):
            dp[i][j] = max(dp[i][j], dp[i-1][j]-0.5)
            dp[i][j] = max(dp[i][j], dp[i][j-1]-0.5)
            if ans[i-1] == s[j-1]:
                dp[i][j] = max(dp[i][j], dp[i-1][j-1]+1)
            if res < dp[i][j]:
                res = dp[i][j]
    if res/n < 0.5:
        res = 0
    return res


def _calling(input: dict):
    res = api({
        'engine': 'yelp',
        "find_desc": input["place"],
        "find_loc": input["location"],
    })
    return res['organic_results'][0][input["key"]]


def check_yelp(data: dict, answer: str):
    ans = ""
    ans = _calling(data.get("tool_usage", {})[0].get("input"))
    ans = str(ans).split(',')
    Ans = []
    sum = 0
    mat = 0
    answer = Format(answer)
    for a0 in ans:
        a = Format(a0)
        Ans.append(a)
        sum += len(a)
        mat += match(answer, a)
    return 1.0*mat/sum
