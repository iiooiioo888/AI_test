/**
 * AVP Studio - Main Application
 * 完整的 frontend 應用邏輯
 */

// ═══════════════════════════════════════════════════════════
// Global App State
// ═══════════════════════════════════════════════════════════

const app = {
  state: {
    currentSection: 'dashboard',
    currentProject: null,
    currentScene: null,
    projects: [],
    scenes: [],
    generationTasks: [],
    healthStatus: 'unknown',
  },

  // Initialize App
  async init() {
    console.log('🎬 AVP Studio initializing...');
    
    // Check health
    await this.checkHealth();
    
    // Load data
    await this.loadDashboard();
    
    // Setup event listeners
    this.setupEventListeners();
    
    // Start WebSocket
    this.connectWebSocket();
    
    // Auto-refresh
    this.startAutoRefresh();
    
    console.log('✅ AVP Studio ready');
  },

  // Navigation
  navigate(section) {
    // Update tabs
    document.querySelectorAll('.nav-tab').forEach(tab => {
      tab.classList.toggle('active', tab.dataset.section === section);
    });
    
    // Update sections
    document.querySelectorAll('.section').forEach(sec => {
      sec.classList.toggle('active', sec.id === `section-${section}`);
    });
    
    this.state.currentSection = section;
    
    // Load section data
    this.loadSection(section);
  },

  async loadSection(section) {
    switch(section) {
      case 'dashboard':
        await this.loadDashboard();
        break;
      case 'projects':
        await projects.load();
        break;
      case 'scenes':
        await scenes.load();
        break;
      case 'generate':
        await generation.refreshQueue();
        break;
    }
  },

  // Health Check
  async checkHealth() {
    try {
      const health = await AVPAPI.Health.check();
      this.state.healthStatus = health.status;
      
      const statusEl = document.getElementById('healthStatus');
      const dot = statusEl.querySelector('.status-dot');
      const text = statusEl.querySelector('.status-text');
      
      if (health.status === 'healthy') {
        dot.style.background = 'var(--success)';
        dot.style.boxShadow = '0 0 10px var(--success)';
        text.textContent = '系統正常';
      } else {
        dot.style.background = 'var(--warning)';
        dot.style.boxShadow = '0 0 10px var(--warning)';
        text.textContent = '部分服務異常';
      }
    } catch (error) {
      this.state.healthStatus = 'error';
      const statusEl = document.getElementById('healthStatus');
      statusEl.querySelector('.status-dot').style.background = 'var(--error)';
      statusEl.querySelector('.status-text').textContent = '連接失敗';
      this.toast('無法連接到服務器', 'error');
    }
  },

  // Load Dashboard Data
  async loadDashboard() {
    try {
      // Load projects count
      const projects = await AVPAPI.Project.list();
      this.state.projects = projects || [];
      document.getElementById('statProjects').textContent = this.state.projects.length;
      
      // Load scenes count
      const scenes = await AVPAPI.Scene.list('');
      this.state.scenes = scenes || [];
      document.getElementById('statScenes').textContent = this.state.scenes.length;
      
      // Load generation queue
      const queue = await AVPAPI.Generation.getQueueStatus();
      document.getElementById('statGenerating').textContent = queue.processing || 0;
      document.getElementById('statCompleted').textContent = queue.completed || 0;
      
      // Update recent projects
      this.updateRecentProjects();
      
      // Update queue
      this.updateQueueDisplay();
    } catch (error) {
      console.error('Failed to load dashboard:', error);
    }
  },

  updateRecentProjects() {
    const container = document.getElementById('recentProjects');
    const recent = this.state.projects.slice(0, 5);
    
    if (recent.length === 0) {
      container.innerHTML = '<div class="empty-state"><p>暫無項目</p></div>';
      return;
    }
    
    container.innerHTML = recent.map(project => `
      <div class="project-card" onclick="projects.open('${project.id}')">
        <div class="project-header">
          <div class="project-icon">📁</div>
        </div>
        <div class="project-title">${project.name || '未命名項目'}</div>
        <div class="project-description">${project.description || '無描述'}</div>
        <div class="project-meta">
          <span>📊 ${project.scenes || 0} 場景</span>
        </div>
      </div>
    `).join('');
  },

  updateQueueDisplay() {
    const container = document.getElementById('generationQueue');
    const tasks = this.state.generationTasks.slice(0, 5);
    
    if (tasks.length === 0) {
      container.innerHTML = '<div class="empty-state"><p>隊列為空</p></div>';
      return;
    }
    
    container.innerHTML = tasks.map(task => `
      <div class="scene-card">
        <div class="scene-icon">⚡</div>
        <div class="scene-info">
          <div class="scene-title">Task #${task.task_id?.slice(-6)}</div>
          <div class="scene-description">
            進度：${task.progress || 0}% | 
            狀態：<span class="status-badge ${task.status}">${task.status}</span>
          </div>
        </div>
      </div>
    `).join('');
  },

  // Event Listeners
  setupEventListeners() {
    // Navigation tabs
    document.querySelectorAll('.nav-tab').forEach(tab => {
      tab.addEventListener('click', () => {
        this.navigate(tab.dataset.section);
      });
    });
    
    // Project filter
    const projectFilter = document.getElementById('projectFilter');
    if (projectFilter) {
      projectFilter.addEventListener('change', (e) => {
        scenes.load(e.target.value);
      });
    }
    
    // Prompt optimization
    const promptInput = document.getElementById('promptInput');
    if (promptInput) {
      promptInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter' && e.ctrlKey) {
          prompts.optimize();
        }
      });
    }
  },

  // WebSocket Connection
  connectWebSocket() {
    try {
      const ws = new AVPAPI.WebSocketClient('/ws');
      
      ws.on('open', () => {
        console.log('✅ WebSocket connected');
        this.toast('實時連接已建立', 'success');
      });
      
      ws.on('message', (data) => {
        console.log('WebSocket message:', data);
        
        if (data.type === 'generation_progress') {
          this.updateGenerationTask(data.task_id, data);
        } else if (data.type === 'scene_updated') {
          this.refreshCurrentScene();
        }
      });
      
      ws.on('close', () => {
        console.log('WebSocket disconnected');
      });
      
      ws.on('error', (error) => {
        console.error('WebSocket error:', error);
      });
      
      ws.connect();
    } catch (error) {
      console.error('Failed to connect WebSocket:', error);
    }
  },

  // Auto Refresh
  startAutoRefresh() {
    // Refresh health every 30s
    setInterval(() => this.checkHealth(), 30000);
    
    // Refresh queue every 10s
    setInterval(() => {
      if (this.state.currentSection === 'dashboard' || this.state.currentSection === 'generate') {
        generation.refreshQueue();
      }
    }, 10000);
  },

  // Update Generation Task
  updateGenerationTask(taskId, data) {
    const taskIndex = this.state.generationTasks.findIndex(t => t.task_id === taskId);
    if (taskIndex >= 0) {
      this.state.generationTasks[taskIndex] = { ...this.state.generationTasks[taskIndex], ...data };
      generation.refreshQueue();
    }
  },

  refreshCurrentScene() {
    if (this.state.currentScene) {
      scenes.loadDetail(this.state.currentScene.id);
    }
  },

  // Toast Notifications
  toast(message, type = 'info') {
    const container = document.getElementById('toastContainer');
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    
    const icons = {
      success: '✅',
      error: '❌',
      warning: '⚠️',
      info: 'ℹ️',
    };
    
    toast.innerHTML = `
      <span class="toast-icon">${icons[type] || icons.info}</span>
      <span class="toast-message">${message}</span>
    `;
    
    container.appendChild(toast);
    
    // Auto remove after 4s
    setTimeout(() => {
      toast.style.animation = 'slideIn 0.3s ease reverse';
      setTimeout(() => toast.remove(), 300);
    }, 4000);
  },

  // Loading State
  showLoading(text = '加載中...') {
    document.getElementById('loadingText').textContent = text;
    document.getElementById('loadingOverlay').style.display = 'flex';
  },

  hideLoading() {
    document.getElementById('loadingOverlay').style.display = 'none';
  },
};

