import yt_dlp

url = "https://youtu.be/uA_mdqwQ4tw"

ydl_opts = {
    'quiet': True,
    'no_warnings': True,
    'extract_flat': False,
    'skip_download': True,
}
with yt_dlp.YoutubeDL(ydl_opts) as ydl:
    info = ydl.extract_info(url, download=False)
    print("Total formats returned by yt-dlp:", len(info.get('formats', [])))
    for f in info.get('formats', []):
        if f.get('vcodec') != 'none':
            res = f.get('height') or f.get('width')
            print(f"Format ID: {f.get('format_id')}, Ext: {f.get('ext')}, Res: {res}, Vcodec: {f.get('vcodec')}, Acodec: {f.get('acodec')}")
