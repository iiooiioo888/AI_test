/* ═══════════════════════════════════════════════════════════
   AI Video Studio — Frontend Logic (Dark Refined)
   ═══════════════════════════════════════════════════════════ */

const App = {
  fileId: null,
  currentTaskId: null,
  ws: null,
  effects: {},
  extendModes: {},
  _reconnectTimer: null,
  _processing: false,
  _currentStep: 0, // 0=upload, 1=workspace, 2=processing, 3=result

  async init() {
    this.initParticles();
    this.bindEvents();
    await this.loadEffects();
    this.connectWS();
  },

  // ── Particle Background ───────────────────────────
  initParticles() {
    const canvas = document.getElementById('bgCanvas');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    let w, h, particles = [];
    const COUNT = 40;
    const SPEED = 0.15;

    function resize() {
      w = canvas.width = window.innerWidth;
      h = canvas.height = window.innerHeight;
    }
    resize();
    window.addEventListener('resize', resize);

    for (let i = 0; i < COUNT; i++) {
      particles.push({
        x: Math.random() * w,
        y: Math.random() * h,
        r: Math.random() * 1.5 + 0.5,
        dx: (Math.random() - 0.5) * SPEED,
        dy: (Math.random() - 0.5) * SPEED,
        o: Math.random() * 0.3 + 0.1,
      });
    }

    const draw = () => {
      ctx.clearRect(0, 0, w, h);
      for (const p of particles) {
        p.x += p.dx;
        p.y += p.dy;
        if (p.x < 0) p.x = w;
        if (p.x > w) p.x = 0;
        if (p.y < 0) p.y = h;
        if (p.y > h) p.y = 0;
        ctx.beginPath();
        ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(124, 92, 252, ${p.o})`;
        ctx.fill();
      }
      // Connect nearby particles
      for (let i = 0; i < particles.length; i++) {
        for (let j = i + 1; j < particles.length; j++) {
          const dx = particles[i].x - particles[j].x;
          const dy = particles[i].y - particles[j].y;
          const dist = Math.sqrt(dx * dx + dy * dy);
          if (dist < 180) {
            ctx.beginPath();
            ctx.moveTo(particles[i].x, particles[i].y);
            ctx.lineTo(particles[j].x, particles[j].y);
            ctx.strokeStyle = `rgba(124, 92, 252, ${0.06 * (1 - dist / 180)})`;
            ctx.lineWidth = 0.5;
            ctx.stroke();
          }
        }
      }
      requestAnimationFrame(draw);
    };
    draw();
  },

  // ── Step Indicator ────────────────────────────────
  setStep(step) {
    this._currentStep = step;
    const items = document.querySelectorAll('.step-item');
    const connectors = document.querySelectorAll('.step-connector');
    items.forEach((el, i) => {
      el.classList.remove('active', 'completed');
      if (i < step) el.classList.add('completed');
      if (i === step) el.classList.add('active');
    });
    connectors.forEach((el, i) => {
      el.classList.toggle('active', i < step);
    });
    // Allow clicking completed steps to go back
    items.forEach((el, i) => {
      if (i < step && step !== 2) {
        // Can go back to completed steps (except during processing)
        el.style.cursor = 'pointer';
      } else {
        el.style.cursor = 'default';
      }
    });
  },

  // ── API ───────────────────────────────────────────
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
    const loadText = document.getElementById('uploadProgressText');
    const fillBar = document.getElementById('uploadProgressFill');

    inner.style.display = 'none';
    loading.style.display = 'block';
    loadText.textContent = '上传中... 0%';
    fillBar.style.width = '0%';

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
            fillBar.style.width = pct + '%';
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
      fillBar.style.width = '0%';
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

  // ── WebSocket ──────────────────────────────────────
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

  // ── UI State Management ────────────────────────────
  showWorkspace(data) {
    this._showSection('workspace');
    this.setStep(1);

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
    this.setStep(2);
    document.getElementById('processingIcon').textContent = icon;
    document.getElementById('processingTitle').textContent = `正在应用`;
    document.getElementById('processingEffectName').textContent = name;
    document.getElementById('progressFill').style.width = '0%';
    document.getElementById('progressText').textContent = '0%';
    document.getElementById('progressDetail').textContent = '初始化...';
    this.setStatus('处理中', 'var(--orange)');
  },

  setStatus(text, color) {
    const pill = document.getElementById('statusPill');
    pill.querySelector('span:last-child').textContent = text;
    const dot = pill.querySelector('.status-dot');
    dot.style.background = color;
    // Update glow color
    const glowMap = {
      'var(--orange)': 'rgba(251,146,60,0.3)',
      'var(--green)': 'var(--green-glow)',
      'var(--red)': 'var(--red-glow)',
    };
    dot.style.boxShadow = `0 0 8px ${glowMap[color] || 'transparent'}`;
  },

  updateProgress(data) {
    const pct = Math.round(data.progress);
    document.getElementById('progressFill').style.width = data.progress + '%';
    document.getElementById('progressText').textContent = pct + '%';
    document.getElementById('progressDetail').textContent = data.message || '';

    if (data.status === 'done') {
      this._processing = false;
      this.setStatus('完成', 'var(--green)');
      setTimeout(() => this.showResult(), 500);
    } else if (data.status === 'error') {
      this._processing = false;
      this.setStatus('出错', 'var(--red)');
      this.toast('处理出错: ' + (data.message || '未知错误'), 'error');
      setTimeout(() => {
        this._showSection('workspace');
        this.setStep(1);
        this.setStatus('就绪', 'var(--green)');
      }, 3000);
    }
  },

  showResult() {
    this._showSection('resultPanel');
    this.setStep(3);
    const url = `/api/download/${this.currentTaskId}`;
    document.getElementById('resultVideo').src = url;
    document.getElementById('btnDownload').href = url;
  },

  _showSection(id) {
    const sections = ['uploadZone', 'workspace', 'processingPanel', 'resultPanel'];
    for (const s of sections) {
      const el = document.getElementById(s);
      if (s === id) {
        el.style.display = '';
        el.style.animation = 'none';
        el.offsetHeight; // trigger reflow
        el.style.animation = '';
      } else {
        el.style.display = 'none';
      }
    }
  },

  // ── Continue Editing ───────────────────────────────
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
      btn.innerHTML = '<span>🔄</span> 继续编辑';
      btn.disabled = false;
    }
  },

  // ── Render ─────────────────────────────────────────
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

  // ── Events ─────────────────────────────────────────
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

    // Navigation
    document.getElementById('btnBackToUpload').addEventListener('click', () => {
      if (!this._processing) this._confirmReset();
    });
    document.getElementById('btnNewVideo').addEventListener('click', () => this._confirmReset());
    document.getElementById('btnBackToEdit').addEventListener('click', () => this.continueEditing());

    // Step bar clicks (go back to completed steps)
    document.getElementById('stepsBar').addEventListener('click', (e) => {
      const stepEl = e.target.closest('.step-item');
      if (!stepEl || this._processing) return;
      const step = parseInt(stepEl.dataset.step);
      if (step < this._currentStep && this._currentStep !== 2) {
        if (step === 0) this._confirmReset();
        if (step === 1 && this._currentStep === 3) {
          this._showSection('workspace');
          this.setStep(1);
        }
      }
    });

    // Keyboard
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && this._processing) {
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
    this.setStep(0);
    document.querySelector('.upload-inner').style.display = '';
    document.getElementById('uploadLoading').style.display = 'none';
    document.getElementById('uploadProgressFill').style.width = '0%';
    document.getElementById('fileInput').value = '';
    this.setStatus('就绪', 'var(--green)');
  },

  toast(msg, type = '') {
    const container = document.getElementById('toastContainer');
    const el = document.createElement('div');
    el.className = `toast ${type}`;
    el.textContent = msg;
    container.appendChild(el);
    while (container.children.length > 5) container.firstChild.remove();
    setTimeout(() => {
      el.style.opacity = '0';
      el.style.transform = 'translateX(50px)';
      setTimeout(() => el.remove(), 300);
    }, 4000);
  },
};

document.addEventListener('DOMContentLoaded', () => App.init());
