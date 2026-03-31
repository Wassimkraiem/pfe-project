import requests


class VideoSearchSDK:
    def __init__(self, base_url: str, api_key: str = None):
        """
        Initialize the SDK with the base URL of the API and optional API key.
        :param base_url: The base URL of the running Flask API (e.g., http://http://localhost:5000)
        :param api_key: The API key for authentication (optional)
        """
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key

    def _headers(self):
        headers = {}
        if self.api_key:
            headers["X-API-KEY"] = self.api_key
        return headers

    def create_video(self, video_data: dict) -> dict:
        """
        Create a new video document.
        :param video_data: Dictionary containing video details.
        :return: API response as a dictionary.
        """
        url = f"{self.base_url}/api/videos/"
        try:
            response = requests.post(url, json=video_data, headers=self._headers())
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            return {"error": str(e), "details": getattr(e.response, "text", None)}

    def get_video(self, video_id: str) -> dict:
        """
        Retrieve a video document by its ID.
        :param video_id: The ID of the video to retrieve.
        :return: API response as a dictionary.
        """
        url = f"{self.base_url}/api/videos/query"
        payload = {"video_id": video_id}
        try:
            response = requests.post(url, json=payload, headers=self._headers())
            response.raise_for_status()
            data = response.json()
            # Assuming the API returns a list of videos in 'data' or similar
            if data:
                return data
            return {"error": "Not found", "details": data}
        except requests.RequestException as e:
            return {"error": str(e), "details": getattr(e.response, "text", None)}

    def search_videos(self, query_params: dict) -> dict:
        """
        Search for videos using query parameters.
        :param query_params: Dictionary of search parameters.
        :return: API response as a dictionary.
        """
        url = f"{self.base_url}/api/videos/query"
        try:
            response = requests.post(url, json=query_params, headers=self._headers())
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            return {"error": str(e), "details": getattr(e.response, "text", None)}

    def delete_video(self, video_id: str) -> dict:
        """
        Delete a video document by its ID.
        :param video_id: The ID of the video to delete.
        :return: API response as a dictionary.
        """
        url = f"{self.base_url}/api/videos/"
        payload = {"video_id": video_id}
        try:
            response = requests.delete(url, json=payload, headers=self._headers())
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            return {"error": str(e), "details": getattr(e.response, "text", None)}
