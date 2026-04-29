from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import os

import sys
sys.path.append(os.path.dirname(__file__))
import downloader
app = FastAPI(title="YouTube Downloader API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class InfoRequest(BaseModel):
    url: str

class DownloadRequest(BaseModel):
    url: str
    format_id: str = ""
    audio_only: bool = False

@app.post("/api/info")
def get_info(req: InfoRequest):
    try:
        info = downloader.get_video_info(req.url)
        return {"success": True, "data": info}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/download")
async def start_download(req: DownloadRequest):
    try:
        task_id = await downloader.start_download(req.url, req.format_id, req.audio_only)
        return {"success": True, "task_id": task_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/status/{task_id}")
def get_status(task_id: str):
    status = downloader.get_task_status(task_id)
    if not status:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"success": True, "data": status}

from fastapi.responses import FileResponse, RedirectResponse, Response
import httpx

@app.get("/api/thumbnail")
async def get_thumbnail(url: str):
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, follow_redirects=True)
            return Response(content=resp.content, media_type=resp.headers.get("content-type", "image/jpeg"))
    except Exception:
        # Fallback to a blank image or 404
        raise HTTPException(status_code=404, detail="Thumbnail not found")

@app.get("/api/file/{task_id}")
def get_file(task_id: str, background_tasks: BackgroundTasks):
    status = downloader.get_task_status(task_id)
    if not status or status.get('status') != 'completed':
        raise HTTPException(status_code=400, detail="File not ready")
        
    filename = status.get('filename')
    if not filename or not os.path.exists(filename):
        raise HTTPException(status_code=404, detail="File not found on disk")
        
    basename = os.path.basename(filename)
    return RedirectResponse(url=f"/downloads/{basename}")

DOWNLOADS_DIR = os.path.join(os.path.dirname(__file__), "downloads")
os.makedirs(DOWNLOADS_DIR, exist_ok=True)
app.mount("/downloads", StaticFiles(directory=DOWNLOADS_DIR), name="downloads")

FRONTEND_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")
os.makedirs(FRONTEND_DIR, exist_ok=True)
app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
