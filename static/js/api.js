/**
 * AVP Platform - API Client
 * 封裝所有後端 API 調用
 */

const API_BASE = '/api/v1';

// ============================================================================
// HTTP 工具函數
// ============================================================================

async function apiRequest(endpoint, options = {}) {
    const url = `${API_BASE}${endpoint}`;
    const config = {
        headers: {
            'Content-Type': 'application/json',
            ...options.headers,
        },
        ...options,
    };

    try {
        const response = await fetch(url, config);
        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.message || `HTTP ${response.status}`);
        }

        return data;
    } catch (error) {
        console.error(`API Error [${endpoint}]:`, error);
        throw error;
    }
}

async function apiGet(endpoint) {
    return apiRequest(endpoint, { method: 'GET' });
}

async function apiPost(endpoint, data) {
    return apiRequest(endpoint, {
        method: 'POST',
        body: JSON.stringify(data),
    });
}

async function apiPut(endpoint, data) {
    return apiRequest(endpoint, {
        method: 'PUT',
        body: JSON.stringify(data),
    });
}

async function apiDelete(endpoint) {
    return apiRequest(endpoint, { method: 'DELETE' });
}

// ============================================================================
// 場景管理 API
// ============================================================================

const SceneAPI = {
    /**
     * 創建場景
     */
    async create(sceneData) {
        return apiPost('/scenes/', sceneData);
    },

    /**
     * 獲取場景詳情
     */
    async get(sceneId) {
        return apiGet(`/scenes/${sceneId}`);
    },

    /**
     * 列出場景
     */
    async list(projectId, filters = {}) {
        const params = new URLSearchParams({ project_id: projectId, ...filters });
        return apiGet(`/scenes/?${params}`);
    },

    /**
     * 更新場景
     */
    async update(sceneId, updates) {
        return apiPut(`/scenes/${sceneId}`, updates);
    },

    /**
     * 刪除場景
     */
    async delete(sceneId) {
        return apiDelete(`/scenes/${sceneId}`);
    },

    /**
     * 狀態轉換
     */
    async transition(sceneId, targetStatus, reason = '') {
        return apiPost(`/scenes/${sceneId}/transition`, {
            target_status: targetStatus,
            reason,
        });
    },

    /**
     * 鎖定場景
     */
    async lock(sceneId) {
        return apiPost(`/scenes/${sceneId}/lock`);
    },

    /**
     * 解鎖場景
     */
    async unlock(sceneId) {
        return apiPost(`/scenes/${sceneId}/unlock`);
    },

    /**
     * 獲取版本歷史
     */
    async getVersions(sceneId) {
        return apiGet(`/scenes/${sceneId}/versions`);
    },

    /**
     * 影響分析
     */
    async analyzeImpact(sceneId) {
        return apiGet(`/scenes/${sceneId}/impact-analysis`);
    },

    /**
     * 連貫性檢查
     */
    async checkContinuity(sceneId) {
        return apiGet(`/scenes/${sceneId}/continuity-check`);
    },
};

// ============================================================================
// 提示詞優化 API
// ============================================================================

const PromptAPI = {
    /**
     * 優化提示詞
     */
    async optimize(prompt, context = {}, style = 'cinematic') {
        return apiPost('/prompts/optimize', {
            prompt,
            context,
            style,
        });
    },

    /**
     * 批量優化
     */
    async batchOptimize(prompts, context = {}) {
        return apiPost('/prompts/batch-optimize', {
            prompts,
            context,
        });
    },

    /**
     * 評估質量
     */
    async evaluateQuality(prompt) {
        return apiPost('/prompts/evaluate', { prompt });
    },

    /**
     * 搜索相似提示詞
     */
    async search(query, filters = {}, limit = 10) {
        const params = new URLSearchParams({ query, limit, ...filters });
        return apiGet(`/prompts/search?${params}`);
    },

    /**
     * 推薦提示詞
     */
    async recommend(sceneContext, limit = 5) {
        return apiPost('/prompts/recommend', {
            scene_context: sceneContext,
            limit,
        });
    },

    /**
     * 獲取提示詞詳情
     */
    async get(promptId) {
        return apiGet(`/prompts/${promptId}`);
    },

    /**
     * 列出提示詞
     */
    async list(projectId, filters = {}) {
        const params = new URLSearchParams({ project_id: projectId, ...filters });
        return apiGet(`/prompts/?${params}`);
    },
};

// ============================================================================
// 項目管理 API
// ============================================================================