// ═══════════════════════════════════════════════════════════
// Projects Module
// ═══════════════════════════════════════════════════════════

const projects = {
  async load() {
    try {
      const projects = await AVPAPI.Project.list();
      app.state.projects = projects || [];
      
      const container = document.getElementById('projectsList');
      
      if (projects.length === 0) {
        container.innerHTML = `
          <div class="empty-state large">
            <div class="empty-icon">📁</div>
            <h3>暫無項目</h3>
            <p>點擊右上角創建第一個項目</p>
          </div>
        `;
        return;
      }
      
      container.innerHTML = projects.map(project => `
        <div class="project-card" onclick="projects.open('${project.id}')">
          <div class="project-header">
            <div class="project-icon">📁</div>
          </div>
          <div class="project-title">${project.name || '未命名項目'}</div>
          <div class="project-description">${project.description || '無描述'}</div>
          <div class="project-meta">
            <span>📊 ${project.scenes || 0} 場景</span>
            <span>🕐 ${new Date(project.created_at).toLocaleDateString()}</span>
          </div>
        </div>
      `).join('');
      
      // Update project filter
      this.updateProjectFilter();
    } catch (error) {
      app.toast('加載項目失敗', 'error');
      console.error(error);
    }
  },

  updateProjectFilter() {
    const filter = document.getElementById('projectFilter');
    if (!filter) return;
    
    const options = ['<option value="">所有項目</option>'];
    app.state.projects.forEach(project => {
      options.push(`<option value="${project.id}">${project.name}</option>`);
    });
    filter.innerHTML = options.join('');
  },

  showCreateModal() {
    document.getElementById('createProjectModal').classList.add('active');
    document.getElementById('projectName').value = '';
    document.getElementById('projectDescription').value = '';
    document.getElementById('projectName').focus();
  },

  closeCreateModal() {
    document.getElementById('createProjectModal').classList.remove('active');
  },

  async create() {
    const name = document.getElementById('projectName').value.trim();
    const description = document.getElementById('projectDescription').value.trim();
    
    if (!name) {
      app.toast('請輸入項目名稱', 'warning');
      return;
    }
    
    try {
      app.showLoading('創建項目中...');
      
      const project = await AVPAPI.Project.create({
        name: name,
        description: description,
      });
      
      app.state.projects.push(project);
      this.closeCreateModal();
      await this.load();
      app.navigate('projects');
      
      app.toast('項目創建成功', 'success');
    } catch (error) {
      app.toast('創建項目失敗', 'error');
      console.error(error);
    } finally {
      app.hideLoading();
    }
  },

  open(projectId) {
    app.state.currentProject = projectId;
    app.navigate('scenes');
    document.getElementById('projectFilter').value = projectId;
    scenes.load(projectId);
  },
};

