import os
import json
import sys
import argparse
from typing import Dict, List, Optional
from pathlib import Path
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich import print as rprint
from dotenv import load_dotenv
import spotipy
from spotipy.oauth2 import SpotifyOAuth

# Configuration Constants
CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID", "")
CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET", "")
REDIRECT_URI = os.getenv("SPOTIFY_REDIRECT_URI", "http://localhost:8888/callback")
# Updated scope to include recommendations access
SCOPE = "playlist-read-private playlist-read-collaborative user-read-private user-top-read"
DEBUG = True
MAX_TRACKS = 100

# Initialize Rich console
console = Console()

def debug_print(message: str, error: Optional[Exception] = None) -> None:
    """Print debug messages if DEBUG is enabled."""
    if DEBUG:
        if error:
            console.print(f"[bold red]DEBUG ERROR: {message}[/bold red]")
            console.print(f"[red]Error details: {str(error)}[/red]")
        else:
            console.print(f"[bold blue]DEBUG: {message}[/bold blue]")

def setup_spotify() -> spotipy.Spotify:
    """Set up and return authenticated Spotify client using Authorization Code flow."""
    try:
        load_dotenv()
        
        if not all([CLIENT_ID, CLIENT_SECRET, REDIRECT_URI]):
            raise ValueError("Spotify credentials not found in environment variables")
        
        auth_manager = SpotifyOAuth(
            client_id=CLIENT_ID,
            client_secret=CLIENT_SECRET,
            redirect_uri=REDIRECT_URI,
            scope=SCOPE,
            open_browser=True,
            cache_path=".spotify_cache"
        )
        
        # Get token (this will automatically handle the OAuth flow if needed)
        token_info = auth_manager.get_cached_token()
        if not token_info:
            debug_print("No cached token found, starting authentication flow...")
            token_info = auth_manager.get_access_token(as_dict=True)
        elif auth_manager.is_token_expired(token_info):
            debug_print("Cached token is expired, refreshing...")
            token_info = auth_manager.refresh_access_token(token_info['refresh_token'])
        
        spotify = spotipy.Spotify(auth_manager=auth_manager)
        
        # Verify authentication
        user_info = spotify.current_user()
        debug_print(f"Successfully authenticated as user: {user_info['id']}")
        
        return spotify
    
    except Exception as e:
        debug_print("Failed to set up Spotify client", e)
        raise

def read_track_ids(input_source: str) -> List[str]:
    """Read track IDs from file or command line argument."""
    track_ids = []
    
    if os.path.isfile(input_source):
        debug_print(f"Reading track IDs from file: {input_source}")
        with open(input_source, 'r', encoding='utf-8') as f:
            track_ids = [line.strip() for line in f if line.strip()]
    else:
        debug_print("Reading track IDs from command line argument")
        track_ids = [id.strip() for id in input_source.split(',') if id.strip()]
    
    if len(track_ids) > MAX_TRACKS:
        raise ValueError(f"Too many track IDs provided. Maximum allowed: {MAX_TRACKS}")
    
    return track_ids

def get_output_filename(input_source: str) -> str:
    """Determine output filename based on input source."""
    if os.path.isfile(input_source):
        base = Path(input_source).stem
        output_file = f"{base}.json"
    else:
        output_file = "trackinfo.json"
    
    # Handle existing file
    if os.path.exists(output_file):
        counter = 1
        while True:
            new_name = f"{Path(output_file).stem}_{counter}.json"
            if not os.path.exists(new_name):
                os.rename(output_file, new_name)
                debug_print(f"Renamed existing file to {new_name}")
                break
            counter += 1
    
    return output_file

