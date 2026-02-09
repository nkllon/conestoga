import requests
import sys

token = "i4vfceb3ibszxtrr3sj74xln44"
print(f"Token length: {len(token)}")

headers = {
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json"
}

try:
    resp = requests.get("https://api.cloudflare.com/client/v4/user/tokens/verify", headers=headers)
    print(f"Status: {resp.status_code}")
    print(f"Response: {resp.text}")
except Exception as e:
    print(f"Error: {e}")
