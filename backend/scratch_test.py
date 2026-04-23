import yt_dlp
import os

COOKIES_FILE = os.path.join(os.path.dirname(__file__), "cookies.txt")

for clients in [
    ['ios'], ['android'], ['web'], ['tv'], ['mweb'], ['web', 'tv'], ['android_vr']
]:
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'extract_flat': False,
        'skip_download': True,
        'extractor_args': {'youtube': {'player_client': clients}}
    }
    if os.path.exists(COOKIES_FILE):
        ydl_opts['cookiefile'] = COOKIES_FILE
        
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info("https://www.youtube.com/watch?v=7uS-hAuJbNY", download=False)
            formats = [f for f in info.get('formats', []) if f.get('vcodec') != 'none']
            print(f"Clients {clients}: Found {len(formats)} video formats")
    except Exception as e:
        print(f"Clients {clients}: Failed - {e}")
