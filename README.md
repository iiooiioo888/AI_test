# Enterprise AI Video Production Platform (AVP)

<p align="center">
  <strong>企業級 AI 視頻生產平台</strong><br>
  <sub>端到端視頻生成系統 · 劇本創作 · 提示詞優化 · 智能擴展 · 生產管理</sub>
</p>

<p align="center">
  <a href="https://fastapi.tiangolo.com"><img src="https://img.shields.io/badge/FastAPI-0.135-009688?style=for-the-badge&logo=fastapi&logoColor=white" alt="FastAPI"></a>
  <a href="https://pytorch.org"><img src="https://img.shields.io/badge/PyTorch-2.6-EE4C2C?style=for-the-badge&logo=pytorch&logoColor=white" alt="PyTorch"></a>
  <a href="https://www.postgresql.org"><img src="https://img.shields.io/badge/PostgreSQL-16-336791?style=for-the-badge&logo=postgresql&logoColor=white" alt="PostgreSQL"></a>
  <a href="https://neo4j.com"><img src="https://img.shields.io/badge/Neo4j-5.x-018BFF?style=for-the-badge&logo=neo4j&logoColor=white" alt="Neo4j"></a>
  <a href="https://milvus.io"><img src="https://img.shields.io/badge/Milvus-2.5-00A1EA?style=for-the-badge&logo=milvus&logoColor=white" alt="Milvus"></a>
  <a href="https://kubernetes.io"><img src="https://img.shields.io/badge/Kubernetes-1.29-326CE5?style=for-the-badge&logo=kubernetes&logoColor=white" alt="Kubernetes"></a>
</p>

---

## 📋 目錄

