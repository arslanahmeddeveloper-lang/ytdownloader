import asyncio
from backend.downloader import get_video_info

url = "https://youtu.be/uA_mdqwQ4tw"
info = get_video_info(url)
print("Formats length:", len(info['formats']))
for f in info['formats']:
    print(f)
