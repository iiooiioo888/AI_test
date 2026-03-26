/* ═══════════════════════════════════════════════════════════
   AI Video Studio — Frontend Logic
   ═══════════════════════════════════════════════════════════ */

const App = {
  fileId: null,
  currentTaskId: null,
  ws: null,
  effects: {},
  extendModes: {},

  async init() {
    this.bindEvents();
    await this.loadEffects();
    this.connectWS();
  },

  // ── API ──────────────────────────────────────────────
  async loadEffects() {
    const res = await fetch('/api/effects');
    const data = await res.json();
    this.effects = data.effects;
    this.extendModes = data.extend_modes;
    this.renderEffects();
    this.renderExtend();
  },

  async uploadFile(file) {
    const zone = document.getElementById('uploadZone');
    const inner = zone.querySelector('.upload-inner');
    const loading = document.getElementById('uploadLoading');
    inner.style.display = 'none';
    loading.style.display = 'block';

    const form = new FormData();
    form.append('file', file);

    try {
      const res = await fetch('/api/upload', { method: 'POST', body: form });
      if (!res.ok) throw new Error('上传失败');
      const data = await res.json();
      this.fileId = data.file_id;
      this.showWorkspace(data);
      this.toast('上传成功！', 'success');
    } catch (e) {
      this.toast(e.message, 'error');
      inner.style.display = '';
      loading.style.display = 'none';
    }
  },

  async startEffect(effect) {
    if (!this.fileId) return;
    const intensity = parseFloat(document.getElementById('intensity').value);

    const form = new FormData();
    form.append('file_id', this.fileId);
    form.append('effect', effect);
    form.append('intensity', intensity);

    try {
      const res = await fetch('/api/process/effect', { method: 'POST', body: form });
      const data = await res.json();
      this.currentTaskId = data.task_id;
      this.showProcessing(this.effects[effect].icon, this.effects[effect].name);
    } catch (e) {
      this.toast('启动失败: ' + e.message, 'error');
    }
  },

  async startExtend(mode) {
    if (!this.fileId) return;
    const slider = document.getElementById('extendSlider');
    const param = parseFloat(slider.value);

    const form = new FormData();
    form.append('file_id', this.fileId);
    form.append('mode', mode);
    form.append('param', param);

    try {
      const res = await fetch('/api/process/extend', { method: 'POST', body: form });
      const data = await res.json();
      this.currentTaskId = data.task_id;
      this.showProcessing(this.extendModes[mode].icon, this.extendModes[mode].name);
    } catch (e) {
      this.toast('启动失败: ' + e.message, 'error');
    }
  },

  // ── WebSocket ────────────────────────────────────────
  connectWS() {
    const proto = location.protocol === 'https:' ? 'wss' : 'ws';
    this.ws = new WebSocket(`${proto}://${location.host}/ws`);
    this.ws.onmessage = (e) => {
      const data = JSON.parse(e.data);
      if (data.task_id === this.currentTaskId) {
        this.updateProgress(data);
      }
    };
    this.ws.onclose = () => setTimeout(() => this.connectWS(), 3000);
  },

  // ── UI Updates ───────────────────────────────────────
  showWorkspace(data) {
    document.getElementById('uploadZone').style.display = 'none';
    document.getElementById('workspace').style.display = '';
    document.getElementById('processingPanel').style.display = 'none';
    document.getElementById('resultPanel').style.display = 'none';

    const video = document.getElementById('previewVideo');
    video.src = `/api/preview/${data.file_id}`;

    const meta = document.getElementById('videoMeta');
    const info = data.info;
    meta.innerHTML = `
      <span>📐 ${info.width}×${info.height}</span>
      <span>🎞️ ${info.fps.toFixed(1)} FPS</span>
      <span>⏱️ ${info.duration.toFixed(1)}s</span>
      <span>📦 ${(info.size / 1024 / 1024).toFixed(1)} MB</span>
      <span>🎬 ${info.codec}</span>
    `;
  },

  showProcessing(icon, name) {
    document.getElementById('workspace').style.display = 'none';
    document.getElementById('processingPanel').style.display = '';
    document.getElementById('resultPanel').style.display = 'none';

    document.getElementById('processingIcon').textContent = icon;
    document.getElementById('processingTitle').textContent = `正在应用: ${name}`;
    document.getElementById('progressFill').style.width = '0%';
    document.getElementById('progressText').textContent = '0%';
    document.getElementById('progressDetail').textContent = '初始化...';
    document.getElementById('statusPill').querySelector('span:last-child').textContent = '处理中';
    document.getElementById('statusPill').querySelector('.status-dot').style.background = 'var(--orange)';
  },

  updateProgress(data) {
    const fill = document.getElementById('progressFill');
    const text = document.getElementById('progressText');
    const detail = document.getElementById('progressDetail');

    fill.style.width = data.progress + '%';
    text.textContent = Math.round(data.progress) + '%';
    detail.textContent = data.message || '';

    if (data.status === 'done') {
      setTimeout(() => this.showResult(), 500);
    }
  },

  showResult() {
    document.getElementById('processingPanel').style.display = 'none';
    document.getElementById('resultPanel').style.display = '';

    const video = document.getElementById('resultVideo');
    const url = `/api/download/${this.currentTaskId}`;
    video.src = url;
    document.getElementById('btnDownload').href = url;

    document.getElementById('statusPill').querySelector('span:last-child').textContent = '完成';
    document.getElementById('statusPill').querySelector('.status-dot').style.background = 'var(--green)';
  },

  renderEffects() {
    const grid = document.getElementById('effectsGrid');
    grid.innerHTML = '';
    for (const [key, eff] of Object.entries(this.effects)) {
      const card = document.createElement('div');
      card.className = 'effect-card';
      card.innerHTML = `
        <span class="effect-icon">${eff.icon}</span>
        <div class="effect-name">${eff.name}</div>
        <div class="effect-desc">${eff.desc}</div>
      `;
      card.addEventListener('click', () => {
        if (card.classList.contains('processing')) return;
        card.classList.add('processing');
        this.startEffect(key).finally(() => card.classList.remove('processing'));
      });
      grid.appendChild(card);
    }
  },

  renderExtend() {
    const grid = document.getElementById('extendGrid');
    grid.innerHTML = '';
    for (const [key, mode] of Object.entries(this.extendModes)) {
      const card = document.createElement('div');
      card.className = 'effect-card';
      card.innerHTML = `
        <span class="effect-icon">${mode.icon}</span>
        <div class="effect-name">${mode.name}</div>
        <div class="effect-desc">${mode.desc}</div>
      `;
      card.addEventListener('click', () => {
        if (card.classList.contains('processing')) return;
        card.classList.add('processing');
        this.startExtend(key).finally(() => card.classList.remove('processing'));
      });
      grid.appendChild(card);
    }
  },

  // ── Events ───────────────────────────────────────────
  bindEvents() {
    const zone = document.getElementById('uploadZone');
    const fileInput = document.getElementById('fileInput');

    // Drag & drop
    zone.addEventListener('dragover', (e) => { e.preventDefault(); zone.classList.add('drag-over'); });
    zone.addEventListener('dragleave', () => zone.classList.remove('drag-over'));
    zone.addEventListener('drop', (e) => {
      e.preventDefault();
      zone.classList.remove('drag-over');
      const file = e.dataTransfer.files[0];
      if (file) this.uploadFile(file);
    });
    zone.addEventListener('click', (e) => {
      if (e.target === fileInput || e.target.closest('label')) return;
      fileInput.click();
    });
    fileInput.addEventListener('change', () => {
      if (fileInput.files[0]) this.uploadFile(fileInput.files[0]);
    });

    // Tabs
    document.querySelectorAll('.tab').forEach(tab => {
      tab.addEventListener('click', () => {
        document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
        document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
        tab.classList.add('active');
        document.getElementById(`tab-${tab.dataset.tab}`).classList.add('active');
      });
    });

    // Intensity slider
    const intensity = document.getElementById('intensity');
    const intensityVal = document.getElementById('intensityVal');
    intensity.addEventListener('input', () => {
      intensityVal.textContent = Math.round(intensity.value * 100) + '%';
    });

    // Extend slider
    const extSlider = document.getElementById('extendSlider');
    const extVal = document.getElementById('extendVal');
    extSlider.addEventListener('input', () => {
      extVal.textContent = extSlider.value + 'x';
    });

    // New video buttons
    document.getElementById('btnNew').addEventListener('click', () => this.reset());
    document.getElementById('btnNewVideo')?.addEventListener('click', () => this.reset());
    document.getElementById('btnBackToEdit')?.addEventListener('click', () => {
      document.getElementById('resultPanel').style.display = 'none';
      document.getElementById('workspace').style.display = '';
    });
  },

  reset() {
    this.fileId = null;
    this.currentTaskId = null;
    document.getElementById('uploadZone').style.display = '';
    document.getElementById('workspace').style.display = 'none';
    document.getElementById('processingPanel').style.display = 'none';
    document.getElementById('resultPanel').style.display = 'none';
    document.querySelector('.upload-inner').style.display = '';
    document.getElementById('uploadLoading').style.display = 'none';
    document.getElementById('fileInput').value = '';
    document.getElementById('statusPill').querySelector('span:last-child').textContent = '就绪';
    document.getElementById('statusPill').querySelector('.status-dot').style.background = 'var(--green)';
  },

  toast(msg, type = '') {
    const container = document.getElementById('toastContainer');
    const el = document.createElement('div');
    el.className = `toast ${type}`;
    el.textContent = msg;
    container.appendChild(el);
    setTimeout(() => { el.style.opacity = '0'; setTimeout(() => el.remove(), 300); }, 3000);
  },
};

document.addEventListener('DOMContentLoaded', () => App.init());