- [概述](#概述)
- [核心模組](#核心模組)
- [系統架構](#系統架構)
- [技術棧](#技術棧)
- [快速開始](#快速開始)
- [API 文檔](#api-文檔)
- [部署指南](#部署指南)
- [安全合規](#安全合規)

---

## 概述

Enterprise AI Video Production Platform (AVP) 是一套端到端的企業級 AI 視頻生成系統，涵蓋從劇本創作、提示詞優化、視頻生成、智能擴展到生產管理的全鏈路閉環。

### 核心優勢

| 特性 | 描述 |
|------|------|
| **JSON 結構化場景** | 採用 JSON 結構化存儲場景，支持版本控制與分支管理 |
| **知識圖譜** | Neo4j 存儲角色/情節/道具依賴關係，實現漣漪效應分析 |
| **狀態機** | 嚴格的場景区生命周期管理 (DRAFT → REVIEW → LOCKED → QUEUED → GENERATING → COMPLETED) |
| **CRDT 協作** | 支持多人實時編輯，字段級權限控制 (RBAC) |
| **RAG 提示詞優化** | 集成向量檢索，自動生成負向提示詞與權重調整 |
| **一致性鎖定** | 角色 ID、風格向量、場景約束跨片段鎖定 |
| **企業級監控** | Prometheus + Grafana 全鏈路監控 |

---

## 核心模組

### 1. 敘事與劇本引擎 (Narrative Engine)

```
┌─────────────────────────────────────────────────────────┐
│                   Narrative Engine                       │
├─────────────────────────────────────────────────────────┤
│  • JSON 結構化場景存儲                                    │
│  • Neo4j 知識圖譜 (角色/情節/道具依賴)                    │
│  • 場景区生命周期狀態機                                   │
│  • CRDT 多人實時編輯                                     │
│  • 漣漪效應分析                                          │
│  • 多版本分支管理                                        │
└─────────────────────────────────────────────────────────┘
```

**關鍵指標:**
- 場景修改觸發全局連貫性檢查 < 100ms
- 支持 100+ 協作者同時編輯
- 版本歷史保留 90 天

### 2. 提示詞優化模組 (Prompt Engineering Core)

```
┌─────────────────────────────────────────────────────────┐
│               Prompt Engineering Core                    │
├─────────────────────────────────────────────────────────┤
│  輸入解析 → 優化生成 (LLM + 進化算法) → 質量評估 → 輸出適配  │
│                                                         │
│  • RAG 檢索歷史成功案例                                   │
│  • 自動生成負向提示詞                                    │
│  • 提示詞版本控制 (Git-like)                             │
│  • 標籤系統與模板市場                                    │
└─────────────────────────────────────────────────────────┘
```

**目標指標:**
- 一次成功率 > 85%
- 提示詞復用率 > 60%

### 3. 視頻生成與擴展引擎 (Video Generation & Continuation)

```
┌─────────────────────────────────────────────────────────┐
│            Video Generation & Continuation               │
├─────────────────────────────────────────────────────────┤
│  核心模型：SVD, AnimateDiff, ControlNet, IP-Adapter      │
│                                                         │
│  • 線性延續 / 分支劇情 / 實時直播擴展                     │
│  • 無縫幀融合                                            │
│  • 角色 ID (FaceID) 鎖定                                 │
│  • 風格向量 (LoRA) 鎖定                                  │
│  • 場景約束 (Depth Map) 鎖定                             │
│  • 分塊流式生成 → 邊界融合 → 質量閉環                    │
└─────────────────────────────────────────────────────────┘
```

### 4. 生產控制與 MLOps (Production Control)

```
┌─────────────────────────────────────────────────────────┐
│                  Production Control                      │
├─────────────────────────────────────────────────────────┤
│  • 雙向同步：劇本修改 → 視頻重生成                        │
│  • Kubernetes GPU 集群調度                               │
│  • Prometheus + Grafana 監控                            │
│  • 內容合規預檢 (Azure Content Safety)                  │
│  • 數字水印 (C2PA)                                      │
│  • 操作審計日誌                                          │
└─────────────────────────────────────────────────────────┘
```

---

## 系統架構

```
┌─────────────────────────────────────────────────────────────────────┐
│                            Client Layer                              │
│  ┌──────────────┐  ┌───────────────┐  ┌─────────────────────────┐   │
│  │  Web App     │  │  Mobile App   │  │  API Clients            │   │
│  │  (Next.js)   │  │  (React Native)│  │  (SDK / CLI)            │   │
│  └──────┬───────┘  └───────┬───────┘  └───────────┬─────────────┘   │
└─────────┼──────────────────┼───────────────────────┼─────────────────┘
          │ HTTPS/WSS        │ HTTPS/WSS             │ HTTPS
┌─────────▼──────────────────▼───────────────────────▼─────────────────┐
│                         API Gateway (Kong)                            │
│         Rate Limiting · Authentication · Load Balancing               │
└────────────────────────────────┬──────────────────────────────────────┘
                                 │
┌────────────────────────────────▼──────────────────────────────────────┐
│                      FastAPI Application Cluster                      │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  │
│  │  Auth       │  │  Narrative  │  │  Prompt     │  │  Generation │  │
│  │  Service    │  │  Service    │  │  Service    │  │  Service    │  │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘  │
└────────────────────────────────┬──────────────────────────────────────┘
                                 │
          ┌──────────────────────┼──────────────────────┐
          │                      │                      │
┌─────────▼─────────┐  ┌────────▼──────────┐  ┌────────▼──────────┐    │
│   PostgreSQL      │  │    Neo4j          │  │    Milvus         │    │
│   (業務數據)       │  │    (知識圖譜)      │  │    (向量檢索)      │    │
│                   │  │                   │  │                   │    │
│  - Users/RBAC     │  │  - Characters     │  │  - Prompts        │    │
│  - Projects       │  │  - Relationships  │  │  - Scenes         │    │
│  - Scenes         │  │  - Dependencies   │  │  - Styles         │    │
│  - Generation     │  │  - Ripple Effect  │  │  - Similarity     │    │
│  - Audit Logs     │  │                   │  │                   │    │
└───────────────────┘  └───────────────────┘  └───────────────────┘    │
          │
┌─────────▼──────────────────────────────────────────────────────────┐
│                        Kubernetes Cluster                           │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │                    GPU Worker Nodes                           │  │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐     │  │
│  │  │ SVD      │  │ Animate  │  │ Control  │  │ IP-      │     │  │
│  │  │ Worker   │  │ Diff     │  │ Net      │  │ Adapter  │     │  │
│  │  │          │  │ Worker   │  │ Worker   │  │ Worker   │     │  │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘     │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                                                     │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐     │
│  │  Redis          │  │  MinIO/S3       │  │  Prometheus     │     │
│  │  (Cache/Queue)  │  │  (Storage)      │  │  (Monitoring)   │     │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 技術棧

| 層級 | 技術 | 版本 | 用途 |
|------|------|------|------|
| **Backend** | FastAPI | 0.135+ | RESTful API |
| | Python | 3.10+ | 運行環境 |
| | PyTorch | 2.6+ | 深度学习框架 |
| **Database** | PostgreSQL | 16+ | 業務數據 |
| | Neo4j | 5.x | 知識圖譜 |
| | Milvus | 2.5+ | 向量檢索 |
| | Redis | 7.x | 緩存/隊列 |
| **AI/ML** | Diffusers | 0.32+ | 視頻生成模型 |
| | Transformers | 4.49+ | LLM 集成 |
| | OpenCV | 4.x | 圖像處理 |
| **Infra** | Kubernetes | 1.29+ | 容器編排 |
| | Docker | 25.x | 容器化 |
| | Terraform | 1.x | IaC |
| **Monitoring** | Prometheus | 2.x | 指標收集 |
| | Grafana | 10.x | 可視化 |
| | Structlog | 25.x | 結構化日誌 |
| **Security** | OAuth 2.0 | - | 認證 |
| | Vault | - | 密鑰管理 |
| | C2PA | - | 數字水印 |

---

## 快速開始

### 環境需求

| 依賴 | 最低版本 | 用途 |
|------|---------|------|
| Python | 3.10 | 運行環境 |
| PostgreSQL | 16 | 業務數據庫 |
| Neo4j | 5.x | 知識圖譜 |
| Milvus | 2.5 | 向量檢索 |
| Redis | 7 | 緩存 |
| Docker | 25 | 容器化 |
| NVIDIA GPU | RTX 3090+ | 視頻生成 |

### 安裝

```bash
# 克隆代碼庫
git clone https://github.com/iiooiioo888/AI_test.git
cd AI_test

# 創建虛擬環境
python3 -m venv venv && source venv/bin/activate

# 安裝依賴
pip install -r requirements.txt

# 配置環境變數
cp .env.example .env
# 編輯 .env 文件，配置數據庫連接等

# 初始化數據庫
python -m app.db.init

# 啟動應用
python -m app.main
```

### 啟動服務

```bash
# 開發環境
python -m app.main

# 生產環境 (多 worker)
uvicorn app.main:app --host 0.0.0.0 --port 8888 --workers 4

# Docker Compose
docker-compose up -d
```

---

## API 文檔

啟動應用後訪問：
- Swagger UI: http://localhost:8888/docs
- ReDoc: http://localhost:8888/redoc
- OpenAPI JSON: http://localhost:8888/openapi.json

### 核心端點

| 方法 | 路徑 | 說明 |
|------|------|------|
| `POST` | `/api/v1/scenes/` | 創建場景 |
| `GET` | `/api/v1/scenes/{id}` | 獲取場景詳情 |
| `POST` | `/api/v1/scenes/{id}/transition` | 狀態轉換 |
| `GET` | `/api/v1/scenes/{id}/impact-analysis` | 漣漪效應分析 |
| `POST` | `/api/v1/prompts/optimize` | 優化提示詞 |
| `POST` | `/api/v1/generation/submit` | 提交生成任務 |

---

## 部署指南

### Docker Compose (開發環境)

```yaml
version: '3.8'
services:
  api:
    build: .
    ports:
      - "8888:8888"
    environment:
      - DATABASE_URL=postgresql://avp:password@postgres:5432/avp
      - NEO4J_URI=bolt://neo4j:7687
      - MILVUS_HOST=milvus
    depends_on:
      - postgres
      - neo4j
      - milvus

  postgres:
    image: postgres:16
    environment:
      - POSTGRES_DB=avp
      - POSTGRES_USER=avp
      - POSTGRES_PASSWORD=password

  neo4j:
    image: neo4j:5
    environment:
      - NEO4J_AUTH=neo4j/password

  milvus:
    image: milvusdb/milvus:v2.5.0

  redis:
    image: redis:7
```

### Kubernetes (生產環境)

詳見 `kubernetes/` 目錄。

---

## 安全合規

### SOC2/ISO27001 合規

- ✅ 字段級加密 (AES-256)
- ✅ 審計日誌 (不可篡改)
- ✅ RBAC 權限控制
- ✅ 操作審計追蹤
- ✅ 數據備份與災備恢復
- ✅ C2PA 數字水印

### 內容安全

- Azure Content Safety 集成
- 敏感詞過濾
- 版權保護 (圖像指紋)

---

## 授權

本專案以 MIT 授權條款釋出。

---

## 聯繫

- GitHub: https://github.com/iiooiioo888/AI_test
- 文檔：https://docs.openclaw.ai
