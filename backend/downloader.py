import os
import uuid
import asyncio
import yt_dlp
import glob
import itertools
import threading
from concurrent.futures import ThreadPoolExecutor

DOWNLOAD_DIR = os.path.join(os.path.dirname(__file__), "downloads")
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

def cleanup_downloads_if_needed():
    max_size_bytes = 10 * 1024 * 1024 * 1024 # 10 GB
    target_size_bytes = 9 * 1024 * 1024 * 1024 # 9 GB
    
    total_size = 0
    files = []
    for f in os.listdir(DOWNLOAD_DIR):
        file_path = os.path.join(DOWNLOAD_DIR, f)
        if os.path.isfile(file_path):
            size = os.path.getsize(file_path)
            total_size += size
            files.append((file_path, os.path.getmtime(file_path), size))
            
    if total_size > max_size_bytes:
        # Sort files by oldest first
        files.sort(key=lambda x: x[1])
        for file_path, _, size in files:
            try:
                os.remove(file_path)
                total_size -= size
                if total_size <= target_size_bytes:
                    break
            except Exception:
                pass


PROXIES = [
    "http://shumzmajid:DBZgnJUSSV@96.62.111.183:50100",
    "http://shumzmajid:DBZgnJUSSV@151.247.188.170:50100",
    "http://shumzmajid:DBZgnJUSSV@193.169.218.174:50100",
    "http://shumzmajid:DBZgnJUSSV@85.208.11.31:50100",
    "http://shumzmajid:DBZgnJUSSV@209.101.255.173:50100"
]
proxy_pool = itertools.cycle(PROXIES)
proxy_lock = threading.Lock()

def get_next_proxy():
    with proxy_lock:
        return next(proxy_pool)

# In-memory dictionary to store task progress
# Format: { task_id: {"status": "downloading", "progress": 0, "filename": "", "error": ""} }
tasks = {}
executor = ThreadPoolExecutor(max_workers=5)

def get_video_info(url: str):
    max_retries = 3
    last_error_msg = ""
    
    for attempt in range(max_retries):
        try:
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'extract_flat': False,
                'skip_download': True,
                'source_address': '0.0.0.0'
            }
            ydl_opts['proxy'] = get_next_proxy()
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                
                # Filter formats
                extracted_formats = []
                if 'formats' in info:
                    for f in info['formats']:
                        if f.get('vcodec') != 'none':
                            filesize = f.get('filesize') or f.get('filesize_approx') or 0
                            note = (f.get('format_note') or '').lower()
                            w = f.get('width') or 0
                            h = f.get('height') or 0
                            res_val = min(w, h) if w and h else (h or w)
                            
                            display_res = ''
                            if res_val:
                                if res_val >= 2160: display_res = '4K'
                                elif res_val >= 1440: display_res = '1440p'
                                elif res_val >= 1080: display_res = '1080p'
                                elif res_val >= 720: display_res = '720p'
                                elif res_val >= 480: display_res = '480p'
                                elif res_val >= 360: display_res = '360p'
                                elif res_val >= 240: display_res = '240p'
                                elif res_val >= 144: display_res = '144p'
                            elif 'p' in note:
                                for word in note.split():
                                    if 'p' in word and word[:-1].isdigit():
                                        p_val = int(word[:-1])
                                        if p_val >= 2160: display_res = '4K'
                                        elif p_val >= 1440: display_res = '1440p'
                                        elif p_val >= 1080: display_res = '1080p'
                                        elif p_val >= 720: display_res = '720p'
                                        elif p_val >= 480: display_res = '480p'
                                        elif p_val >= 360: display_res = '360p'
                                        elif p_val >= 240: display_res = '240p'
                                        elif p_val >= 144: display_res = '144p'
                                        break
                            
                            TARGET_RES = ['144p', '240p', '360p', '480p', '720p', '1080p', '1440p', '4K']
                            if display_res in TARGET_RES:
                                form = {
                                    "format_id": f.get('format_id'),
                                    "ext": f.get('ext'),
                                    "resolution": display_res,
                                    "vcodec": f.get('vcodec'),
                                    "acodec": f.get('acodec'),
                                    "filesize": filesize,
                                    "fps": f.get('fps'),
                                    "has_video": True,
                                    "has_audio": f.get('acodec') != 'none'
                                }
                                extracted_formats.append(form)
                            
                thumbnail_url = info.get('thumbnail')
                if not thumbnail_url and info.get('thumbnails'):
                    for t in reversed(info['thumbnails']):
                        if t.get('url'):
                            thumbnail_url = t.get('url')
                            break
                            
                return {
                    "title": info.get('title', 'Unknown Title'),
                    "thumbnail": thumbnail_url,
                    "duration": info.get('duration', 0),
                    "formats": extracted_formats
                }
                
        except Exception as e:
            error_msg = str(e).lower()
            last_error_msg = str(e)
            if "sign in to confirm" in error_msg and "bot" in error_msg:
                continue
            else:
                raise e

    if last_error_msg:
        raise Exception("Please reload, your internet is very slow")

