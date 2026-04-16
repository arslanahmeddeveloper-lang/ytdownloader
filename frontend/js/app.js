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
    const videoFormatSelect = document.getElementById('videoFormatSelect');
    
    const downloadVideoBtn = document.getElementById('downloadVideoBtn');
    
    const progressBar = document.getElementById('progressBar');
    const progressPercentage = document.getElementById('progressPercentage');
    const progressStatus = document.getElementById('progressStatus');
    const downloadLinkBox = document.getElementById('downloadLinkBox');
    const downloadAnotherBtn = document.getElementById('downloadAnotherBtn');

    let currentVideoUrl = '';
    let currentDownloadType = 'video';

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
        if (!url) {
            showError("Please enter a valid YouTube URL.");
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

            // Populate Select (filter for likely usable video variants)
            videoFormatSelect.innerHTML = '';
            
            // Deduplicate formats by resolution explicitly
            const uniqueFormats = {};
            info.formats.forEach(f => {
                if(f.has_video && f.resolution) {
                    const key = f.resolution;
                    // Prefer formats with audio if available directly, or highest filesize if both lack audio
                    if(!uniqueFormats[key] || (!uniqueFormats[key].has_audio && f.has_audio) || (uniqueFormats[key].filesize < f.filesize)) {
                        uniqueFormats[key] = f;
                    }
                }
            });

            // If empty, fallback to basic options
            const processedFormats = Object.values(uniqueFormats).sort((a,b) => {
                const resA = parseInt(a.resolution) || 0;
                const resB = parseInt(b.resolution) || 0;
                return resB - resA; // Highest quality first
            });

            if (processedFormats.length === 0) {
                 const opt = document.createElement('option');
                 opt.value = "";
                 opt.textContent = "Best Quality Output (Auto MP4)";
                 videoFormatSelect.appendChild(opt);
            } else {
                processedFormats.forEach(f => {
                    const opt = document.createElement('option');
                    opt.value = f.format_id;
                    const size = formatBytes(f.filesize);
                    opt.textContent = `${f.resolution} (MP4) - ${size}`;
                    videoFormatSelect.appendChild(opt);
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
        if (val.match(/(youtube\.com\/watch\?v=|youtu\.be\/)/)) {
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
        const formatId = videoFormatSelect.value;
        initDownload(formatId, false);
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