const ProjectAPI = {
    /**
     * 創建項目
     */
    async create(projectData) {
        return apiPost('/projects/', projectData);
    },

    /**
     * 獲取項目詳情
     */
    async get(projectId) {
        return apiGet(`/projects/${projectId}`);
    },

    /**
     * 列出項目
     */
    async list() {
        return apiGet('/projects/');
    },

    /**
     * 更新項目
     */
    async update(projectId, updates) {
        return apiPut(`/projects/${projectId}`, updates);
    },

    /**
     * 刪除項目
     */
    async delete(projectId) {
        return apiDelete(`/projects/${projectId}`);
    },

    /**
     * 獲取項目統計
     */
    async getStatistics(projectId) {
        return apiGet(`/projects/${project_id}/statistics`);
    },
};

// ============================================================================
// 角色管理 API
// ============================================================================

const CharacterAPI = {
    /**
     * 創建角色
     */
    async create(characterData) {
        return apiPost('/characters/', characterData);
    },

    /**
     * 獲取角色詳情
     */
    async get(characterId) {
        return apiGet(`/characters/${characterId}`);
    },

    /**
     * 列出角色
     */
    async list(projectId) {
        return apiGet(`/characters/?project_id=${projectId}`);
    },

    /**
     * 更新角色
     */
    async update(characterId, updates) {
        return apiPut(`/characters/${characterId}`, updates);
    },

    /**
     * 刪除角色
     */
    async delete(characterId) {
        return apiDelete(`/characters/${characterId}`);
    },

    /**
     * 獲取角色關係網絡
     */
    async getNetwork(projectId) {
        return apiGet(`/characters/network?project_id=${projectId}`);
    },
};

// ============================================================================
// 視頻生成 API
// ============================================================================

const GenerationAPI = {
    /**
     * 提交生成任務
     */
    async submit(sceneId) {
        return apiPost('/generation/submit', { scene_id: sceneId });
    },

    /**
     * 查詢任務狀態
     */
    async getTaskStatus(taskId) {
        return apiGet(`/generation/tasks/${taskId}`);
    },

    /**
     * 取消任務
     */
    async cancelTask(taskId) {
        return apiPost(`/generation/tasks/${taskId}/cancel`);
    },

    /**
     * 查看隊列狀態
     */
    async getQueueStatus() {
        return apiGet('/generation/queue');
    },

    /**
     * 下載生成結果
     */
    async download(taskId) {
        window.open(`/api/v1/generation/download/${taskId}`, '_blank');
    },
};

// ============================================================================
// 健康檢查 API
// ============================================================================

const HealthAPI = {
    /**
     * 健康檢查
     */
    async check() {
        return apiGet('/health');
    },

    /**
     * 詳細健康檢查
     */
    async detailed() {
        return apiGet('/health/detailed');
    },
};

// ============================================================================
// WebSocket 連接
// ============================================================================

class WebSocketClient {
    constructor(endpoint) {
        this.endpoint = endpoint;
        this.ws = null;
        this.reconnectInterval = 3000;
        this.reconnectTimer = null;
        this.callbacks = {
            open: [],
            message: [],
            close: [],
            error: [],
        };
    }

    connect() {
        const wsUrl = `ws://${window.location.host}${this.endpoint}`;
        this.ws = new WebSocket(wsUrl);

        this.ws.onopen = () => {
            console.log('WebSocket connected');
            this.callbacks.open.forEach(cb => cb());
            clearTimeout(this.reconnectTimer);
        };

        this.ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            this.callbacks.message.forEach(cb => cb(data));
        };

        this.ws.onclose = () => {
            console.log('WebSocket closed, reconnecting...');
            this.callbacks.close.forEach(cb => cb());
            this.reconnectTimer = setTimeout(() => this.connect(), this.reconnectInterval);
        };

        this.ws.onerror = (error) => {
            console.error('WebSocket error:', error);
            this.callbacks.error.forEach(cb => cb(error));
        };
    }

    disconnect() {
        if (this.ws) {
            this.ws.close();
            this.ws = null;
        }
        clearTimeout(this.reconnectTimer);
    }

    send(data) {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify(data));
        } else {
            console.warn('WebSocket not connected');
        }
    }

    on(event, callback) {
        if (this.callbacks[event]) {
            this.callbacks[event].push(callback);
        }
    }

    off(event, callback) {
        if (this.callbacks[event]) {
            this.callbacks[event] = this.callbacks[event].filter(cb => cb !== callback);
        }
    }
}

// ============================================================================
// 導出
// ============================================================================

window.AVPAPI = {
    // API 模塊
    Scene: SceneAPI,
    Prompt: PromptAPI,
    Project: ProjectAPI,
    Character: CharacterAPI,
    Generation: GenerationAPI,
    Health: HealthAPI,

    // WebSocket
    WebSocketClient,

    // 工具函數
    request: apiRequest,
    get: apiGet,
    post: apiPost,
    put: apiPut,
    delete: apiDelete,
};

console.log('✅ AVP API Client loaded');
