from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from typing import Optional
import requests

from backend.services.spotify_service import SpotifyService
from backend.services.genius_service import GeniusService
from backend.config import SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET, SPOTIFY_REDIRECT_URI, GENIUS_ACCESS_TOKEN


app = FastAPI()
spotify_service = SpotifyService(SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET, SPOTIFY_REDIRECT_URI)
genius_service = GeniusService(GENIUS_ACCESS_TOKEN)

@app.get("/login")
def login():
    authorization_url = spotify_service.get_auth_url()
    return RedirectResponse(url=authorization_url)

@app.get("/callback")
def callback(request: Request):
    code = request.query_params.get('code')
    if code:
        token_info = spotify_service.get_access_token(code)
        top_tracks = spotify_service.get_top_tracks(token_info['access_token'])
        top_tracks_info = []
        
        for track in top_tracks['items']:
            track_info = {
                "id": track['id'],
                "album": track['album']['name'],
                "main_artist": track['artists'][0]['name'],
                "track_name": track['name'],
                "preview_url": track.get('preview_url'),
                "duration_ms": track['duration_ms']
            }
            top_tracks_info.append(track_info)
        
        return {"top_tracks": top_tracks_info}
    else:
        return {"Error": "Auth Code NOT FOUND"}

@app.get("/analyze_track/{track_id}")
def analyze_track(track_id: str, request: Request):
    # For button/direct track ID selection
    top_tracks = request.session.get("top_tracks", [])
    track = next((t for t in top_tracks if t["id"] == track_id), None)
    if not track:
        return {"error": "Track not found"}
        
    lyrics = genius_service.search_song(track["track_name"], track["main_artist"])
    if not lyrics:
        return {"error": "Lyrics not found"}
        
    return {
        "track": track,
        "lyrics": lyrics
    }

@app.post("/chat_analyze")
async def chat_analyze(request: Request):
    # For natural language track selection
    body = await request.json()
    user_message = body.get("message", "")
    top_tracks = request.session.get("top_tracks", [])
    
    # Simple pattern matching for demo - you'll replace this with LangChain
    track = None
    if "#" in user_message:
        # Handle "track #3" style references
        try:
            track_num = int(user_message.split("#")[1].split()[0]) - 1
            if 0 <= track_num < len(top_tracks):
                track = top_tracks[track_num]
        except:
            pass
    else:
        # Try to match by track name
        track = next((t for t in top_tracks if t["track_name"].lower() in user_message.lower()), None)
    
    if not track:
        return {"error": "Could not identify which track to analyze"}
        
    lyrics = genius_service.search_song(track["track_name"], track["main_artist"])
    if not lyrics:
        return {"error": "Lyrics not found"}
        
    return {
        "track": track,
        "lyrics": lyrics
    }

@app.get("/test_lyrics")
def test_lyrics():
    # Test with a known song
    lyrics = genius_service.search_song("Bohemian Rhapsody", "Queen")
    return {"lyrics": lyrics}

@app.get("/debug_genius")
def debug_genius():
    search_url = f"{genius_service.base_url}/search"
    params = {
        "q": "Bohemian Rhapsody Queen"
    }
    response = requests.get(search_url, headers=genius_service.headers, params=params)
    return {
        "status_code": response.status_code,
        "headers": dict(response.headers),
        "response": response.json() if response.status_code == 200 else None
    }
    
