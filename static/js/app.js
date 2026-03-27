/* ═══════════════════════════════════════════════════════════
   AVP Studio — Frontend Logic (Enterprise Edition)
   ═══════════════════════════════════════════════════════════ */

const App = {
  fileId: null,
  currentTaskId: null,
  ws: null,
  effects: {},
  extendModes: {},
  _reconnectTimer: null,
  _processing: false,
  _currentStep: 0,
  _currentSection: 'video',

  // ── Narrative State ────────────────────────────────
  scenes: [],
  activeSceneId: null,
  graphNodes: [],
  graphEdges: [],

  async init() {
    this.initParticles();
    this.bindEvents();
    this.bindNavEvents();
    await this.loadEffects();
    this.connectWS();
    this.loadDemoScenes();
  },

  // ════════════════════════════════════════════════════════
  //  Navigation
  // ════════════════════════════════════════════════════════

  bindNavEvents() {
    document.querySelectorAll('.nav-tab').forEach(tab => {
      tab.addEventListener('click', () => {
        const section = tab.dataset.section;
        this.switchSection(section);
      });
    });
  },

  switchSection(section) {
    this._currentSection = section;
    document.querySelectorAll('.nav-tab').forEach(t => t.classList.remove('active'));
    document.querySelector(`.nav-tab[data-section="${section}"]`).classList.add('active');
    document.querySelectorAll('.section').forEach(s => s.classList.remove('active'));
    document.getElementById(`section-${section}`).classList.add('active');

    if (section === 'graph') {
      this.renderGraph();
    }
  },

  // ════════════════════════════════════════════════════════
  //  Particle Background
  // ════════════════════════════════════════════════════════

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
        x: Math.random() * w, y: Math.random() * h,
        r: Math.random() * 1.5 + 0.5,
        dx: (Math.random() - 0.5) * SPEED,
        dy: (Math.random() - 0.5) * SPEED,
        o: Math.random() * 0.3 + 0.1,
      });
    }

    const draw = () => {
      ctx.clearRect(0, 0, w, h);
      for (const p of particles) {
        p.x += p.dx; p.y += p.dy;
        if (p.x < 0) p.x = w; if (p.x > w) p.x = 0;
        if (p.y < 0) p.y = h; if (p.y > h) p.y = 0;
        ctx.beginPath();
        ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(124, 92, 252, ${p.o})`;
        ctx.fill();
      }
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

  // ════════════════════════════════════════════════════════
  //  Step Indicator
  // ════════════════════════════════════════════════════════

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
    items.forEach((el, i) => {
      el.style.cursor = (i < step && step !== 2) ? 'pointer' : 'default';
    });
  },

  // ════════════════════════════════════════════════════════
  //  API — Video Processing
  // ════════════════════════════════════════════════════════

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
            if (xhr.status >= 200 && xhr.status < 300) resolve(resp);
            else reject(new Error(resp.detail || '上传失败'));
          } catch { reject(new Error('上传失败')); }
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

  // ════════════════════════════════════════════════════════
  //  WebSocket
  // ════════════════════════════════════════════════════════

  connectWS() {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) return;
    const proto = location.protocol === 'https:' ? 'wss' : 'ws';
    this.ws = new WebSocket(`${proto}://${location.host}/ws`);
    this.ws.onmessage = (e) => {
      try {
        const data = JSON.parse(e.data);
        if (data.task_id === this.currentTaskId) this.updateProgress(data);
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

  // ════════════════════════════════════════════════════════
  //  UI State Management — Video
  // ════════════════════════════════════════════════════════

  showWorkspace(data) {
    this._showVideoSection('workspace');
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
    this._showVideoSection('processingPanel');
    this.setStep(2);
    document.getElementById('processingIcon').textContent = icon;
    document.getElementById('processingTitle').textContent = '正在应用';
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
        this._showVideoSection('workspace');
        this.setStep(1);
        this.setStatus('就绪', 'var(--green)');
      }, 3000);
    }
  },

  showResult() {
    this._showVideoSection('resultPanel');
    this.setStep(3);
    const url = `/api/download/${this.currentTaskId}`;
    document.getElementById('resultVideo').src = url;
    document.getElementById('btnDownload').href = url;
  },

  _showVideoSection(id) {
    const sections = ['uploadZone', 'workspace', 'processingPanel', 'resultPanel'];
    for (const s of sections) {
      const el = document.getElementById(s);
      if (s === id) {
        el.style.display = '';
        el.style.animation = 'none';
        el.offsetHeight;
        el.style.animation = '';
      } else {
        el.style.display = 'none';
      }
    }
  },

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

  // ════════════════════════════════════════════════════════
  //  Render — Video Effects
  // ════════════════════════════════════════════════════════

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
    if (!modeCfg.has_param) { paramDiv.style.display = 'none'; return; }
    paramDiv.style.display = '';
    document.getElementById('paramLabel').textContent = modeCfg.param_label || '参数';
    const slider = document.getElementById('extendSlider');
    slider.min = modeCfg.param_min || 1;
    slider.max = modeCfg.param_max || 10;
    slider.step = modeCfg.param_step || 1;
    slider.value = modeCfg.param_default || 2;
    document.getElementById('extendVal').textContent = slider.value + 'x';
  },

  // ════════════════════════════════════════════════════════
  //  Narrative — Demo Data & Scene Management
  // ════════════════════════════════════════════════════════

  loadDemoScenes() {
    this.scenes = [
      {
        id: 's1', title: '序幕：城市甦醒', state: 'COMPLETED', version: 3,
        branch: 'main', updated: '2026-03-26',
        narrative: { beat: '黎明時分，攝影師在空曠的屋頂等待日出', desc: '城市天際線從黑暗中浮現，第一縷陽光照亮摩天大樓的玻璃幕牆', arc: 'tension', conflict: '時間緊迫 vs 完美構圖' },
        dialogue: [{ char: '旁白', text: '每一個黎明，都是一次重生的機會' }],
        visual: { setting: '城市屋頂', time: 'dawn', camera: 'wide', lighting: 'natural' },
        tags: ['開場', '城市'], duration: 45, complexity: 0.3,
        characters: ['c1'], props: ['p1'],
        audit: [{ action: 'CREATE', time: '2026-03-24 10:00' }, { action: 'TRANSITION: DRAFT→REVIEW', time: '2026-03-25 14:30' }, { action: 'TRANSITION: REVIEW→COMPLETED', time: '2026-03-26 09:00' }]
      },
      {
        id: 's2', title: '第一幕：咖啡邂逅', state: 'LOCKED', version: 2,
        branch: 'main', updated: '2026-03-27',
        narrative: { beat: '主角在咖啡館遇見神秘人物', desc: '午後陽光透過百葉窗灑落，一個戴墨鏡的女人走向主角的桌子', arc: 'surprise', conflict: '信任 vs 懷疑' },
        dialogue: [
          { char: '林薇', text: '你拍的照片... 有種說不出的孤獨感' },
          { char: '主角', text: '孤獨？我只是在記錄真實' }
        ],
        visual: { setting: '復古咖啡館', time: 'afternoon', camera: 'medium', lighting: 'soft' },
        tags: ['對話', '咖啡館'], duration: 90, complexity: 0.6,
        characters: ['c1', 'c2'], props: ['p2', 'p3'],
        audit: [{ action: 'CREATE', time: '2026-03-26 15:00' }, { action: 'TRANSITION: DRAFT→LOCKED', time: '2026-03-27 11:00' }]
      },
      {
        id: 's3', title: '第二幕：追逐真相', state: 'REVIEW', version: 1,
        branch: 'main', updated: '2026-03-27',
        narrative: { beat: '主角跟蹤線索來到廢棄工廠', desc: '雨夜中的工業區，生鏽的鐵門後藏著不為人知的秘密', arc: 'suspense', conflict: '好奇心 vs 危險' },
        dialogue: [{ char: '主角', text: '這就是他們不想讓我看見的東西...' }],
        visual: { setting: '廢棄工廠', time: 'night', camera: 'tracking', lighting: 'low_key' },
        tags: ['追逐', '懸疑', '雨夜'], duration: 120, complexity: 0.8,
        characters: ['c1'], props: ['p4', 'p5'],
        audit: [{ action: 'CREATE', time: '2026-03-27 08:00' }, { action: 'TRANSITION: DRAFT→REVIEW', time: '2026-03-27 16:00' }]
      },
      {
        id: 's4', title: '第三幕：真相大白', state: 'DRAFT', version: 1,
        branch: 'main', updated: '2026-03-27',
        narrative: { beat: '所有線索匯聚，真相終於揭曉', desc: '回到最初的城市屋頂，但現在一切都不同了', arc: 'triumph', conflict: '過去 vs 現在' },
        dialogue: [],
        visual: { setting: '城市屋頂（夜）', time: 'night', camera: 'aerial', lighting: 'dramatic' },
        tags: ['高潮', '城市'], duration: 60, complexity: 0.5,
        characters: ['c1', 'c2'], props: ['p1'],
        audit: [{ action: 'CREATE', time: '2026-03-27 17:00' }]
      }
    ];

    this.renderSceneList();
    this.updateStats();
  },

  renderSceneList() {
    const list = document.getElementById('sceneList');
    list.innerHTML = '';
    this.scenes.forEach(scene => {
      const el = document.createElement('div');
      el.className = `scene-item ${scene.id === this.activeSceneId ? 'active' : ''}`;
      const stateClass = scene.state.toLowerCase();
      el.innerHTML = `
        <div class="scene-item-title">
          <span class="scene-state-dot ${stateClass}"></span>
          ${scene.title}
        </div>
        <div class="scene-item-meta">
          <span>v${scene.version}</span>
          <span>${scene.state}</span>
          <span>${scene.duration}s</span>
        </div>
      `;
      el.addEventListener('click', () => this.selectScene(scene.id));
      list.appendChild(el);
    });
  },

  selectScene(id) {
    this.activeSceneId = id;
    this.renderSceneList();
    const scene = this.scenes.find(s => s.id === id);
    if (!scene) return;

    document.getElementById('editorEmpty').style.display = 'none';
    document.getElementById('editorContent').style.display = '';

    // Fill editor
    document.getElementById('sceneTitle').value = scene.title;
    document.getElementById('sceneVersion').textContent = scene.version;
    document.getElementById('sceneBranch').textContent = scene.branch;
    document.getElementById('sceneUpdated').textContent = scene.updated;

    const badge = document.getElementById('stateBadge');
    badge.textContent = scene.state;
    badge.className = `state-badge ${scene.state.toLowerCase()}`;

    document.getElementById('narrativeBeat').value = scene.narrative.beat || '';
    document.getElementById('narrativeDesc').value = scene.narrative.desc || '';
    document.getElementById('emotionalArc').value = scene.narrative.arc || '';
    document.getElementById('narrativeConflict').value = scene.narrative.conflict || '';

    // Dialogue
    const dl = document.getElementById('dialogueList');
    dl.innerHTML = '';
    (scene.dialogue || []).forEach(d => this._addDialogueLine(d.char, d.text));

    // Visual
    document.getElementById('visualSetting').value = scene.visual?.setting || '';
    document.getElementById('visualTime').value = scene.visual?.time || '';
    document.getElementById('cameraShot').value = scene.visual?.camera || 'medium';
    document.getElementById('lightingStyle').value = scene.visual?.lighting || 'natural';

    // Properties
    document.getElementById('durationEst').value = scene.duration || 30;
    document.getElementById('complexityScore').value = scene.complexity || 0.5;
    document.getElementById('complexityVal').textContent = (scene.complexity || 0.5).toFixed(1);

    // Tags
    const tagList = document.getElementById('tagList');
    tagList.innerHTML = '';
    (scene.tags || []).forEach(t => this._addTag(t));

    // State machine
    this._renderStateFlow(scene.state);
    this._renderStateActions(scene.state);

    // Dependencies
    this._renderDeps('characterDeps', scene.characters, 'character');
    this._renderDeps('propDeps', scene.props, 'prop');

    // Audit
    const auditEl = document.getElementById('auditLog');
    if (scene.audit && scene.audit.length) {
      auditEl.innerHTML = scene.audit.map(a => `
        <div class="audit-entry">
          <span class="audit-action">${a.action}</span>
          <span class="audit-time">${a.time}</span>
        </div>
      `).join('');
    } else {
      auditEl.innerHTML = '<div class="audit-empty">尚無操作記錄</div>';
    }
  },

  _addDialogueLine(char = '', text = '') {
    const dl = document.getElementById('dialogueList');
    const item = document.createElement('div');
    item.className = 'dialogue-item';
    item.innerHTML = `
      <input type="text" placeholder="角色名" value="${char}">
      <input type="text" placeholder="對白內容..." value="${text}">
      <button class="dialogue-remove" title="刪除">×</button>
    `;
    item.querySelector('.dialogue-remove').addEventListener('click', () => item.remove());
    dl.appendChild(item);
  },

  _addTag(text) {
    const tagList = document.getElementById('tagList');
    const tag = document.createElement('span');
    tag.className = 'tag-item';
    tag.innerHTML = `${text} <span class="tag-remove">×</span>`;
    tag.querySelector('.tag-remove').addEventListener('click', () => tag.remove());
    tagList.appendChild(tag);
  },

  _renderDeps(containerId, items, type) {
    const el = document.getElementById(containerId);
    if (!items || !items.length) {
      el.innerHTML = '<div class="dep-empty">尚無關聯</div>';
      return;
    }
    const labels = {
      c1: '主角 (攝影師)', c2: '林薇 (神秘女人)', c3: '老張 (工廠守衛)',
      p1: '相機', p2: '墨鏡', p3: '咖啡杯', p4: '手電筒', p5: '鐵門鑰匙'
    };
    el.innerHTML = items.map(id => `
      <div class="dep-item">
        <span class="dep-dot ${type}"></span>
        <span>${labels[id] || id}</span>
      </div>
    `).join('');
  },

  _renderStateFlow(currentState) {
    const states = ['DRAFT', 'REVIEW', 'LOCKED', 'COMPLETED'];
    const nodes = document.querySelectorAll('.state-node');
    nodes.forEach(n => {
      const s = n.dataset.state;
      n.classList.remove('active', 'completed-node');
      if (s === currentState) n.classList.add('active');
      else if (states.indexOf(s) < states.indexOf(currentState)) n.classList.add('completed-node');
    });
  },

  _renderStateActions(currentState) {
    const actions = document.getElementById('stateActions');
    const transitions = {
      DRAFT: [{ label: '提交審核 → REVIEW', to: 'REVIEW' }],
      REVIEW: [{ label: '✓ 通過 → LOCKED', to: 'LOCKED' }, { label: '✗ 退回 DRAFT', to: 'DRAFT' }],
      LOCKED: [{ label: '✓ 完成 → COMPLETED', to: 'COMPLETED' }, { label: '✗ 退回 DRAFT', to: 'DRAFT' }],
      COMPLETED: [{ label: '↺ 重新編輯 → DRAFT', to: 'DRAFT' }]
    };
    const valid = transitions[currentState] || [];
    actions.innerHTML = valid.map(t => `
      <button class="btn-mini state-transition-btn" data-to="${t.to}">${t.label}</button>
    `).join('');
    actions.querySelectorAll('.state-transition-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        const to = btn.dataset.to;
        const scene = this.scenes.find(s => s.id === this.activeSceneId);
        if (!scene) return;
        scene.state = to;
        scene.version++;
        scene.updated = new Date().toISOString().split('T')[0];
        scene.audit = scene.audit || [];
        scene.audit.push({ action: `TRANSITION: ${btn.closest('.state-actions').previousElementSibling ? currentState : currentState}→${to}`, time: new Date().toLocaleString() });
        this.toast(`狀態已轉換: ${currentState} → ${to}`, 'success');
        this.selectScene(this.activeSceneId);
        this.renderSceneList();
        this.updateStats();
      });
    });
  },

  updateStats() {
    document.getElementById('statTotal').textContent = this.scenes.length;
    document.getElementById('statDraft').textContent = this.scenes.filter(s => s.state === 'DRAFT').length;
    document.getElementById('statLocked').textContent = this.scenes.filter(s => s.state === 'LOCKED' || s.state === 'COMPLETED').length;
  },

  // ════════════════════════════════════════════════════════
  //  Ripple Analysis
  // ════════════════════════════════════════════════════════

  analyzeRipple() {
    const scene = this.scenes.find(s => s.id === this.activeSceneId);
    if (!scene) return;

    const results = document.getElementById('rippleResults');
    results.innerHTML = '<div class="ripple-empty">分析中...</div>';

    setTimeout(() => {
      // Simulated ripple analysis
      const conflicts = [];
      const idx = this.scenes.indexOf(scene);

      // Check if characters that appear later have been "killed" or removed
      if (scene.id === 's1') {
        // Scene 1 is completed, checking downstream
        if (this.scenes[1]?.state !== 'DRAFT') {
          conflicts.push({
            title: '角色連續性警告',
            detail: '場景「咖啡邂逅」引用了主角 (c1)，若修改主角描述將影響後續場景的一致性'
          });
        }
      }

      if (scene.id === 's3') {
        conflicts.push({
          title: '道具邏輯衝突',
          detail: '場景「追逐真相」中使用手電筒 (p4)，但前一場景「咖啡邂逅」未建立此道具的引入'
        });
      }

      if (conflicts.length) {
        results.innerHTML = conflicts.map(c => `
          <div class="ripple-conflict">
            <div class="conflict-title">⚠️ ${c.title}</div>
            <div class="conflict-detail">${c.detail}</div>
          </div>
        `).join('');
      } else {
        results.innerHTML = '<div class="ripple-safe">✓ 未發現衝突，劇情邏輯連貫</div>';
      }
    }, 800);
  },

  // ════════════════════════════════════════════════════════
  //  Graph View
  // ════════════════════════════════════════════════════════

  renderGraph() {
    const canvas = document.getElementById('graphCanvas');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    const rect = canvas.parentElement.getBoundingClientRect();
    canvas.width = rect.width;
    canvas.height = Math.max(500, rect.height);

    const w = canvas.width;
    const h = canvas.height;

    // Define nodes
    const nodes = [
      { id: 's1', type: 'scene', label: '序幕：城市甦醒', x: w * 0.2, y: h * 0.3, color: '#7c5cfc' },
      { id: 's2', type: 'scene', label: '咖啡邂逅', x: w * 0.45, y: h * 0.25, color: '#7c5cfc' },
      { id: 's3', type: 'scene', label: '追逐真相', x: w * 0.7, y: h * 0.35, color: '#7c5cfc' },
      { id: 's4', type: 'scene', label: '真相大白', x: w * 0.85, y: h * 0.6, color: '#7c5cfc' },
      { id: 'c1', type: 'character', label: '主角', x: w * 0.3, y: h * 0.65, color: '#5cccfc' },
      { id: 'c2', type: 'character', label: '林薇', x: w * 0.55, y: h * 0.7, color: '#5cccfc' },
      { id: 'p1', type: 'prop', label: '相機', x: w * 0.15, y: h * 0.75, color: '#fb923c' },
      { id: 'p2', type: 'prop', label: '墨鏡', x: w * 0.6, y: h * 0.5, color: '#fb923c' },
    ];

    const edges = [
      { from: 's1', to: 's2', type: 'leads', color: '#7c5cfc' },
      { from: 's2', to: 's3', type: 'leads', color: '#7c5cfc' },
      { from: 's3', to: 's4', type: 'leads', color: '#7c5cfc' },
      { from: 's1', to: 'c1', type: 'contains', color: '#5cccfc' },
      { from: 's2', to: 'c1', type: 'contains', color: '#5cccfc' },
      { from: 's2', to: 'c2', type: 'contains', color: '#5cccfc' },
      { from: 's3', to: 'c1', type: 'contains', color: '#5cccfc' },
      { from: 's4', to: 'c1', type: 'contains', color: '#5cccfc' },
      { from: 's4', to: 'c2', type: 'contains', color: '#5cccfc' },
      { from: 's1', to: 'p1', type: 'requires', color: '#fb923c' },
      { from: 's2', to: 'p2', type: 'requires', color: '#fb923c' },
    ];

    this._graphNodes = nodes;
    this._graphEdges = edges;

    // Draw
    ctx.clearRect(0, 0, w, h);

    // Draw edges
    edges.forEach(e => {
      const from = nodes.find(n => n.id === e.from);
      const to = nodes.find(n => n.id === e.to);
      if (!from || !to) return;
      ctx.beginPath();
      ctx.moveTo(from.x, from.y);
      ctx.lineTo(to.x, to.y);
      ctx.strokeStyle = e.color + '40';
      ctx.lineWidth = e.type === 'leads' ? 2 : 1;
      if (e.type === 'leads') ctx.setLineDash([]);
      else ctx.setLineDash([4, 4]);
      ctx.stroke();
      ctx.setLineDash([]);

      // Arrow for leads
      if (e.type === 'leads') {
        const angle = Math.atan2(to.y - from.y, to.x - from.x);
        const headLen = 10;
        const ax = to.x - Math.cos(angle) * 28;
        const ay = to.y - Math.sin(angle) * 28;
        ctx.beginPath();
        ctx.moveTo(ax, ay);
        ctx.lineTo(ax - headLen * Math.cos(angle - 0.4), ay - headLen * Math.sin(angle - 0.4));
        ctx.lineTo(ax - headLen * Math.cos(angle + 0.4), ay - headLen * Math.sin(angle + 0.4));
        ctx.closePath();
        ctx.fillStyle = e.color + '80';
        ctx.fill();
      }
    });

    // Draw nodes
    nodes.forEach(n => {
      const r = n.type === 'scene' ? 24 : 16;
      // Glow
      ctx.beginPath();
      ctx.arc(n.x, n.y, r + 8, 0, Math.PI * 2);
      ctx.fillStyle = n.color + '15';
      ctx.fill();
      // Node
      ctx.beginPath();
      ctx.arc(n.x, n.y, r, 0, Math.PI * 2);
      ctx.fillStyle = n.color + '30';
      ctx.fill();
      ctx.strokeStyle = n.color;
      ctx.lineWidth = 2;
      ctx.stroke();
      // Label
      ctx.fillStyle = '#e4e4f0';
      ctx.font = '11px Inter, sans-serif';
      ctx.textAlign = 'center';
      ctx.fillText(n.label, n.x, n.y + r + 16);
    });

    // Click handler
    canvas.onclick = (ev) => {
      const bcr = canvas.getBoundingClientRect();
      const mx = ev.clientX - bcr.left;
      const my = ev.clientY - bcr.top;
      let clicked = null;
      for (const n of nodes) {
        const r = n.type === 'scene' ? 24 : 16;
        if (Math.sqrt((mx - n.x) ** 2 + (my - n.y) ** 2) < r + 4) {
          clicked = n; break;
        }
      }
      this._showGraphDetail(clicked);
    };
  },

  _showGraphDetail(node) {
    const el = document.getElementById('graphNodeDetail');
    if (!node) {
      el.innerHTML = '<div class="dep-empty">點擊圖譜節點查看詳情</div>';
      return;
    }
    const typeLabels = { scene: '場景', character: '角色', prop: '道具' };
    const connections = this._graphEdges.filter(e => e.from === node.id || e.to === node.id);
    const connectedNodes = connections.map(e => {
      const otherId = e.from === node.id ? e.to : e.from;
      const other = this._graphNodes.find(n => n.id === otherId);
      return { ...other, relation: e.type };
    });

    el.innerHTML = `
      <div class="node-title">
        <span class="node-type ${node.type}">${typeLabels[node.type]}</span>
        ${node.label}
      </div>
      <dl class="node-props">
        <dt>ID</dt><dd>${node.id}</dd>
        <dt>關聯 (${connectedNodes.length})</dt>
        <dd>${connectedNodes.map(c => `
          <div class="dep-item" style="margin-top:4px">
            <span class="dep-dot ${c.type}"></span>
            <span>${c.label}</span>
            <span style="margin-left:auto;font-size:10px;color:var(--text-mute)">${c.relation}</span>
          </div>
        `).join('')}</dd>
      </dl>
    `;
  },

  // ════════════════════════════════════════════════════════
  //  Events
  // ════════════════════════════════════════════════════════

  bindEvents() {
    const zone = document.getElementById('uploadZone');
    const fileInput = document.getElementById('fileInput');

    // Drag & drop
    zone.addEventListener('dragover', (e) => { e.preventDefault(); zone.classList.add('drag-over'); });
    zone.addEventListener('dragleave', () => zone.classList.remove('drag-over'));
    zone.addEventListener('drop', (e) => {
      e.preventDefault(); zone.classList.remove('drag-over');
      if (e.dataTransfer.files[0]) this.uploadFile(e.dataTransfer.files[0]);
    });
    zone.addEventListener('click', (e) => {
      if (e.target === fileInput || e.target.closest('label')) return;
      fileInput.click();
    });
    fileInput.addEventListener('change', () => {
      if (fileInput.files[0]) this.uploadFile(fileInput.files[0]);
    });

    // Paste
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

    // Video tabs
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
    this._bindSlider('complexityScore', 'complexityVal', v => parseFloat(v).toFixed(1));

    // Navigation
    document.getElementById('btnBackToUpload').addEventListener('click', () => {
      if (!this._processing) this._confirmReset();
    });
    document.getElementById('btnNewVideo').addEventListener('click', () => this._confirmReset());
    document.getElementById('btnBackToEdit').addEventListener('click', () => this.continueEditing());

    // Step bar
    document.getElementById('stepsBar').addEventListener('click', (e) => {
      const stepEl = e.target.closest('.step-item');
      if (!stepEl || this._processing) return;
      const step = parseInt(stepEl.dataset.step);
      if (step < this._currentStep && this._currentStep !== 2) {
        if (step === 0) this._confirmReset();
        if (step === 1 && this._currentStep === 3) {
          this._showVideoSection('workspace');
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

    // Narrative events
    document.getElementById('btnNewScene').addEventListener('click', () => this._createNewScene());
    document.getElementById('btnAddDialogue').addEventListener('click', () => this._addDialogueLine());
    document.getElementById('btnAnalyze').addEventListener('click', () => this.analyzeRipple());
    document.getElementById('btnSave').addEventListener('click', () => this._saveScene());
    document.getElementById('btnDiscard').addEventListener('click', () => {
      if (this.activeSceneId) this.selectScene(this.activeSceneId);
    });

    // Tag input
    document.getElementById('tagInput').addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && e.target.value.trim()) {
        this._addTag(e.target.value.trim());
        e.target.value = '';
      }
    });

    // Graph controls
    document.getElementById('btnGraphRefresh')?.addEventListener('click', () => this.renderGraph());
    document.getElementById('btnZoomFit')?.addEventListener('click', () => this.renderGraph());
  },

  _createNewScene() {
    const id = 's' + (this.scenes.length + 1);
    const scene = {
      id, title: `新場景 ${this.scenes.length + 1}`, state: 'DRAFT', version: 1,
      branch: 'main', updated: new Date().toISOString().split('T')[0],
      narrative: { beat: '', desc: '', arc: '', conflict: '' },
      dialogue: [], visual: { setting: '', time: '', camera: 'medium', lighting: 'natural' },
      tags: [], duration: 30, complexity: 0.5,
      characters: [], props: [],
      audit: [{ action: 'CREATE', time: new Date().toLocaleString() }]
    };
    this.scenes.push(scene);
    this.renderSceneList();
    this.updateStats();
    this.selectScene(id);
    this.toast('新場景已創建', 'success');
  },

  _saveScene() {
    const scene = this.scenes.find(s => s.id === this.activeSceneId);
    if (!scene) return;

    scene.title = document.getElementById('sceneTitle').value;
    scene.narrative.beat = document.getElementById('narrativeBeat').value;
    scene.narrative.desc = document.getElementById('narrativeDesc').value;
    scene.narrative.arc = document.getElementById('emotionalArc').value;
    scene.narrative.conflict = document.getElementById('narrativeConflict').value;
    scene.visual.setting = document.getElementById('visualSetting').value;
    scene.visual.time = document.getElementById('visualTime').value;
    scene.visual.camera = document.getElementById('cameraShot').value;
    scene.visual.lighting = document.getElementById('lightingStyle').value;
    scene.visual.action = document.getElementById('visualAction')?.value || '';
    scene.duration = parseInt(document.getElementById('durationEst').value) || 30;
    scene.complexity = parseFloat(document.getElementById('complexityScore').value) || 0.5;

    // Dialogue
    const dItems = document.querySelectorAll('.dialogue-item');
    scene.dialogue = Array.from(dItems).map(item => {
      const inputs = item.querySelectorAll('input');
      return { char: inputs[0].value, text: inputs[1].value };
    }).filter(d => d.text);

    // Tags
    scene.tags = Array.from(document.querySelectorAll('.tag-item')).map(t => t.textContent.replace('×', '').trim());

    scene.version++;
    scene.updated = new Date().toISOString().split('T')[0];
    scene.audit.push({ action: 'SAVE', time: new Date().toLocaleString() });

    this.renderSceneList();
    this.toast('場景已保存', 'success');
  },

  _bindSlider(inputId, displayId, formatter) {
    const input = document.getElementById(inputId);
    const display = document.getElementById(displayId);
    if (!input || !display) return;
    let raf;
    input.addEventListener('input', () => {
      cancelAnimationFrame(raf);
      raf = requestAnimationFrame(() => { display.textContent = formatter(input.value); });
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
    this._showVideoSection('uploadZone');
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
