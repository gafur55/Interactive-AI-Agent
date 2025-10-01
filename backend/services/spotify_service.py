"""
Spotify API service for searching tracks, artists, playlists, and albums.
Handles authentication and result formatting.
"""

import base64
import requests
from typing import Dict, List, Optional
from config import config

class SpotifyService:
    """Service for interacting with Spotify API"""
    
    def __init__(self):
        self.client_id = config.SPOTIFY_CLIENT_ID
        self.client_secret = config.SPOTIFY_CLIENT_SECRET
        self.token_url = "https://accounts.spotify.com/api/token"
        self.search_url = "https://api.spotify.com/v1/search"
    
    def get_access_token(self) -> str:
        """
        Get Spotify API access token using client credentials flow.
        
        Returns:
            Access token string
            
        Raises:
            requests.HTTPError: If authentication fails
        """
        auth_str = f"{self.client_id}:{self.client_secret}"
        b64_auth = base64.b64encode(auth_str.encode()).decode()
        
        headers = {"Authorization": f"Basic {b64_auth}"}
        data = {"grant_type": "client_credentials"}
        
        response = requests.post(self.token_url, headers=headers, data=data)
        response.raise_for_status()
        return response.json()["access_token"]
    
    def search(
        self, 
        query: str, 
        search_type: str = "track", 
        limit: int = 3
    ) -> Dict:
        """
        Search Spotify for tracks, artists, playlists, or albums.
        
        Args:
            query: Search query string
            search_type: Type of search ("track", "artist", "playlist", "album")
            limit: Maximum number of results to return
            
        Returns:
            Raw Spotify API response dictionary
            
        Raises:
            requests.HTTPError: If search request fails
        """
        token = self.get_access_token()
        headers = {"Authorization": f"Bearer {token}"}
        params = {"q": query, "type": search_type, "limit": limit}
        
        response = requests.get(self.search_url, headers=headers, params=params)
        response.raise_for_status()
        return response.json()
    
    def format_results(self, raw_response: Dict) -> List[Dict[str, str]]:
        """
        Format raw Spotify API response into a clean list of results.
        
        Args:
            raw_response: Raw response from Spotify API
            
        Returns:
            List of dicts with 'name', 'artist', and 'url' keys
            
        Example:
            [
                {
                    "name": "Song Name",
                    "artist": "Artist Name",
                    "url": "https://open.spotify.com/track/..."
                }
            ]
        """
        results = []
        
        # Handle track results
        if "tracks" in raw_response:
            for track in raw_response["tracks"]["items"][:3]:
                url = track.get("external_urls", {}).get("spotify")
                if url:
                    results.append({
                        "name": track["name"],
                        "artist": track["artists"][0]["name"],
                        "url": url
                    })
        
        # Handle playlist results
        elif "playlists" in raw_response:
            for playlist in raw_response["playlists"]["items"][:3]:
                if not playlist:
                    continue
                url = playlist.get("external_urls", {}).get("spotify")
                if url:
                    results.append({
                        "name": playlist.get("name", "Unknown Playlist"),
                        "artist": "Playlist",
                        "url": url
                    })
        
        # Handle artist results
        elif "artists" in raw_response:
            for artist in raw_response["artists"]["items"][:3]:
                url = artist.get("external_urls", {}).get("spotify")
                if url:
                    results.append({
                        "name": artist["name"],
                        "artist": "Artist",
                        "url": url
                    })
        
        # Handle album results
        elif "albums" in raw_response:
            for album in raw_response["albums"]["items"][:3]:
                url = album.get("external_urls", {}).get("spotify")
                if url:
                    results.append({
                        "name": album["name"],
                        "artist": album["artists"][0]["name"],
                        "url": url
                    })
        
        return results

# Create a singleton instance
spotify_service = SpotifyService()