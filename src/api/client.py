import logging
import requests

logger = logging.getLogger('weather-app.api')

class ApiClient:
    def __init__(self, api_key, base_url):
        self.api_key = api_key
        self.base_url = base_url

    def fetch_data(self, endpoint):
        url = f"{self.base_url}/{endpoint}&key={self.api_key}&contentType=json"
        logger.info("Fetching weather data from API for endpoint=%s", endpoint.split('?')[0])
        response = requests.get(url)
        logger.info("API response status=%s for endpoint=%s", response.status_code, endpoint.split('?')[0])
        response.raise_for_status()
        return response.json()
