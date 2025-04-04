from fastapi import FastAPI, Request, Response
from fastapi.responses import RedirectResponse, JSONResponse, HTMLResponse
from typing import Optional
import requests
from starlette.middleware.sessions import SessionMiddleware
import secrets
import json

from backend.services.spotify_service import SpotifyService
from backend.services.genius_service import GeniusService
from backend.config import (
    SPOTIFY_CLIENT_ID, 
    SPOTIFY_CLIENT_SECRET, 
    SPOTIFY_REDIRECT_URI, 
    GENIUS_ACCESS_TOKEN
)

app = FastAPI()
# Add session middleware
app.add_middleware(
    SessionMiddleware,
    secret_key=secrets.token_urlsafe(32),
    session_cookie="spotify_lyrics_session",
    same_site="lax",
    https_only=False,  # Allow cookies over HTTP in development
    max_age=3600,  # 1 hour
    path="/",  # Make cookie available for all paths
    domain=None  # Allow cookie for any domain in development
)

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
        
        # Debug session data size
        session_data = json.dumps(top_tracks_info)
        print("Data size in bytes:", len(session_data.encode("utf-8")))
        
        # Return HTML that will store data in localStorage and redirect
        return HTMLResponse(content=f"""
        <html>
            <head>
                <title>Analyzing Track</title>
            </head>
            <body>
                <h1>Analyzing Track</h1>
                <p>Redirecting to analysis...</p>
                <script>
                    // Store tracks in localStorage
                    localStorage.setItem('top_tracks', JSON.stringify({json.dumps(top_tracks_info)}));
                    
                    // Wait for data to be stored
                    setTimeout(() => {{
                        window.location.href = '/analyze_track/{top_tracks_info[0]["id"]}';
                    }}, 1000);
                </script>
            </body>
        </html>
        """)
    else:
        return {"Error": "Auth Code NOT FOUND"}

@app.get("/analyze_track/{track_id}")
def analyze_track(track_id: str, request: Request):
    print("ANALYZE: Looking for track_id:", track_id)
    
    # Return HTML that will read from localStorage
    return HTMLResponse(content=f"""
    <html>
        <head>
            <title>Analyzing Track</title>
            <style>
                .track-list {{
                    margin: 20px 0;
                    padding: 0;
                    list-style: none;
                }}
                .track-item {{
                    padding: 10px;
                    margin: 5px 0;
                    border: 1px solid #ccc;
                    border-radius: 4px;
                    cursor: pointer;
                }}
                .track-item:hover {{
                    background-color: #f0f0f0;
                }}
                .no-lyrics {{
                    color: #666;
                    font-style: italic;
                }}
            </style>
        </head>
        <body>
            <h1>Analyzing Track</h1>
            <p>Loading track data...</p>
            <div id="debug"></div>
            <div id="result"></div>
            <div id="track-selector" style="display: none;">
                <h2>Select a different track to analyze:</h2>
                <ul class="track-list" id="track-list"></ul>
            </div>
            <script>
                // Get tracks from localStorage
                const tracks = JSON.parse(localStorage.getItem('top_tracks') || '[]');
                console.log('Tracks in localStorage:', tracks);
                document.getElementById('debug').innerHTML += `<p>Tracks found: ${{tracks.length}}</p>`;
                
                const track = tracks.find(t => t.id === '{track_id}');
                console.log('Found track:', track);
                document.getElementById('debug').innerHTML += `<p>Track found: ${{!!track}}</p>`;
                
                if (!track) {{
                    document.getElementById('result').innerHTML = 'Track not found';
                }} else {{
                    // Fetch lyrics and display result
                    fetch(`/api/analyze_track/{track_id}`, {{
                        method: 'POST',
                        headers: {{
                            'Content-Type': 'application/json'
                        }},
                        body: JSON.stringify({{ track }})
                    }})
                        .then(response => {{
                            console.log('Response status:', response.status);
                            return response.json();
                        }})
                        .then(data => {{
                            console.log('Response data:', data);
                            if (data.error) {{
                                document.getElementById('result').innerHTML = `Error: ${{data.error}}`;
                            }} else {{
                                document.getElementById('result').innerHTML = `
                                    <h2>${{track.track_name}} by ${{track.main_artist}}</h2>
                                    <p>Album: ${{track.album}}</p>
                                    <p>Lyrics: ${{data.lyrics}}</p>
                                `;
                                
                                // If lyrics are not available, show track selector
                                if (data.lyrics.includes('Coming soon') || data.lyrics.includes('No lyrics found')) {{
                                    document.getElementById('result').innerHTML += '<p class="no-lyrics">Lyrics not available for this track. Please select another track:</p>';
                                    document.getElementById('track-selector').style.display = 'block';
                                    
                                    // Populate track list
                                    const trackList = document.getElementById('track-list');
                                    tracks.forEach(t => {{
                                        const li = document.createElement('li');
                                        li.className = 'track-item';
                                        li.innerHTML = `${{t.track_name}} by ${{t.main_artist}}`;
                                        li.onclick = () => window.location.href = `/analyze_track/${{t.id}}`;
                                        trackList.appendChild(li);
                                    }});
                                }}
                            }}
                        }})
                        .catch(error => {{
                            console.error('Error:', error);
                            document.getElementById('result').innerHTML = 'Error analyzing track';
                            document.getElementById('debug').innerHTML += `<p>Error: ${{error.message}}</p>`;
                        }});
                }}
            </script>
        </body>
    </html>
    """)

@app.post("/api/analyze_track/{track_id}")
async def api_analyze_track(track_id: str, request: Request):
    # Get track info from request body
    body = await request.json()
    track = body.get("track")
    
    if not track:
        return {"error": "Track information not provided"}
        
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

@app.get("/test_session")
def test_session(request: Request):
    # Try to get a number from session, if not exists, set it to 1
    number = request.session.get("test_number", 1)
    # Store it back in session
    request.session["test_number"] = number + 1
    return {"number": number, "session_keys": list(request.session.keys())}
    
