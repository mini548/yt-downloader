// i18n Dictionary
const translations = {
  'zh-TW': {
    badge_online: '服務正常',
    hero_title_1: '極速下載',
    hero_title_2: 'YouTube 影音',
    hero_subtitle: '免費支援 1080p / 4K 高畫質 MP4 與 320kbps MP3 音訊，貼上連結一鍵解析！',
    url_placeholder: '請在此貼上 YouTube 影片網址 (https://www.youtube.com/watch?v=...)',
    paste_btn: '貼上',
    fetch_btn: '解析影片',
    loading_text: '正在高速解析 YouTube 串流與可用畫質... 請稍候',
    tab_video: 'MP4 影片下載',
    tab_audio: 'MP3 音訊下載',
    download_btn: '下載',
    downloading_notice: '正在由伺服器處理與封裝中，瀏覽器將在數秒內自動彈出儲存檔案視窗...',
    feat_1_title: '極速無廣告',
    feat_1_desc: '簡潔純粹的介面，絕無惱人彈跳廣告與惡意導流，貼上連結即刻開始。',
    feat_2_title: '1080p / 4K 高畫質',
    feat_2_desc: '內建 FFmpeg 音畫無損封裝，支援最高解析度 MP4 影片下載。',
    feat_3_title: '全裝置通用',
    feat_3_desc: '響應式自適應排版，電腦、iPhone、Android 手機與平板隨開即用。',
    disclaimer: '免責聲明：本服務僅供個人學習、研究與離線備份自身擁有之影音用途。請尊重原創版權與 YouTube 服務協議，嚴禁下載未經授權之商業版權影音。',
    clipboard_denied: '無法讀取剪貼簿，請手動按 Ctrl+V 貼上。',
    empty_url: '請輸入有效的 YouTube 網址！'
  },
  'en': {
    badge_online: 'Online',
    hero_title_1: 'Fast & Easy',
    hero_title_2: 'YouTube Downloader',
    hero_subtitle: 'Free 1080p / 4K MP4 video & 320kbps MP3 audio download. Paste link to start!',
    url_placeholder: 'Paste YouTube link here (https://www.youtube.com/watch?v=...)',
    paste_btn: 'Paste',
    fetch_btn: 'Fetch Info',
    loading_text: 'Analyzing YouTube stream & available resolutions... Please wait',
    tab_video: 'MP4 Video',
    tab_audio: 'MP3 Audio',
    download_btn: 'Download',
    downloading_notice: 'Server is processing & muxing media. Browser download will pop up shortly...',
    feat_1_title: 'Fast & No Ads',
    feat_1_desc: 'Clean, minimal interface without intrusive popups or shady redirects.',
    feat_2_title: '1080p / 4K HD',
    feat_2_desc: 'Integrated lossless FFmpeg remuxing for crystal-clear video quality.',
    feat_3_title: 'Works Everywhere',
    feat_3_desc: 'Fully responsive for PC, Mac, iPhone, Android, and tablets.',
    disclaimer: 'Disclaimer: This tool is intended for personal learning and fair-use archiving. Please respect copyright laws and YouTube Terms of Service.',
    clipboard_denied: 'Unable to access clipboard. Please paste manually (Ctrl+V).',
    empty_url: 'Please enter a valid YouTube URL!'
  }
};

let currentLang = 'zh-TW';
let currentVideoData = null;

// DOM Elements
const urlForm = document.getElementById('urlForm');
const videoUrlInput = document.getElementById('videoUrl');
const pasteBtn = document.getElementById('pasteBtn');
const fetchBtn = document.getElementById('fetchBtn');
const loadingBox = document.getElementById('loadingBox');
const errorBox = document.getElementById('errorBox');
const errorMessage = document.getElementById('errorMessage');
const resultCard = document.getElementById('resultCard');

const videoThumb = document.getElementById('videoThumb');
const videoTitle = document.getElementById('videoTitle');
const videoAuthor = document.getElementById('videoAuthor');
const videoDuration = document.getElementById('videoDuration');

const tabVideo = document.getElementById('tabVideo');
const tabAudio = document.getElementById('tabAudio');
const videoFormatsList = document.getElementById('videoFormatsList');
const audioFormatsList = document.getElementById('audioFormatsList');
const downloadNotice = document.getElementById('downloadNotice');
const downloadNoticeText = document.getElementById('downloadNoticeText');

const langToggle = document.getElementById('langToggle');
const langLabel = document.getElementById('langLabel');

// Language switcher
function setLanguage(lang) {
  currentLang = lang;
  langLabel.textContent = lang === 'zh-TW' ? 'English' : '繁體中文';
  videoUrlInput.placeholder = translations[lang].url_placeholder;

  document.querySelectorAll('[data-i18n]').forEach(el => {
    const key = el.getAttribute('data-i18n');
    if (translations[lang][key]) {
      el.textContent = translations[lang][key];
    }
  });

  if (currentVideoData) {
    renderFormats();
  }
}

langToggle.addEventListener('click', () => {
  setLanguage(currentLang === 'zh-TW' ? 'en' : 'zh-TW');
});

// Paste button
pasteBtn.addEventListener('click', async () => {
  try {
    const text = await navigator.clipboard.readText();
    if (text) {
      videoUrlInput.value = text.trim();
      videoUrlInput.focus();
    }
  } catch (err) {
    showError(translations[currentLang].clipboard_denied);
  }
});

