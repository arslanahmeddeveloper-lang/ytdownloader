# Nexus YouTube Downloader

A modern, production-ready, full-stack YouTube Downloader web application. 
No third-party YouTube API used—powered exclusively by `yt-dlp` and `FFmpeg`.

## Features
- **Extremely Fast:** Video resolution up to 4K + high-quality 192kbps MP3 audio extraction.
- **Smart Logic:** Uses asynchronous background tasks so the UI never blocks. Merges audio and video seamlessly.
- **Premium Design:** Glassmorphic UI with smooth animations.
- **Auto Cleanup:** Deletes downloaded files from the disk automatically after the user downloads them.

---

## 🚀 Setup & Installation (Local)

### Prerequisites
1. **Python 3.9+** installed.
2. **FFmpeg** installed and added to your system environment variables (PATH).
   - *Windows:* Download from [gyan.dev](https://www.gyan.dev/ffmpeg/builds/), extract, and add the `bin` folder to your PATH.
   - *Linux:* `sudo apt install ffmpeg`
   - *Mac:* `brew install ffmpeg`

### Steps
1. Navigate to the `backend` folder.
   ```bash
   cd backend
   ```
2. Create a virtual environment (optional but recommended):
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Run the application:
   ```bash
   uvicorn main:app --reload
   ```
5. Open your browser and go to: `http://127.0.0.1:8000`

---

## 🌍 Server Deployment (Linux VPS using Nginx & Gunicorn/Uvicorn)

1. Clone your project onto your server:
   ```bash
   git clone <your-repo> /var/www/yt-downloader
   cd /var/www/yt-downloader/backend
   ```
2. Install FFmpeg:
   ```bash
   sudo apt update && sudo apt install ffmpeg -y
   ```
3. Setup Python Virtual Environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```
4. Create a systemd service for FastAPI (`/etc/systemd/system/ytdownloader.service`):
   ```ini
   [Unit]
   Description=Gunicorn instance to serve FastAPI
   After=network.target

   [Service]
   User=www-data
   Group=www-data
   WorkingDirectory=/var/www/yt-downloader/backend
   Environment="PATH=/var/www/yt-downloader/backend/venv/bin"
   ExecStart=/var/www/yt-downloader/backend/venv/bin/gunicorn -w 4 -k uvicorn.workers.UvicornWorker main:app

   [Install]
   WantedBy=multi-user.target
   ```
   Start the service:
   ```bash
   sudo systemctl start ytdownloader
   sudo systemctl enable ytdownloader
   ```
5. Setup Nginx Reverse Proxy (`/etc/nginx/sites-available/ytdownloader`):
   ```nginx
   server {
       listen 80;
       server_name yourdomain.com;

       location / {
           proxy_pass http://127.0.0.1:8000;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
           proxy_buffering off;
       }
   }
   ```
   Enable it:
   ```bash
   sudo ln -s /etc/nginx/sites-available/ytdownloader /etc/nginx/sites-enabled
   sudo systemctl restart nginx
   ```
---

## 📂 Folder Structure

```
yt-downloader/
│
├── backend/
│   ├── downloads/           # Temp dir for files
│   ├── main.py              # FastAPI server
│   ├── downloader.py        # yt-dlp core wrapper
│   └── requirements.txt     # Python deps
│
├── frontend/
│   ├── css/
│   │   └── style.css        # Premium Glassmorphism styling
│   ├── js/
│   │   └── app.js           # Vanilla JS AJAX logic
│   └── index.html           # Structure
│
└── README.md
```

## Example Requests

**Get Video Info**
```bash
curl -X POST "http://127.0.0.1:8000/api/info" \
     -H "Content-Type: application/json" \
     -d '{"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"}'
```

**Start Download (Audio Only)**
```bash
curl -X POST "http://127.0.0.1:8000/api/download" \
     -H "Content-Type: application/json" \
     -d '{"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ", "audio_only": true}'
```
