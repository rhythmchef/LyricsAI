import requests
from typing import Optional
from backend.config import GENIUS_ACCESS_TOKEN
from bs4 import BeautifulSoup

class GeniusService:
    def __init__(self, access_token: str):
        self.access_token = access_token
        self.base_url = "https://api.genius.com"
        self.headers = {"Authorization": f"Bearer {access_token}"}

    def search_song(self, track_name: str, artist_name: str) -> Optional[str]:
        search_url = f"{self.base_url}/search"
        params = {
            "q": f"{track_name} {artist_name}"
        }
        
        response = requests.get(search_url, headers=self.headers, params=params)
        if response.status_code != 200:
            return None

        hits = response.json()["response"]["hits"]
        if not hits:
            return None

        # Get the first hit's lyrics URL
        song_url = hits[0]["result"]["url"]
        print(f"Fetching lyrics from: {song_url}")
        return self._scrape_lyrics(song_url)

    def _scrape_lyrics(self, song_url: str) -> Optional[str]:
        """
        Scrape lyrics from Genius webpage using BeautifulSoup
        """
        try:
            response = requests.get(song_url)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Try different possible selectors for lyrics
            lyrics_div = None
            selectors = [
                '[data-lyrics-container="true"]',  # Primary container
                'div[class^="Lyrics__Container"]',  # New Genius format
                '.lyrics',  # Old format
                '[class*="lyrics"]'  # Generic lyrics class
            ]
            
            for selector in selectors:
                lyrics_divs = soup.select(selector)  # Get all matching containers
                if lyrics_divs:
                    print(f"Found {len(lyrics_divs)} lyrics containers with selector: {selector}")
                    # Combine all lyrics containers
                    lyrics = '\n'.join(div.get_text(separator='\n').strip() for div in lyrics_divs)
                    if lyrics:
                        print(f"Lyrics length: {len(lyrics)} characters")
                        return lyrics
            
            print("No lyrics found with any selector")
            return None
            
        except Exception as e:
            print(f"Error scraping lyrics: {e}")
            return None