def get_similar_tracks(spotify: spotipy.Spotify, track_info: Dict) -> List[Dict]:
    """Get similar tracks using artist top tracks and album tracks."""
    similar_tracks = []
    
    try:
        # Get primary artist's ID
        primary_artist_id = track_info['artists'][0]['id']
        debug_print(f"Getting top tracks for artist: {primary_artist_id}")
        
        # Get artist's top tracks
        top_tracks = spotify.artist_top_tracks(primary_artist_id, country='US')
        if top_tracks and 'tracks' in top_tracks:
            for track in top_tracks['tracks'][:3]:  # Get top 3 tracks
                if track['id'] != track_info['id']:  # Don't include the original track
                    similar_tracks.append({
                        'id': track['id'],
                        'name': track['name'],
                        'artists': [artist['name'] for artist in track['artists']],
                        'popularity': track['popularity'],
                        'preview_url': track.get('preview_url'),
                        'external_urls': track['external_urls'],
                        'source': 'artist_top_tracks'
                    })
        
        # Get tracks from the same album
        album_id = track_info['album']['id']
        debug_print(f"Getting tracks from album: {album_id}")
        
        album_tracks = spotify.album_tracks(album_id)
        if album_tracks and 'items' in album_tracks:
            for track in album_tracks['items'][:2]:  # Get up to 2 tracks
                if track['id'] != track_info['id']:  # Don't include the original track
                    track_full = spotify.track(track['id'])  # Get full track info for popularity
                    similar_tracks.append({
                        'id': track['id'],
                        'name': track['name'],
                        'artists': [artist['name'] for artist in track['artists']],
                        'popularity': track_full.get('popularity', 0),
                        'preview_url': track.get('preview_url'),
                        'external_urls': track['external_urls'],
                        'source': 'same_album'
                    })
        
        # Get tracks from artist's other albums
        debug_print(f"Getting other albums from artist: {primary_artist_id}")
        albums = spotify.artist_albums(
            primary_artist_id,
            album_type='album,single',
            limit=2
        )
        
        if albums and 'items' in albums:
            for album in albums['items']:
                if album['id'] != album_id:  # Don't include the same album
                    album_tracks = spotify.album_tracks(album['id'])
                    if album_tracks and 'items' in album_tracks:
                        track = album_tracks['items'][0]  # Get first track from each album
                        track_full = spotify.track(track['id'])  # Get full track info for popularity
                        similar_tracks.append({
                            'id': track['id'],
                            'name': track['name'],
                            'artists': [artist['name'] for artist in track['artists']],
                            'popularity': track_full.get('popularity', 0),
                            'preview_url': track.get('preview_url'),
                            'external_urls': track['external_urls'],
                            'source': 'other_album'
                        })
        
        return similar_tracks
    
    except Exception as e:
        debug_print("Failed to get similar tracks", e)
        return []

def get_track_info(spotify: spotipy.Spotify, track_ids: List[str]) -> List[Dict]:
    """Get detailed track information and similar tracks."""
    results = []
    
    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("[cyan]Fetching track information...", total=len(track_ids))
            
            for track_id in track_ids:
                try:
                    debug_print(f"Fetching track info for {track_id}")
                    # Clean track ID
                    clean_track_id = track_id.split(':')[-1] if ':' in track_id else track_id
                    track_info = spotify.track(clean_track_id, market='US')
                    debug_print(f"Track info: {track_info}")

                    # Get the actual track ID (handle linked tracks)
                    actual_track_id = track_info.get('id')
                    debug_print(f"Using actual track ID: {actual_track_id}")

                    # Build track information
                    result = {
                        'track_id': track_id,
                        'actual_track_id': actual_track_id,
                        'status': 'retrieved',
                        'name': track_info['name'],
                        'artists': [artist['name'] for artist in track_info['artists']],
                        'album': {
                            'name': track_info['album']['name'],
                            'release_date': track_info['album']['release_date'],
                            'total_tracks': track_info['album']['total_tracks'],
                            'images': track_info['album']['images']
                        },
                        'track_details': {
                            'duration_ms': track_info['duration_ms'],
                            'explicit': track_info['explicit'],
                            'popularity': track_info['popularity'],
                            'preview_url': track_info['preview_url'],
                            'track_number': track_info['track_number'],
                            'is_playable': track_info.get('is_playable', True),
                            'external_ids': track_info.get('external_ids', {}),
                            'disc_number': track_info.get('disc_number', 1)
                        },
                        'external_urls': track_info['external_urls']
                    }

                    # Get similar tracks using alternative methods
                    similar_tracks = get_similar_tracks(spotify, track_info)
                    result['similar_tracks'] = similar_tracks
                    result['similar_tracks_count'] = len(similar_tracks)
                        
                except Exception as e:
                    debug_print(f"Failed to get info for track {track_id}", e)
                    result = {
                        'track_id': track_id,
                        'status': 'failed',
                        'error': str(e)
                    }
                
                results.append(result)
                progress.update(task, advance=1)
    
    except Exception as e:
        debug_print("Failed to get track information", e)
        raise
    
    return results

def main():
    """Main function to run the Spotify track info downloader."""
    parser = argparse.ArgumentParser(description="Download Spotify track information and recommendations")
    parser.add_argument("input", help="Either a file containing track IDs (one per line) or comma-separated track IDs")
    args = parser.parse_args()
    
    console.print("[bold magenta]Spotify Track Info Downloader[/bold magenta]")
    console.print("=" * 50)
    
    try:
        # Set up Spotify client
        spotify = setup_spotify()
        
        # Read track IDs
        track_ids = read_track_ids(args.input)
        debug_print(f"Processing {len(track_ids)} track IDs")
        
        # Get output filename
        output_file = get_output_filename(args.input)
        debug_print(f"Output file: {output_file}")
        
        # Get track information
        results = get_track_info(spotify, track_ids)
        
        # Save results
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump({
                'track_count': len(results),
                'tracks': results
            }, f, indent=2, ensure_ascii=False)
        
        console.print(f"[green]✓[/green] Successfully saved track information to {output_file}")
        return 0
    
    except Exception as e:
        console.print("[bold red]An error occurred:[/bold red]")
        console.print(f"[red]{str(e)}[/red]")
        return 1

if __name__ == "__main__":
    exit(main()) 