// ═══════════════════════════════════════════════════════════
// Scenes Module
// ═══════════════════════════════════════════════════════════

const scenes = {
  async load(projectId = '') {
    try {
      const filter = projectId || document.getElementById('projectFilter')?.value || '';
      const scenes = await AVPAPI.Scene.list(filter);
      app.state.scenes = scenes || [];
      
      const container = document.getElementById('scenesList');
      
      if (scenes.length === 0) {
        container.innerHTML = `
          <div class="empty-state large">
            <div class="empty-icon">🎬</div>
            <h3>暫無場景</h3>
            <p>${filter ? '該項目下暫無場景' : '選擇項目後創建場景'}</p>
          </div>
        `;
        return;
      }
      
      container.innerHTML = scenes.map(scene => `
        <div class="scene-card" onclick="scenes.openDetail('${scene.id}')">
          <div class="scene-icon">🎬</div>
          <div class="scene-info">
            <div class="scene-title">${scene.title || '未命名場景'}</div>
            <div class="scene-description">${scene.description || '無描述'}</div>
          </div>
          <div class="scene-actions">
            <span class="status-badge ${scene.status}">${scene.status}</span>
          </div>
        </div>
      `).join('');
    } catch (error) {
      app.toast('加載場景失敗', 'error');
      console.error(error);
    }
  },

  showCreateModal() {
    if (!app.state.currentProject) {
      app.toast('請先選擇項目', 'warning');
      return;
    }
    
    document.getElementById('createSceneModal').classList.add('active');
    document.getElementById('sceneTitle').value = '';
    document.getElementById('sceneDescription').value = '';
    document.getElementById('sceneNarrative').value = '';
    document.getElementById('scenePositivePrompt').value = '';
    document.getElementById('sceneNegativePrompt').value = '';
    document.getElementById('sceneTitle').focus();
  },

  closeCreateModal() {
    document.getElementById('createSceneModal').classList.remove('active');
  },

  async create() {
    const title = document.getElementById('sceneTitle').value.trim();
    const description = document.getElementById('sceneDescription').value.trim();
    const narrative = document.getElementById('sceneNarrative').value.trim();
    const positivePrompt = document.getElementById('scenePositivePrompt').value.trim();
    const negativePrompt = document.getElementById('sceneNegativePrompt').value.trim();
    
    if (!title) {
      app.toast('請輸入場景標題', 'warning');
      return;
    }
    
    if (!positivePrompt) {
      app.toast('請輸入正向提示詞', 'warning');
      return;
    }
    
    try {
      app.showLoading('創建場景中...');
      
      const scene = await AVPAPI.Scene.create({
        project_id: app.state.currentProject,
        title: title,
        description: description,
        narrative_text: narrative,
        positive_prompt: positivePrompt,
        negative_prompt: negativePrompt,
        duration: 5.0,
        resolution: '1920x1080',
        fps: 24,
      });
      
      app.state.scenes.push(scene);
      this.closeCreateModal();
      await this.load();
      
      app.toast('場景創建成功', 'success');
    } catch (error) {
      app.toast('創建場景失敗', 'error');
      console.error(error);
    } finally {
      app.hideLoading();
    }
  },

  openDetail(sceneId) {
    app.state.currentScene = { id: sceneId };
    this.loadDetail(sceneId);
  },

  async loadDetail(sceneId) {
    try {
      const scene = await AVPAPI.Scene.get(sceneId);
      
      document.getElementById('sceneDetailTitle').textContent = scene.title;
      document.getElementById('sceneDetailStatus').textContent = scene.status;
      document.getElementById('sceneDetailStatus').className = `status-badge ${scene.status}`;
      document.getElementById('sceneDetailVersion').textContent = scene.version || '1.0.0';
      document.getElementById('sceneDetailDuration').textContent = `${scene.duration || 5.0}s`;
      document.getElementById('sceneDetailResolution').textContent = scene.resolution || '1920x1080';
      document.getElementById('sceneDetailDescription').textContent = scene.description || '無描述';
      document.getElementById('sceneDetailNarrative').textContent = scene.narrative_text || '無';
      
      document.getElementById('sceneDetailModal').classList.add('active');
    } catch (error) {
      app.toast('加載場景詳情失敗', 'error');
      console.error(error);
    }
  },

  closeDetailModal() {
    document.getElementById('sceneDetailModal').classList.remove('active');
  },

  async transitionToReview() {
    if (!app.state.currentScene) return;
    
    try {
      app.showLoading('提交審核中...');
      
      await AVPAPI.Scene.transition(
        app.state.currentScene.id,
        'review',
        '用戶提交審核'
      );
      
      this.closeDetailModal();
      await this.load();
      
      app.toast('場景已提交審核', 'success');
    } catch (error) {
      app.toast('提交審核失敗', 'error');
      console.error(error);
    } finally {
      app.hideLoading();
    }
  },

  async submitGeneration() {
    if (!app.state.currentScene) return;
    
    try {
      app.showLoading('提交生成任務中...');
      
      const result = await AVPAPI.Generation.submit(app.state.currentScene.id);
      
      this.closeDetailModal();
      app.navigate('generate');
      
      app.toast(`生成任務已提交：${result.task_id?.slice(-6)}`, 'success');
    } catch (error) {
      app.toast('提交生成任務失敗', 'error');
      console.error(error);
    } finally {
      app.hideLoading();
    }
  },
};

