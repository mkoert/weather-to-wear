import requests

class ApiClient:
    def __init__(self, api_key, base_url):
        self.api_key = api_key
        self.base_url = base_url

    def fetch_data(self, endpoint):
        url = f"{self.base_url}/{endpoint}&key={self.api_key}&contentType=json"
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
