import requests
import time

def fetch_json_data():
    url = "https://1xbet.com/LiveFeed/Get1x2_VZip?sports=85&count=50&lng=fr"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        log_request(url, response.status_code)
        return response.json()
    except requests.RequestException as e:
        log_request(url, "error")
        return {"error": str(e)}

def fetch_odds(sport_id=85):
    url = f"https://1xbet.com/LiveFeed/Get1x2_VZip?sports={sport_id}&count=50&lng=fr"
    try:
        response = requests.get(url)
        response.raise_for_status()
        log_request(url, response.status_code)
        return response.json()
    except requests.RequestException as e:
        log_request(url, "error")
        return {"error": str(e)}

def check_site_status():
    url = "https://1xbet.com"
    try:
        response = requests.get(url, timeout=5)
        return {"status": "online", "code": response.status_code}
    except requests.RequestException:
        return {"status": "offline", "code": None}

def log_request(endpoint, status):
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] Request to {endpoint} → Status: {status}")
