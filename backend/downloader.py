import os
import uuid
import asyncio
import yt_dlp
import glob
from concurrent.futures import ThreadPoolExecutor

DOWNLOAD_DIR = os.path.join(os.path.dirname(__file__), "downloads")
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# In-memory dictionary to store task progress
# Format: { task_id: {"status": "downloading", "progress": 0, "filename": "", "error": ""} }
tasks = {}
executor = ThreadPoolExecutor(max_workers=5)

def get_video_info(url: str):
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'extract_flat': False,
        'skip_download': True
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        
        # Filter formats
        extracted_formats = []
        if 'formats' in info:
            for f in info['formats']:
                if f.get('vcodec') != 'none':
                    filesize = f.get('filesize') or f.get('filesize_approx') or 0
                    note = (f.get('format_note') or '').lower()
                    h = f.get('height') or 0
                    
                    display_res = ''
                    if h == 144 or '144p' in note: display_res = '144p'
                    elif h == 360 or '360p' in note: display_res = '360p'
                    elif h == 480 or '480p' in note: display_res = '480p'
                    elif h == 720 or '720p' in note: display_res = '720p'
                    elif h == 1080 or '1080p' in note: display_res = '1080p'
                    elif h == 1440 or '1440p' in note: display_res = '1440p'
                    elif h == 2160 or '2160p' in note or '4k' in note: display_res = '4K'
                    else: continue
                    
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
                    
        return {
            "title": info.get('title', 'Unknown Title'),
            "thumbnail": info.get('thumbnail'),
            "duration": info.get('duration', 0),
            "formats": extracted_formats
        }

def download_video_sync(task_id: str, url: str, format_id: str, audio_only: bool):
    try:
        tasks[task_id] = {"status": "starting", "progress": 0, "filename": "", "error": None}
        
        outtmpl = os.path.join(DOWNLOAD_DIR, f"{task_id}_%(title)s.%(ext)s")
        ydl_opts = {
            'outtmpl': outtmpl,
            'quiet': True,
            'no_warnings': True,
            'concurrent_fragment_downloads': 10,
        }
        
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
