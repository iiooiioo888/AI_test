# AVP Platform - 快速開始指南

## 🚀 5 分鐘快速啟動

### 方法 1: Docker Compose (推薦)

```bash
# 克隆代碼庫
git clone https://github.com/iiooiioo888/AI_test.git
cd AI_test

# 啟動所有服務
docker-compose up -d

# 查看日誌
docker-compose logs -f api

# 訪問應用
# Web UI: http://localhost:8888
# API Docs: http://localhost:8888/docs
```

### 方法 2: 本地啟動

```bash
# 1. 安裝依賴
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# 2. 配置環境
cp .env.example .env
# 編輯 .env 文件

# 3. 啟動應用
python -m app.main

# 或使用啟動腳本
./scripts/start.sh --dev
```

---

## 📋 系統要求

### 最低要求
- Python 3.10+
- 2GB RAM
- 10GB 磁碟空間

### 推薦配置
- Python 3.10+
- 8GB RAM
- 50GB 磁碟空間
- NVIDIA GPU (用於視頻生成)

### 依賴服務 (Docker 會自動啟動)
- PostgreSQL 16
- Neo4j 5
- Milvus 2.5
- Redis 7

---

## 🧪 測試

### 運行單元測試

```bash
# 使用測試腳本
./scripts/test.sh

# 或直接運行 pytest
python -m pytest tests/unit/ -v

# 帶覆蓋率報告
python -m pytest tests/unit/ --cov=app --cov-report=html
```

### API 測試

```bash
# 健康檢查
curl http://localhost:8888/health

# 獲取文檔
curl http://localhost:8888/docs
```

---

## 🎯 基本使用

### 1. 創建項目

```python
from AVPAPI import Project

project = await ProjectAPI.create({
    "name": "我的第一個項目",
    "description": "測試項目",
})
print(f"項目 ID: {project.id}")
```

### 2. 創建場景

```python
from AVPAPI import Scene

scene = await SceneAPI.create({
    "project_id": project.id,
    "title": "開場場景",
    "description": "主角登場",
    "narrative_text": "晨光中，主角緩緩走上舞台...",
    "positive_prompt": "cinematic shot, heroic figure, dramatic lighting",
    "negative_prompt": "ugly, deformed, low quality",
})
```

### 3. 優化提示詞

```python
from AVPAPI import Prompt

result = await PromptAPI.optimize(
    prompt="一個人在走路",
    context={"scene": "city street", "time": "night"},
    style="cinematic",
)

print(f"優化後：{result.optimized_prompt}")
print(f"負向提示詞：{result.negative_prompt}")
print(f"質量評分：{result.quality_score}")
```

### 4. 狀態轉換

```python
# 提交審核
await SceneAPI.transition(scene.id, "review", "完成編輯")

# 審核通過 (需要 Director 權限)
await SceneAPI.transition(scene.id, "locked", "審核通過")

# 加入生成隊列
await SceneAPI.transition(scene.id, "queued", "準備生成")
```

### 5. 視頻生成

```python
from AVPAPI import Generation

# 提交生成任務
task = await GenerationAPI.submit(scene.id)
print(f"任務 ID: {task.task_id}")

# 輪詢狀態
while True:
    status = await GenerationAPI.getTaskStatus(task.task_id)
    print(f"進度：{status.progress}%")
    
    if status.status in ["completed", "failed"]:
        break
    
    await asyncio.sleep(5)

# 下載結果
if status.status == "completed":
    await GenerationAPI.download(task.task_id)
```

---

## 🔧 配置說明

### 關鍵環境變數

```bash
# 數據庫
DATABASE_URL=postgresql://avp:password@localhost:5432/avp_platform
NEO4J_URI=bolt://neo4j:password@localhost:7687
MILVUS_HOST=localhost

# 安全
SECRET_KEY=your_secret_key
JWT_SECRET_KEY=your_jwt_secret

# 存儲
STORAGE_BACKEND=local  # 或 s3, gcs, azure
STORAGE_PATH=./storage

# 視頻生成
GPU_POOL_SIZE=4
MAX_CONCURRENT_GENERATIONS=10
```

---

## 📊 監控

### Prometheus 指標

訪問 http://localhost:9090

關鍵指標：
- `avp_http_requests_total` - HTTP 請求總數
- `avp_generation_tasks_total` - 生成任務總數
- `avp_gpu_utilization_percent` - GPU 使用率

### Grafana 儀表板

訪問 http://localhost:3000
- 用戶名：admin
- 密碼：admin_password

預設儀表板：
- 系統健康
- 生成任務監控
- API 性能

---

## 🐛 故障排除

### 常見問題

**1. 端口被佔用**
```bash
# 檢查端口
lsof -i :8888

# 殺死進程
kill -9 <PID>
```

**2. 數據庫連接失敗**
```bash
# 檢查 PostgreSQL
docker-compose ps postgres

# 查看日誌
docker-compose logs postgres
```

**3. 依賴安裝失敗**
```bash
# 清理並重新安裝
rm -rf venv
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

**4. GPU 不可用**
```bash
# 檢查 NVIDIA 驅動
nvidia-smi

# 檢查 CUDA
nvcc --version
```

### 日誌位置

```bash
# 應用日誌
docker-compose logs api

# 數據庫日誌
docker-compose logs postgres
docker-compose logs neo4j

# 結構化日誌 (JSON 格式)
tail -f logs/app.log | jq
```

---

## 📚 下一步

- 📖 閱讀完整文檔：`README.md`
- 🎬 觀看教程視頻：[待添加]
- 💬 加入社區：[待添加]
- 🐛 報告問題：GitHub Issues

---

## ✅ 檢查清單

啟動後確認以下內容：

- [ ] Web UI 可訪問 (http://localhost:8888)
- [ ] API 文檔可訪問 (http://localhost:8888/docs)
- [ ] 健康檢查通過 (`/health` 返回 healthy)
- [ ] 數據庫連接正常
- [ ] 文件上傳正常
- [ ] 視頻生成正常 (如有 GPU)

祝使用愉快！🎉