// ═══════════════════════════════════════════════════════════
// Prompts Module
// ═══════════════════════════════════════════════════════════

const prompts = {
  async optimize() {
    const prompt = document.getElementById('promptInput').value.trim();
    const style = document.getElementById('promptStyle').value;
    
    if (!prompt) {
      app.toast('請輸入提示詞', 'warning');
      return;
    }
    
    try {
      app.showLoading('優化提示詞中...');
      
      const result = await AVPAPI.Prompt.optimize(prompt, {}, style);
      
      document.getElementById('optimizedPrompt').value = result.optimized_prompt;
      document.getElementById('negativePrompt').value = result.negative_prompt;
      document.getElementById('qualityScore').textContent = `質量：${(result.quality_score * 100).toFixed(0)}%`;
      document.getElementById('promptResult').style.display = 'block';
      
      app.toast('提示詞優化完成', 'success');
    } catch (error) {
      app.toast('優化提示詞失敗', 'error');
      console.error(error);
    } finally {
      app.hideLoading();
    }
  },
};

// ═══════════════════════════════════════════════════════════
// Generation Module
// ═══════════════════════════════════════════════════════════

const generation = {
  async refreshQueue() {
    try {
      const queue = await AVPAPI.Generation.getQueueStatus();
      app.state.generationQueue = queue;
      
      // Update dashboard stats
      document.getElementById('statGenerating').textContent = queue.processing || 0;
      
      // Load tasks
      const container = document.getElementById('generateTasks');
      
      // For now, show queue status
      container.innerHTML = `
        <div class="result-box">
          <div class="result-header">
            <h4>隊列狀態</h4>
          </div>
          <div class="result-content">
            <div class="detail-row">
              <span class="detail-label">排隊中:</span>
              <span>${queue.queued || 0}</span>
            </div>
            <div class="detail-row">
              <span class="detail-label">生成中:</span>
              <span>${queue.processing || 0}</span>
            </div>
            <div class="detail-row">
              <span class="detail-label">可用 GPU:</span>
              <span>${queue.available_gpus || 4}</span>
            </div>
          </div>
        </div>
      `;
    } catch (error) {
      console.error('Failed to refresh queue:', error);
    }
  },
};

// ═══════════════════════════════════════════════════════════
// Initialize App
// ═══════════════════════════════════════════════════════════

document.addEventListener('DOMContentLoaded', () => {
  app.init();
});

// Export for global access
window.app = app;
window.projects = projects;
window.scenes = scenes;
window.prompts = prompts;
window.generation = generation;
