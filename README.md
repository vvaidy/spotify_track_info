# Spotify Track Info Downloader

A command-line tool to download Spotify track audio features for specified track IDs. This tool uses the Spotify Web API to fetch track information and audio features.

## Features

- Beautiful command-line interface with rich formatting
- Secure OAuth authentication with Spotify
- Download track information and audio features for up to 100 tracks
- Support for input via file or command line arguments
- Progress indicators and debug logging
- Saves track information in JSON format
- Automatic file renaming to prevent overwriting

## Prerequisites

- Python 3.7 or higher
- Spotify Developer Account
- Spotify API credentials (Client ID and Client Secret)

## Setup

1. First, clone this repository:
```bash
git clone <repository-url>
cd <repository-directory>
```

2. Install the required dependencies:
```bash
pip install -r requirements.txt
```

3. Create a Spotify Developer Account and set up your application:
   - Go to [Spotify Developer Dashboard](https://developer.spotify.com/dashboard)
   - Create a new application
   - Note down your Client ID and Client Secret
   - Add `http://localhost:8888/callback` to your application's Redirect URIs in the app settings

4. Create a `.env` file in the project root with your Spotify credentials:
```
SPOTIFY_CLIENT_ID=your_client_id_here
SPOTIFY_CLIENT_SECRET=your_client_secret_here
SPOTIFY_REDIRECT_URI=http://localhost:8888/callback
```

## Usage

You can provide track IDs either via a file or directly on the command line:

1. Using a file (one track ID per line):
```bash
python spotify_downloader.py track_ids.txt
```

2. Using command line arguments (comma-separated):
```bash
python spotify_downloader.py "track_id1,track_id2,track_id3"
```

The first time you run the script, it will:
1. Open your default web browser for Spotify authentication
2. Ask you to log in to your Spotify account (if not already logged in)
3. Request permission to access your account
4. Redirect you back to the application

After authentication, the script will create a JSON file with the results:
- If using a file input, the output will be `<input_filename>.json`
- If using command line input, the output will be `trackinfo.json`
- If the output file already exists, it will be renamed with a number suffix

## Output Format

The downloaded JSON files will have the following structure:

** NOTE: Spotify has deleted the audio_features and so we no longer havea way to
populate that data ... bummer! **

```json
{
  "track_count": 2,
  "tracks": [
    {
      "track_id": "spotify_track_id1",
      "status": "retrieved",
      "name": "Track Name",
      "artists": ["Artist 1", "Artist 2"],
      "audio_features": {
        "danceability": 0.735,
        "energy": 0.578,
        "key": 5,
        "loudness": -11.84,
        "mode": 0,
        "speechiness": 0.0461,
        "acousticness": 0.514,
        "instrumentalness": 0.0902,
        "liveness": 0.159,
        "valence": 0.624,
        "tempo": 98.002,
        "duration_ms": 255349,
        "time_signature": 4
      }
    },
    {
      "track_id": "invalid_track_id",
      "status": "failed",
      "error": "Error message here"
    }
  ]
}
```

## Authentication

The script uses Spotify's OAuth 2.0 Authorization Code flow for authentication, which:
- Is more secure than using API keys
- Allows access to user-specific data
- Provides refresh token functionality
- Caches tokens locally for future use

The first time you run the script, it will open your browser for authentication. After that, it will use the cached tokens unless they expire.

## Limitations

- Maximum of 100 track IDs can be processed at once
- Requires valid Spotify track IDs
- Requires user authentication via web browser

## Debug Mode

Debug mode is enabled by default. To disable debug logging, set `DEBUG = False` in the script.

## Error Handling

The script includes comprehensive error handling:
- Invalid track IDs are marked as "failed" in the output
- Successful tracks are marked as "retrieved"
- Each failed track includes an error message
- The script will still complete and save results even if some tracks fail

## License

This project is licensed under the MIT License - see the LICENSE file for details. 

## TODO AND FORTHCOMING

Adding analysis of BPM and Danceability scores courtesy of the wonderful folks at [GetSongBPM.com](https://www.GetSongBPM.com)

They generously offer free API Keys at https://getsongbpm.com/api on request!

