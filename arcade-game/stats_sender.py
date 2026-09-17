import requests


class StatsSender:
    def __init__(self, server_url="http://127.0.0.1:8080"):
        self.url = server_url

    def send(self, data: dict):
        response = requests.post(f"{self.url}/api/update-stats", json=data)
        if response.status_code == 200:
            result = response.json()
            return result
        else:
            return None

    def get(self, username):
        response = requests.get(f"{self.url}/api/user/{username}")
        if response.status_code == 200:
            result = response.json()
            return result
        else:
            return None