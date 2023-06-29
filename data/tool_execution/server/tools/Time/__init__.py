# This API returns current time in %Y-%m-%d %H:%M:%S format

import datetime
def calling(input: dict) -> str:
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# if __name__ == '__main__':
#     print(calling({}))