/**
 * Dashboard 數據可視化模塊
 * 實時統計、圖表展示、數據整理
 */

const Dashboard = {
  // 儀表板數據
  data: {
    projects: {
      total: 0,
      active: 0,
      completed: 0,
      trend: 0,
    },
    scenes: {
      total: 0,
      byStatus: {},
      trend: 0,
    },
    generations: {
      total: 0,
      queued: 0,
      processing: 0,
      completed: 0,
      failed: 0,
      successRate: 0,
    },
    assets: {
      total: 0,
      byType: {},
      storageUsed: 0,
    },
    tasks: {
      scheduled: 0,
      running: 0,
      completed: 0,
      failed: 0,
    },
    performance: {
      avgRenderTime: 0,
      cacheHitRate: 0,
      apiResponseTime: 0,
    },
  },

  // 圖表實例
  charts: {},

  // 初始化儀表板
  async init() {
    console.log('📊 Dashboard initializing...');
    
    // 加載初始數據
    await this.loadData();
    
    // 創建圖表
    this.createCharts();
    
    // 啟動實時更新
    this.startRealTimeUpdates();
    
    // 綁定事件
    this.bindEvents();
    
    console.log('✅ Dashboard ready');
  },

  // 加載數據
  async loadData() {
    try {
      // 並行加載所有數據
      const [
        projectsData,
        scenesData,
        generationsData,
        assetsData,
        tasksData,
        performanceData,
      ] = await Promise.all([
        this.loadProjectsData(),
        this.loadScenesData(),
        this.loadGenerationsData(),
        this.loadAssetsData(),
        this.loadTasksData(),
        this.loadPerformanceData(),
      ]);

      // 更新數據
      this.data.projects = projectsData;
      this.data.scenes = scenesData;
      this.data.generations = generationsData;
      this.data.assets = assetsData;
      this.data.tasks = tasksData;
      this.data.performance = performanceData;

      // 更新 UI
      this.updateUI();
    } catch (error) {
      console.error('Failed to load dashboard data:', error);
      app.toast('加載儀表板數據失敗', 'error');
    }
  },

  // 加載項目數據
  async loadProjectsData() {
    try {
      const projects = await AVPAPI.Project.list();
      const total = projects.length;
      const active = projects.filter(p => p.status === 'active').length;
      const completed = projects.filter(p => p.status === 'completed').length;
      
      // 計算趨勢 (與上週比較)
      const trend = this.calculateTrend(projects, 'created_at', 7);

      return {
        total,
        active,
        completed,
        trend,
      };
    } catch (error) {
      console.error('Failed to load projects:', error);
      return { total: 0, active: 0, completed: 0, trend: 0 };
    }
  },

  // 加載場景數據
  async loadScenesData() {
    try {
      const scenes = await AVPAPI.Scene.list('');
      const total = scenes.length;
      
      // 按狀態分組
      const byStatus = scenes.reduce((acc, scene) => {
        const status = scene.status || 'draft';
        acc[status] = (acc[status] || 0) + 1;
        return acc;
      }, {});

      const trend = this.calculateTrend(scenes, 'created_at', 7);

      return {
        total,
        byStatus,
        trend,
      };
    } catch (error) {
      console.error('Failed to load scenes:', error);
      return { total: 0, byStatus: {}, trend: 0 };
    }
  },

  // 加載生成數據
  async loadGenerationsData() {
    try {
      const queue = await AVPAPI.Generation.getQueueStatus();
      
      const total = (queue.queued || 0) + 
                   (queue.processing || 0) + 
                   (queue.completed || 0) + 
                   (queue.failed || 0);
      
      const completed = queue.completed || 0;
      const failed = queue.failed || 0;
      const successRate = total > 0 ? (completed / total * 100) : 0;

      return {
        total,
        queued: queue.queued || 0,
        processing: queue.processing || 0,
        completed,
        failed,
        successRate: Math.round(successRate * 100) / 100,
      };
    } catch (error) {
      console.error('Failed to load generations:', error);
      return {
        total: 0,
        queued: 0,
        processing: 0,
        completed: 0,
        failed: 0,
        successRate: 0,
      };
    }
  },

  // 加載資產數據
  async loadAssetsData() {
    try {
      // TODO: 實現資產 API
      return {
        total: 0,
        byType: {},
        storageUsed: 0,
      };
    } catch (error) {
      console.error('Failed to load assets:', error);
      return { total: 0, byType: {}, storageUsed: 0 };
    }
  },

  // 加載任務數據
  async loadTasksData() {
    try {
      // TODO: 實現排程任務 API
      return {
        scheduled: 0,
        running: 0,
        completed: 0,
        failed: 0,
      };
    } catch (error) {
      console.error('Failed to load tasks:', error);
      return { scheduled: 0, running: 0, completed: 0, failed: 0 };
    }
  },

  // 加載性能數據
  async loadPerformanceData() {
    try {
      // TODO: 實現性能 API
      return {
        avgRenderTime: 0,
        cacheHitRate: 0,
        apiResponseTime: 0,
      };
    } catch (error) {
      console.error('Failed to load performance:', error);
      return { avgRenderTime: 0, cacheHitRate: 0, apiResponseTime: 0 };
    }
  },

  // 計算趨勢
  calculateTrend(items, dateField, days) {
    const now = new Date();
    const pastDate = new Date(now.getTime() - days * 24 * 60 * 60 * 1000);
    
    const recent = items.filter(item => {
      const date = new Date(item[dateField]);
      return date >= pastDate;
    });

    const previous = items.filter(item => {
      const date = new Date(item[dateField]);
      return date < pastDate && date >= new Date(pastDate.getTime() - days * 24 * 60 * 60 * 1000);
    });

    if (previous.length === 0) return recent.length > 0 ? 100 : 0;
    
    const growth = ((recent.length - previous.length) / previous.length) * 100;
    return Math.round(growth * 100) / 100;
  },

  // 更新 UI
  updateUI() {
    // 更新統計卡片
    this.updateStatCards();
    
    // 更新圖表
    this.updateCharts();
    
    // 更新列表
    this.updateLists();
  },

  // 更新統計卡片
  updateStatCards() {
    // 項目統計
    this.setTextWithTrend('statProjects', this.data.projects.total, this.data.projects.trend);
    this.setTextWithTrend('statActiveProjects', this.data.projects.active, 0);
    this.setTextWithTrend('statCompletedProjects', this.data.projects.completed, 0);
    
    // 場景統計
    this.setTextWithTrend('statScenes', this.data.scenes.total, this.data.scenes.trend);
    
    // 生成統計
    this.setTextWithTrend('statGenerations', this.data.generations.total, 0);
    this.setText('statSuccessRate', `${this.data.generations.successRate}%`);
    
    // 任務統計
    this.setText('statScheduledTasks', this.data.tasks.scheduled);
    this.setText('statRunningTasks', this.data.tasks.running);
  },

  // 設置文本 (帶趨勢)
  setTextWithTrend(elementId, value, trend) {
    const element = document.getElementById(elementId);
    if (!element) return;
    
    element.innerHTML = `
      <span class="stat-value">${this.formatNumber(value)}</span>
      ${trend !== 0 ? `
        <span class="stat-trend ${trend > 0 ? 'up' : 'down'}">
          ${trend > 0 ? '📈' : '📉'} ${Math.abs(trend)}%
        </span>
      ` : ''}
    `;
  },

  // 設置文本
  setText(elementId, value) {
    const element = document.getElementById(elementId);
    if (element) {
      element.textContent = value;
    }
  },

  // 格式化數字
  formatNumber(num) {
    if (num >= 1000000) {
      return (num / 1000000).toFixed(1) + 'M';
    } else if (num >= 1000) {
      return (num / 1000).toFixed(1) + 'K';
    }
    return num.toString();
  },

  // 創建圖表
  createCharts() {
    // 場景狀態分佈圖
    this.createStatusChart();
    
    // 生成趨勢圖
    this.createGenerationTrendChart();
    
    // 資產類型分佈圖
    this.createAssetTypeChart();
    
    // 性能指標圖
    this.createPerformanceChart();
  },

  // 創建場景狀態圖
  createStatusChart() {
    const ctx = document.getElementById('statusChart');
    if (!ctx) return;

    const data = this.data.scenes.byStatus;
    
    this.charts.status = new Chart(ctx, {
      type: 'doughnut',
      data: {
        labels: Object.keys(data),
        datasets: [{
          data: Object.values(data),
          backgroundColor: [
            'rgba(99, 102, 241, 0.8)',   // draft
            'rgba(245, 158, 11, 0.8)',   // review
            'rgba(59, 130, 246, 0.8)',   // locked
            'rgba(16, 185, 129, 0.8)',   // completed
            'rgba(239, 68, 68, 0.8)',    // failed
          ],
          borderWidth: 0,
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            position: 'bottom',
            labels: {
              color: '#a0a0b0',
              padding: 15,
            },
          },
        },
      },
    });
  },

  // 創建生成趨勢圖
  createGenerationTrendChart() {
    const ctx = document.getElementById('generationTrendChart');
    if (!ctx) return;

    // 模擬 7 天數據
    const labels = [];
    const data = [];
    for (let i = 6; i >= 0; i--) {
      const date = new Date();
      date.setDate(date.getDate() - i);
      labels.push(date.toLocaleDateString('zh-TW', { month: 'short', day: 'numeric' }));
      data.push(Math.floor(Math.random() * 20) + 5);
    }

    this.charts.generationTrend = new Chart(ctx, {
      type: 'line',
      data: {
        labels,
        datasets: [{
          label: '生成數量',
          data,
          borderColor: 'rgb(99, 102, 241)',
          backgroundColor: 'rgba(99, 102, 241, 0.1)',
          tension: 0.4,
          fill: true,
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            display: false,
          },
        },
        scales: {
          y: {
            beginAtZero: true,
            grid: {
              color: 'rgba(255, 255, 255, 0.05)',
            },
            ticks: {
              color: '#a0a0b0',
            },
          },
          x: {
            grid: {
              display: false,
            },
            ticks: {
              color: '#a0a0b0',
            },
          },
        },
      },
    });
  },

  // 創建資產類型圖
  createAssetTypeChart() {
    const ctx = document.getElementById('assetTypeChart');
    if (!ctx) return;

    this.charts.assetType = new Chart(ctx, {
      type: 'bar',
      data: {
        labels: ['視頻', '圖片', '音樂', '音效', '3D 模型'],
        datasets: [{
          label: '數量',
          data: [0, 0, 0, 0, 0],
          backgroundColor: 'rgba(99, 102, 241, 0.8)',
          borderRadius: 5,
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            display: false,
          },
        },
        scales: {
          y: {
            beginAtZero: true,
            grid: {
              color: 'rgba(255, 255, 255, 0.05)',
            },
            ticks: {
              color: '#a0a0b0',
            },
          },
          x: {
            grid: {
              display: false,
            },
            ticks: {
              color: '#a0a0b0',
            },
          },
        },
      },
    });
  },

  // 創建性能指標圖
  createPerformanceChart() {
    const ctx = document.getElementById('performanceChart');
    if (!ctx) return;

    this.charts.performance = new Chart(ctx, {
      type: 'radar',
      data: {
        labels: ['渲染速度', '緩存命中', 'API 響應', '生成質量', '系統穩定'],
        datasets: [{
          label: '性能指標',
          data: [0, 0, 0, 0, 0],
          backgroundColor: 'rgba(99, 102, 241, 0.2)',
          borderColor: 'rgb(99, 102, 241)',
          pointBackgroundColor: 'rgb(99, 102, 241)',
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
          r: {
            angleLines: {
              color: 'rgba(255, 255, 255, 0.1)',
            },
            grid: {
              color: 'rgba(255, 255, 255, 0.1)',
            },
            pointLabels: {
              color: '#a0a0b0',
            },
            ticks: {
              display: false,
            },
          },
        },
        plugins: {
          legend: {
            display: false,
          },
        },
      },
    });
  },

  // 更新圖表
  updateCharts() {
    // 更新場景狀態圖
    if (this.charts.status) {
      this.charts.status.data.datasets[0].data = Object.values(this.data.scenes.byStatus);
      this.charts.status.update();
    }
  },

  // 更新列表
  updateLists() {
    // 更新最近項目
    this.updateRecentProjects();
    
    // 更新生成隊列
    this.updateGenerationQueue();
    
    // 更新排程任務
    this.updateScheduledTasks();
  },

  // 更新最近項目
  async updateRecentProjects() {
    const container = document.getElementById('recentProjectsList');
    if (!container) return;

    try {
      const projects = await AVPAPI.Project.list();
      const recent = projects.slice(0, 5);

      if (recent.length === 0) {
        container.innerHTML = `
          <div class="empty-state">
            <div class="empty-icon">📁</div>
            <p>暫無項目</p>
          </div>
        `;
        return;
      }

      container.innerHTML = recent.map(project => `
        <div class="recent-item" onclick="projects.open('${project.id}')">
          <div class="recent-icon">📁</div>
          <div class="recent-info">
            <div class="recent-name">${project.name || '未命名項目'}</div>
            <div class="recent-meta">
              <span>${project.scenes || 0} 場景</span>
              <span>·</span>
              <span>${new Date(project.created_at).toLocaleDateString()}</span>
            </div>
          </div>
          <div class="recent-status status-badge ${project.status || 'active'}">
            ${project.status || 'active'}
          </div>
        </div>
      `).join('');
    } catch (error) {
      console.error('Failed to load recent projects:', error);
    }
  },

  // 更新生成隊列
  async updateGenerationQueue() {
    const container = document.getElementById('generationQueueList');
    if (!container) return;

    try {
      const queue = await AVPAPI.Generation.getQueueStatus();
      
      container.innerHTML = `
        <div class="queue-stats">
          <div class="queue-stat">
            <div class="queue-stat-value">${queue.queued || 0}</div>
            <div class="queue-stat-label">排隊中</div>
          </div>
          <div class="queue-stat">
            <div class="queue-stat-value">${queue.processing || 0}</div>
            <div class="queue-stat-label">生成中</div>
          </div>
          <div class="queue-stat">
            <div class="queue-stat-value">${queue.completed || 0}</div>
            <div class="queue-stat-label">已完成</div>
          </div>
        </div>
      `;
    } catch (error) {
      console.error('Failed to load generation queue:', error);
    }
  },

  // 更新排程任務
  updateScheduledTasks() {
    const container = document.getElementById('scheduledTasksList');
    if (!container) return;

    // TODO: 從排程服務獲取數據
    container.innerHTML = `
      <div class="empty-state">
        <p>暫無排程任務</p>
      </div>
    `;
  },

  // 啟動實時更新
  startRealTimeUpdates() {
    // 每 30 秒更新一次數據
    setInterval(() => {
      this.loadData();
    }, 30000);

    // 每 5 秒更新一次隊列狀態
    setInterval(() => {
      this.updateGenerationQueue();
    }, 5000);
  },

  // 綁定事件
  bindEvents() {
    // 刷新按鈕
    const refreshBtn = document.getElementById('refreshDashboard');
    if (refreshBtn) {
      refreshBtn.addEventListener('click', () => {
        this.loadData();
        app.toast('儀表板已刷新', 'success');
      });
    }

    // 時間範圍選擇
    const timeRangeSelect = document.getElementById('dashboardTimeRange');
    if (timeRangeSelect) {
      timeRangeSelect.addEventListener('change', (e) => {
        this.loadData();
      });
    }
  },

  // 導出數據
  exportData(format = 'json') {
    const data = this.data;
    let content, filename, mimeType;

    if (format === 'json') {
      content = JSON.stringify(data, null, 2);
      filename = `dashboard_${new Date().toISOString().split('T')[0]}.json`;
      mimeType = 'application/json';
    } else if (format === 'csv') {
      // TODO: 轉換為 CSV
      content = '';
      filename = `dashboard_${new Date().toISOString().split('T')[0]}.csv`;
      mimeType = 'text/csv';
    }

    // 下載文件
    const blob = new Blob([content], { type: mimeType });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);

    app.toast(`已導出${format.toUpperCase()}數據`, 'success');
  },
};

// 導出為全局對象
window.Dashboard = Dashboard;

// 頁面加載完成後初始化
document.addEventListener('DOMContentLoaded', () => {
  // 等待 Chart.js 加載
  if (typeof Chart !== 'undefined') {
    Dashboard.init();
  } else {
    console.warn('Chart.js not loaded, dashboard charts disabled');
  }
});
