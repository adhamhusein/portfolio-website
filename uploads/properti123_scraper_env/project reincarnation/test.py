import requests

BOT_TOKEN = "7744183695:AAFE542XI3BkBNd9P6JWFjMA6FLVZ3-tl3c"
chat_id = "-4788488501"

url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage?chat_id={chat_id}&text=Test"

# url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates"
response = requests.get(url)
print(response.json())