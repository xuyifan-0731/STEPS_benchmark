import requests
import json

url = "http://localhost:9999/api/v1"

payload = json.dumps({})
headers = {
    'Authorization': 'key-m5VLjfeG6zjQwaG4',
    'Content-Type': 'application/json'
}

response = requests.request("POST", url, headers=headers, data=payload)

print(response.text)
