/* ═══════════════════════════════════════════════════════════
   AI Video Studio — Frontend Logic (Optimized)
   ═══════════════════════════════════════════════════════════ */

const App = {
  fileId: null,
  currentTaskId: null,
  ws: null,
  effects: {},
  extendModes: {},
  _reconnectTimer: null,
  _processing: false,

  async init() {
    this.bindEvents();
    await this.loadEffects();
    this.connectWS();
  },

  // ── API ──────────────────────────────────────────────
  async loadEffects() {
    try {
      const res = await fetch('/api/effects');
      if (!res.ok) throw new Error('加载特效列表失败');
      const data = await res.json();
      this.effects = data.effects;
      this.extendModes = data.extend_modes;
      this.renderEffects();
      this.renderExtend();
    } catch (e) {
      this.toast('无法加载特效: ' + e.message, 'error');
    }
  },

  async uploadFile(file) {
    const MAX_SIZE = 500 * 1024 * 1024;
    if (file.size > MAX_SIZE) {
      this.toast(`文件过大 (${(file.size/1024/1024).toFixed(0)}MB)，最大支持 500MB`, 'error');
      return;
    }

    const zone = document.getElementById('uploadZone');
    const inner = zone.querySelector('.upload-inner');
    const loading = document.getElementById('uploadLoading');
    const loadText = loading.querySelector('p');

    inner.style.display = 'none';
    loading.style.display = 'block';
    loadText.textContent = '上传中... 0%';

    // Use XMLHttpRequest for upload progress
    const form = new FormData();
    form.append('file', file);

    try {
      const data = await new Promise((resolve, reject) => {
        const xhr = new XMLHttpRequest();
        xhr.open('POST', '/api/upload');

        xhr.upload.onprogress = (e) => {
          if (e.lengthComputable) {
            const pct = Math.round((e.loaded / e.total) * 100);
            loadText.textContent = `上传中... ${pct}%`;
          }
        };

        xhr.onload = () => {
          try {
            const resp = JSON.parse(xhr.responseText);
            if (xhr.status >= 200 && xhr.status < 300) {
              resolve(resp);
            } else {
              reject(new Error(resp.detail || '上传失败'));
            }
          } catch {
            reject(new Error('上传失败'));
          }
        };

        xhr.onerror = () => reject(new Error('网络错误'));
        xhr.send(form);
      });

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
    if (!this.fileId || this._processing) return;
    this._processing = true;

    const intensity = parseFloat(document.getElementById('intensity').value);
    const form = new FormData();
    form.append('file_id', this.fileId);
    form.append('effect', effect);
    form.append('intensity', intensity);

    try {
      const res = await fetch('/api/process/effect', { method: 'POST', body: form });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || '启动失败');
      this.currentTaskId = data.task_id;
      this.showProcessing(this.effects[effect].icon, this.effects[effect].name);
    } catch (e) {
      this.toast('启动失败: ' + e.message, 'error');
      this._processing = false;
    }
  },

  async startExtend(mode) {
    if (!this.fileId || this._processing) return;
    this._processing = true;

    const modeCfg = this.extendModes[mode];
    let param = 2;
    if (modeCfg.has_param) {
      param = parseFloat(document.getElementById('extendSlider').value);
    }

    const form = new FormData();
    form.append('file_id', this.fileId);
    form.append('mode', mode);
    form.append('param', param);

    try {
      const res = await fetch('/api/process/extend', { method: 'POST', body: form });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || '启动失败');
      this.currentTaskId = data.task_id;
      this.showProcessing(modeCfg.icon, modeCfg.name);
    } catch (e) {
      this.toast('启动失败: ' + e.message, 'error');
      this._processing = false;
    }
  },

  // ── WebSocket ────────────────────────────────────────
  connectWS() {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) return;

    const proto = location.protocol === 'https:' ? 'wss' : 'ws';
    this.ws = new WebSocket(`${proto}://${location.host}/ws`);

    this.ws.onmessage = (e) => {
      try {
        const data = JSON.parse(e.data);
        if (data.task_id === this.currentTaskId) {
          this.updateProgress(data);
        }
      } catch {}
    };

    this.ws.onclose = () => {
      if (this.currentTaskId && this._processing) {
        clearTimeout(this._reconnectTimer);
        this._reconnectTimer = setTimeout(() => {
          this.connectWS();
          setTimeout(() => {
            if (this.ws?.readyState === WebSocket.OPEN && this.currentTaskId) {
              this.ws.send(JSON.stringify({ action: 'query_task', task_id: this.currentTaskId }));
            }
          }, 500);
        }, 2000);
      }
    };
  },

  // ── UI Updates ───────────────────────────────────────
  showWorkspace(data) {
    this._showSection('workspace');

    const video = document.getElementById('previewVideo');
    video.src = `/api/preview/${data.file_id}`;

    const info = data.info;
    document.getElementById('videoMeta').innerHTML = `
      <span>📐 ${info.width}×${info.height}</span>
      <span>🎞️ ${info.fps.toFixed(1)} FPS</span>
      <span>⏱️ ${info.duration.toFixed(1)}s</span>
      <span>📦 ${(info.size / 1024 / 1024).toFixed(1)} MB</span>
      <span>🎬 ${info.codec}</span>
    `;
  },

  showProcessing(icon, name) {
    this._showSection('processingPanel');
    document.getElementById('processingIcon').textContent = icon;
    document.getElementById('processingTitle').textContent = `正在应用: ${name}`;
    document.getElementById('progressFill').style.width = '0%';
    document.getElementById('progressText').textContent = '0%';
    document.getElementById('progressDetail').textContent = '初始化...';
    this.setStatus('处理中', 'var(--orange)');
  },

  setStatus(text, color) {
    const pill = document.getElementById('statusPill');
    pill.querySelector('span:last-child').textContent = text;
    pill.querySelector('.status-dot').style.background = color;
  },

  updateProgress(data) {
    document.getElementById('progressFill').style.width = data.progress + '%';
    document.getElementById('progressText').textContent = Math.round(data.progress) + '%';
    document.getElementById('progressDetail').textContent = data.message || '';

    if (data.status === 'done') {
      this._processing = false;
      this.setStatus('完成', 'var(--green)');
      setTimeout(() => this.showResult(), 400);
    } else if (data.status === 'error') {
      this._processing = false;
      this.setStatus('出错', 'var(--red)');
      this.toast('处理出错: ' + (data.message || '未知错误'), 'error');
      setTimeout(() => {
        this._showSection('workspace');
        this.setStatus('就绪', 'var(--green)');
      }, 3000);
    }
  },

  showResult() {
    this._showSection('resultPanel');
    const url = `/api/download/${this.currentTaskId}`;
    document.getElementById('resultVideo').src = url;
    document.getElementById('btnDownload').href = url;
  },

  _showSection(id) {
    const sections = ['uploadZone', 'workspace', 'processingPanel', 'resultPanel'];
    for (const s of sections) {
      document.getElementById(s).style.display = s === id ? '' : 'none';
    }
  },

  renderEffects() {
    const grid = document.getElementById('effectsGrid');
    grid.innerHTML = '';
    for (const [key, eff] of Object.entries(this.effects)) {
      const card = this._createCard(eff);
      card.addEventListener('click', () => {
        if (card.classList.contains('processing') || this._processing) return;
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
      const card = this._createCard(mode);
      card.dataset.mode = key;
      card.addEventListener('click', () => {
        if (card.classList.contains('processing') || this._processing) return;
        grid.querySelectorAll('.effect-card').forEach(c => c.classList.remove('selected'));
        card.classList.add('selected');
        this._updateExtendParam(mode);
        card.classList.add('processing');
        this.startExtend(key).finally(() => card.classList.remove('processing'));
      });
      grid.appendChild(card);
    }
  },

  _createCard(data) {
    const card = document.createElement('div');
    card.className = 'effect-card';
    card.innerHTML = `
      <span class="effect-icon">${data.icon}</span>
      <div class="effect-name">${data.name}</div>
      <div class="effect-desc">${data.desc}</div>
    `;
    return card;
  },

  _updateExtendParam(modeCfg) {
    const paramDiv = document.getElementById('extendParam');
    if (!modeCfg.has_param) {
      paramDiv.style.display = 'none';
      return;
    }
    paramDiv.style.display = '';
    document.getElementById('paramLabel').textContent = modeCfg.param_label || '参数';
    const slider = document.getElementById('extendSlider');
    slider.min = modeCfg.param_min || 1;
    slider.max = modeCfg.param_max || 10;
    slider.step = modeCfg.param_step || 1;
    slider.value = modeCfg.param_default || 2;
    document.getElementById('extendVal').textContent = slider.value + 'x';
  },

  // ── Continue Editing ─────────────────────────────────
  async continueEditing() {
    if (!this.currentTaskId) return;

    const btn = document.getElementById('btnBackToEdit');
    btn.textContent = '⏳ 加载中...';
    btn.disabled = true;

    try {
      const form = new FormData();
      form.append('task_id', this.currentTaskId);
      const res = await fetch('/api/import-result', { method: 'POST', body: form });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || '导入失败');

      this.fileId = data.file_id;
      this.currentTaskId = null;
      this.showWorkspace(data);
      this.toast('已加载处理结果，可继续编辑', 'success');
    } catch (e) {
      this.toast('继续编辑失败: ' + e.message, 'error');
    } finally {
      btn.textContent = '🔄 继续编辑';
      btn.disabled = false;
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
      if (e.dataTransfer.files[0]) this.uploadFile(e.dataTransfer.files[0]);
    });
    zone.addEventListener('click', (e) => {
      if (e.target === fileInput || e.target.closest('label')) return;
      fileInput.click();
    });
    fileInput.addEventListener('change', () => {
      if (fileInput.files[0]) this.uploadFile(fileInput.files[0]);
    });

    // Paste support
    document.addEventListener('paste', (e) => {
      const items = e.clipboardData?.items;
      if (!items) return;
      for (const item of items) {
        if (item.type.startsWith('video/') || item.type === 'image/gif') {
          const file = item.getAsFile();
          if (file) this.uploadFile(file);
          break;
        }
      }
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

    // Sliders
    this._bindSlider('intensity', 'intensityVal', v => Math.round(v * 100) + '%');
    this._bindSlider('extendSlider', 'extendVal', v => v + 'x');

    // Navigation buttons
    document.getElementById('btnNew').addEventListener('click', () => this._confirmReset());
    document.getElementById('btnNewVideo').addEventListener('click', () => this._confirmReset());
    document.getElementById('btnBackToEdit').addEventListener('click', () => this.continueEditing());

    // Keyboard shortcuts
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && this._processing) {
        // Can't cancel yet, but show feedback
        this.toast('处理中无法取消，请等待完成', 'error');
      }
    });
  },

  _bindSlider(inputId, displayId, formatter) {
    const input = document.getElementById(inputId);
    const display = document.getElementById(displayId);
    let raf;
    input.addEventListener('input', () => {
      cancelAnimationFrame(raf);
      raf = requestAnimationFrame(() => {
        display.textContent = formatter(input.value);
      });
    });
  },

  _confirmReset() {
    if (this._processing) {
      this.toast('处理中，请等待完成后再上传新视频', 'error');
      return;
    }
    this.reset();
  },

  reset() {
    this.fileId = null;
    this.currentTaskId = null;
    this._processing = false;
    this._showSection('uploadZone');
    document.querySelector('.upload-inner').style.display = '';
    document.getElementById('uploadLoading').style.display = 'none';
    document.getElementById('fileInput').value = '';
    this.setStatus('就绪', 'var(--green)');
  },

  toast(msg, type = '') {
    const container = document.getElementById('toastContainer');
    const el = document.createElement('div');
    el.className = `toast ${type}`;
    el.textContent = msg;
    container.appendChild(el);
    // Limit max toasts
    while (container.children.length > 5) container.firstChild.remove();
    setTimeout(() => { el.style.opacity = '0'; setTimeout(() => el.remove(), 300); }, 4000);
  },
};

document.addEventListener('DOMContentLoaded', () => App.init());