// Tab Switcher
tabVideo.addEventListener('click', () => {
  tabVideo.className = "px-5 py-2.5 font-semibold text-sm border-b-2 border-rose-500 text-white flex items-center space-x-2";
  tabAudio.className = "px-5 py-2.5 font-semibold text-sm border-b-2 border-transparent text-slate-400 hover:text-slate-200 flex items-center space-x-2 transition-colors";
  videoFormatsList.classList.remove('hidden');
  audioFormatsList.classList.add('hidden');
});

tabAudio.addEventListener('click', () => {
  tabAudio.className = "px-5 py-2.5 font-semibold text-sm border-b-2 border-rose-500 text-white flex items-center space-x-2";
  tabVideo.className = "px-5 py-2.5 font-semibold text-sm border-b-2 border-transparent text-slate-400 hover:text-slate-200 flex items-center space-x-2 transition-colors";
  audioFormatsList.classList.remove('hidden');
  videoFormatsList.classList.add('hidden');
});

function showError(msg) {
  errorMessage.textContent = msg;
  errorBox.classList.remove('hidden');
  loadingBox.classList.add('hidden');
  resultCard.classList.add('hidden');
}

function clearError() {
  errorBox.classList.add('hidden');
  errorMessage.textContent = '';
}

// Fetch Video Info
urlForm.addEventListener('submit', async (e) => {
  e.preventDefault();
  const url = videoUrlInput.value.trim();
  if (!url) {
    showError(translations[currentLang].empty_url);
    return;
  }

  clearError();
  resultCard.classList.add('hidden');
  loadingBox.classList.remove('hidden');
  downloadNotice.classList.add('hidden');
  fetchBtn.disabled = true;

  try {
    const response = await fetch('/api/info', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url: url })
    });

    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.detail || '無法取得影片資訊，請稍後再試。');
    }

    currentVideoData = data;
    displayResult(data);
  } catch (err) {
    showError(err.message || '連線伺服器時發生問題。');
  } finally {
    loadingBox.classList.add('hidden');
    fetchBtn.disabled = false;
  }
});

function displayResult(data) {
  videoThumb.src = data.thumbnail || '';
  videoTitle.textContent = data.title;
  videoAuthor.textContent = data.uploader;
  videoDuration.textContent = data.duration;

  renderFormats();
  resultCard.classList.remove('hidden');
  resultCard.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

function renderFormats() {
  if (!currentVideoData) return;

  const t = translations[currentLang];

  // Render Video Options
  videoFormatsList.innerHTML = '';
  currentVideoData.video_options.forEach(opt => {
    const item = document.createElement('div');
    item.className = "flex items-center justify-between p-3.5 bg-slate-800/60 hover:bg-slate-800 border border-slate-700/60 rounded-xl transition-all";
    item.innerHTML = `
      <div class="flex items-center space-x-3">
        <span class="w-8 h-8 rounded-lg bg-rose-500/10 text-rose-400 font-bold text-xs flex items-center justify-center shrink-0">
          MP4
        </span>
        <div>
          <div class="font-semibold text-white text-sm">${opt.label}</div>
          <div class="text-xs text-slate-400">MP4 (Video + Audio)</div>
        </div>
      </div>
      <button 
        onclick="triggerDownload('${encodeURIComponent(currentVideoData.url)}', 'video', '${opt.quality}')"
        class="px-4 py-2 bg-rose-600 hover:bg-rose-500 text-white text-xs font-semibold rounded-lg shadow-sm transition-colors flex items-center space-x-1.5 cursor-pointer"
      >
        <span>${t.download_btn}</span>
        <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"/>
        </svg>
      </button>
    `;
    videoFormatsList.appendChild(item);
  });

  // Render Audio Options
  audioFormatsList.innerHTML = '';
  currentVideoData.audio_options.forEach(opt => {
    const item = document.createElement('div');
    item.className = "flex items-center justify-between p-3.5 bg-slate-800/60 hover:bg-slate-800 border border-slate-700/60 rounded-xl transition-all";
    item.innerHTML = `
      <div class="flex items-center space-x-3">
        <span class="w-8 h-8 rounded-lg bg-sky-500/10 text-sky-400 font-bold text-xs flex items-center justify-center shrink-0">
          ${opt.ext.toUpperCase()}
        </span>
        <div>
          <div class="font-semibold text-white text-sm">${opt.label}</div>
          <div class="text-xs text-slate-400">Audio Only</div>
        </div>
      </div>
      <button 
        onclick="triggerDownload('${encodeURIComponent(currentVideoData.url)}', 'audio', '${opt.quality}')"
        class="px-4 py-2 bg-sky-600 hover:bg-sky-500 text-white text-xs font-semibold rounded-lg shadow-sm transition-colors flex items-center space-x-1.5 cursor-pointer"
      >
        <span>${t.download_btn}</span>
        <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"/>
        </svg>
      </button>
    `;
    audioFormatsList.appendChild(item);
  });
}

// Download action
function triggerDownload(encodedUrl, formatType, quality) {
  const t = translations[currentLang];
  downloadNoticeText.textContent = t.downloading_notice;
  downloadNotice.classList.remove('hidden');

  const downloadUrl = `/api/download?url=${encodedUrl}&format_type=${formatType}&quality=${quality}`;
  
  // Use a hidden iframe or direct location change to trigger browser file download without losing page state
  const iframe = document.createElement('iframe');
  iframe.style.display = 'none';
  iframe.src = downloadUrl;
  document.body.appendChild(iframe);

  // Hide the notice after 8 seconds
  setTimeout(() => {
    downloadNotice.classList.add('hidden');
    document.body.removeChild(iframe);
  }, 10000);
}