def download_video_sync(task_id: str, url: str, format_id: str, audio_only: bool):
    try:
        cleanup_downloads_if_needed()
        tasks[task_id] = {"status": "starting", "progress": 0, "filename": "", "error": None}
        
        outtmpl = os.path.join(DOWNLOAD_DIR, f"{task_id}_%(title)s.%(ext)s")
        
        def run_ydl(use_proxy=False):
            ydl_opts = {
                'outtmpl': outtmpl,
                'quiet': True,
                'no_warnings': True,
                'source_address': '0.0.0.0',
                'concurrent_fragment_downloads': 30,
                'http_chunk_size': 10485760,
                'buffersize': 1024 * 1024 * 5,
                'nocheckcertificate': True,
                'socket_timeout': 15,
                'external_downloader': 'aria2c',
                'external_downloader_args': ['-c', '-j', '10', '-x', '10', '-s', '10', '-k', '5M']
            }
            if use_proxy:
                ydl_opts['proxy'] = get_next_proxy()
                
            def hooked(d):
                if d['status'] == 'downloading':
                    total = d.get('total_bytes') or d.get('total_bytes_estimate')
                    if total:
                        downloaded = d.get('downloaded_bytes', 0)
                        progress = (downloaded / total) * 100
                        tasks[task_id]['progress'] = round(progress, 2)
                        tasks[task_id]['status'] = 'downloading'
                elif d['status'] == 'finished':
                    tasks[task_id]['progress'] = 100
                    tasks[task_id]['status'] = 'processing'
                    
            ydl_opts['progress_hooks'] = [hooked]
            
            if audio_only:
                ydl_opts['format'] = 'bestaudio/best'
                ydl_opts['postprocessors'] = [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }]
            else:
                if format_id:
                    ydl_opts['format'] = f"{format_id}+bestaudio/best"
                    ydl_opts['merge_output_format'] = 'mp4'
                else:
                    ydl_opts['format'] = 'bestvideo+bestaudio/best'
                    ydl_opts['merge_output_format'] = 'mp4'

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                
                search_pattern = os.path.join(DOWNLOAD_DIR, f"{task_id}_*.*")
                actual_files = glob.glob(search_pattern)
                if actual_files:
                    final_files = [f for f in actual_files if not f.endswith('.part') and not f.endswith('.ytdl')]
                    if final_files:
                        filename = final_files[0]
                    else:
                        filename = actual_files[0]
                else:
                    filename = ydl.prepare_filename(info)
                    if audio_only:
                        base, _ = os.path.splitext(filename)
                        filename = f"{base}.mp3"
                    
                tasks[task_id]['filename'] = filename
                tasks[task_id]['status'] = 'completed'

        try:
            run_ydl(use_proxy=False)
        except Exception as native_e:
            error_str = str(native_e).lower()
            if "sign in" in error_str or "bot" in error_str or "403" in error_str or "429" in error_str:
                # Fallback to proxy
                run_ydl(use_proxy=True)
            else:
                raise native_e

    except Exception as e:
        tasks[task_id]['status'] = 'error'
        tasks[task_id]['error'] = str(e)

async def start_download(url: str, format_id: str, audio_only: bool) -> str:
    task_id = str(uuid.uuid4())
    asyncio.get_event_loop().run_in_executor(
        executor, 
        download_video_sync, 
        task_id, url, format_id, audio_only
    )
    return task_id

def get_task_status(task_id: str):
    return tasks.get(task_id)

def delete_task_file(task_id: str):
    task = tasks.get(task_id)
    if task and task.get('filename'):
        try:
            if os.path.exists(task['filename']):
                os.remove(task['filename'])
        except Exception:
            pass
    if task_id in tasks:
        del tasks[task_id]
