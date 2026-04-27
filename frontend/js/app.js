document.addEventListener('DOMContentLoaded', () => {
    // UI Elements
    const urlInput = document.getElementById('urlInput');
    const fetchBtn = document.getElementById('fetchBtn');
    
    const errorBox = document.getElementById('errorBox');
    const errorText = document.getElementById('errorText');
    
    const loadingBox = document.getElementById('loadingBox');
    const resultBox = document.getElementById('resultBox');
    const progressBox = document.getElementById('progressBox');
    
    const thumbnail = document.getElementById('thumbnail');
    const videoTitle = document.getElementById('videoTitle');
    const videoDuration = document.getElementById('videoDuration');
    const qualityGrid = document.getElementById('qualityGrid');
    
    const downloadVideoBtn = document.getElementById('downloadVideoBtn');
    
    const progressBar = document.getElementById('progressBar');
    const progressPercentage = document.getElementById('progressPercentage');
    const progressStatus = document.getElementById('progressStatus');
    const downloadLinkBox = document.getElementById('downloadLinkBox');
    const downloadAnotherBtn = document.getElementById('downloadAnotherBtn');

    let currentVideoUrl = '';
    let currentDownloadType = 'video';
    let selectedFormatId = '';

    function formatTime(seconds) {
        if (!seconds) return '00:00';
        const h = Math.floor(seconds / 3600);
        const m = Math.floor((seconds % 3600) / 60);
        const s = seconds % 60;
        if (h > 0) return `${h}:${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
        return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
    }

    function formatBytes(bytes) {
        if (!bytes || bytes === 0) return 'Unknown size';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    function showError(msg) {
        errorText.textContent = msg;
        errorBox.classList.remove('hidden');
        loadingBox.classList.add('hidden');
        resultBox.classList.add('hidden');
        progressBox.classList.add('hidden');
    }

    function hideError() {
        errorBox.classList.add('hidden');
    }

    // Fetch Video Info
    const fetchMetadata = async () => {
        const url = urlInput.value.trim();
        if (!url || (!url.startsWith('http://') && !url.startsWith('https://'))) {
            showError("Please enter a valid video URL.");
            return;
        }

        currentVideoUrl = url;
        hideError();
        resultBox.classList.add('hidden');
        progressBox.classList.add('hidden');
        loadingBox.classList.remove('hidden');

        try {
            const res = await fetch('/api/info', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ url: url })
            });
            const data = await res.json();

            if (!res.ok || !data.success) {
                throw new Error(data.detail || "Failed to fetch video info.");
            }

            // Populate UI
            const info = data.data;
            thumbnail.src = info.thumbnail;
            videoTitle.textContent = info.title;
            videoDuration.textContent = formatTime(info.duration);

            // Populate Quality Grid
            qualityGrid.innerHTML = '';
            selectedFormatId = '';
            
            // Deduplicate to show only distinct resolutions, prioritizing MP4 format
            const uniqueFormats = {};
            info.formats.forEach(f => {
                if(f.has_video && f.resolution && f.resolution !== "watermarked") {
                    const key = f.resolution;
                    const isMP4 = (f.ext && f.ext.toLowerCase() === 'mp4');
                    
                    if (!uniqueFormats[key]) {
                        uniqueFormats[key] = f;
                    } else {
                        const existing = uniqueFormats[key];
                        const existingIsMP4 = (existing.ext && existing.ext.toLowerCase() === 'mp4');
                        
                        if (isMP4 && !existingIsMP4) {
                            uniqueFormats[key] = f;
                        } else if (isMP4 === existingIsMP4) {
                             if ((f.filesize || 0) > (existing.filesize || 0)) {
                                 uniqueFormats[key] = f;
                             }
                        }
                    }
                }
            });

            // Sort formats by resolution (highest to lowest)
            const processedFormats = Object.values(uniqueFormats).sort((a,b) => {
                let resA = parseInt(a.resolution) || 0;
                let resB = parseInt(b.resolution) || 0;
                if (a.resolution === '4K') resA = 2160;
                if (b.resolution === '4K') resB = 2160;
                return resB - resA;
            });

            if (processedFormats.length === 0) {
                 qualityGrid.innerHTML = '<p style="color: var(--text-muted); padding: 10px;">Best quality will be selected automatically.</p>';
                 selectedFormatId = "";
            } else {
                processedFormats.forEach((f, index) => {
                    const box = document.createElement('div');
                    box.className = 'quality-box';
                    
                    // Select the best quality by default
                    if (index === 0) {
                        box.classList.add('selected');
                        selectedFormatId = f.format_id;
                    }
                    
                    const size = formatBytes(f.filesize);
                    const fps = f.fps ? ` ${f.fps}fps` : '';
                    const ext = f.ext ? f.ext.toUpperCase() : 'MP4';
                    
                    box.innerHTML = `
                        <span class="res">${f.resolution}</span>
                        <span class="size">${size} • ${ext}</span>
                    `;
                    
                    box.addEventListener('click', () => {
                        document.querySelectorAll('.quality-box').forEach(b => b.classList.remove('selected'));
                        box.classList.add('selected');
                        selectedFormatId = f.format_id;
                    });
                    
                    qualityGrid.appendChild(box);
                });
            }

            loadingBox.classList.add('hidden');
            resultBox.classList.remove('hidden');

        } catch (err) {
            showError(err.message);
        }
    };

    fetchBtn.addEventListener('click', fetchMetadata);

    urlInput.addEventListener('input', () => {
        const val = urlInput.value.trim();
        if (val.startsWith('http://') || val.startsWith('https://')) {
            if (currentVideoUrl !== val) {
                fetchMetadata();
            }
        }
    });

    // Start Download
    async function initDownload(formatId, audioOnly) {
        currentDownloadType = audioOnly ? 'audio' : 'video';
        resultBox.classList.add('hidden');
        progressBox.classList.remove('hidden');
        downloadLinkBox.classList.add('hidden');
        progressBar.style.width = '0%';
        progressPercentage.textContent = '0%';
        progressStatus.textContent = 'Starting processing...';

        try {
            const res = await fetch('/api/download', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ 
                    url: currentVideoUrl, 
                    format_id: formatId, 
                    audio_only: audioOnly 
                })
            });
            const data = await res.json();

            if (!res.ok) throw new Error(data.detail);

            pollStatus(data.task_id);

        } catch (err) {
            showError(err.message);
        }
    }

    // Polling Mechanism
    function pollStatus(taskId) {
        const interval = setInterval(async () => {
            try {
                const res = await fetch(`/api/status/${taskId}`);
                const data = await res.json();
                
                if(!res.ok) throw new Error("Task checking failed");
                const status = data.data;

                if (status.status === 'error') {
                    clearInterval(interval);
                    showError(status.error || 'Unknown download error occurred');
                    return;
                }

                if (status.status === 'downloading') {
                    progressStatus.textContent = 'Downloading video chunks...';
                    progressBar.style.width = `${status.progress}%`;
                    progressPercentage.textContent = `${status.progress}%`;
                }

                if (status.status === 'processing') {
                    progressStatus.textContent = 'Processing & Merging... (This may take a while)';
                    progressBar.style.width = '100%';
                    progressPercentage.textContent = '100%';
                }

                if (status.status === 'completed') {
                    clearInterval(interval);
                    progressStatus.textContent = 'Ready!';
                    progressBar.style.width = '100%';
                    progressPercentage.textContent = '100%';
                    
                    // Show download Link Box
                    downloadLinkBox.classList.remove('hidden');
                    
                    // Auto download
                    const autoLink = document.createElement('a');
                    autoLink.href = `/api/file/${taskId}`;
                    autoLink.download = currentDownloadType === 'audio' ? 'audio.mp3' : 'video.mp4';
                    document.body.appendChild(autoLink);
                    autoLink.click();
                    document.body.removeChild(autoLink);
                }

            } catch (err) {
                console.error(err);
                // Don't stop on single failure, might just be network blip
            }
        }, 2000);
    }

    downloadVideoBtn.addEventListener('click', () => {
        initDownload(selectedFormatId, false);
    });

    const downloadAudioBtn = document.getElementById('downloadAudioBtn');
    if (downloadAudioBtn) {
        downloadAudioBtn.addEventListener('click', () => {
            initDownload("", true);
        });
    }

    if (downloadAnotherBtn) {
        downloadAnotherBtn.addEventListener('click', () => {
            urlInput.value = '';
            progressBox.classList.add('hidden');
            loadingBox.classList.add('hidden');
            resultBox.classList.add('hidden');
            errorBox.classList.add('hidden');
            urlInput.focus();
        });
    }
});
