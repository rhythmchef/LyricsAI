import json
import requests
import secrets
from requests.auth import HTTPBasicAuth
from backend.config import SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET, SPOTIFY_REDIRECT_URI

class SpotifyService:
    def __init__(self, client_id, client_secret, redirect_uri):
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.access_token = None

    def get_auth_url(self):
        auth_url = 'https://accounts.spotify.com/authorize'
        state = secrets.token_urlsafe(16)
        params = {
            'client_id': self.client_id,
            'response_type': 'code',
            'redirect_uri': self.redirect_uri,
            'state': state,
            'scope': 'user-top-read playlist-read-private user-library-read user-follow-read'
        }
        request_url = requests.Request('GET', auth_url, params=params).prepare().url
        return request_url

    def get_access_token(self, authorization_code):
        token_url = 'https://accounts.spotify.com/api/token'
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        data = {
            'grant_type': 'authorization_code',
            'code': authorization_code,
            'redirect_uri': self.redirect_uri,
            'client_id': self.client_id,
            'client_secret': self.client_secret
        }
        response = requests.post(token_url, headers=headers, data=data)
        if response.status_code == 200:
            token_info = response.json()
            print("token info: ", json.dumps(token_info, indent=4))  # Pretty print the token info
            return token_info
        else:
            response.raise_for_status()


    def get_top_tracks(self, access_token):
        url = "https://api.spotify.com/v1/me/top/tracks"
        headers = {"Authorization": f"Bearer {access_token}"}
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            return response.json()
        return {"error": response.json()}