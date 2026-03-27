<div align="center">

# 🎬 AVP — AI Video Production Platform

**企業級 AI 視頻生產平台**

端到端視頻生成 · 劇本創作 · 提示詞優化 · 智能擴展 · 生產管理

[![FastAPI](https://img.shields.io/badge/FastAPI-0.135-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![PyTorch](https://img.shields.io/badge/PyTorch-2.6-EE4C2C?style=flat-square&logo=pytorch&logoColor=white)](https://pytorch.org)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-336791?style=flat-square&logo=postgresql&logoColor=white)](https://www.postgresql.org)
[![Neo4j](https://img.shields.io/badge/Neo4j-5.x-018BFF?style=flat-square&logo=neo4j&logoColor=white)](https://neo4j.com)
[![Milvus](https://img.shields.io/badge/Milvus-2.5-00A1EA?style=flat-square&logo=milvus&logoColor=white)](https://milvus.io)
[![Kubernetes](https://img.shields.io/badge/Kubernetes-1.29-326CE5?style=flat-square&logo=kubernetes&logoColor=white)](https://kubernetes.io)
[![License](https://img.shields.io/badge/License-MIT-blue?style=flat-square)](#授權)

</div>

---

## ✨ 核心特性

| | |
|:---:|:---|
| 🧩 | **JSON 結構化場景** — 版本控制 + 分支管理，場景即數據 |
| 🕸️ | **知識圖譜** — Neo4j 角色/情節/道具依賴，漣漪效應自動分析 |
| ⚙️ | **狀態機** — 嚴格生命周期 `DRAFT → REVIEW → LOCKED → … → COMPLETED` |
| 🤝 | **CRDT 協作** — 多人實時編輯，字段級鎖 + 向量時鐘 |
| 🔍 | **RAG 提示詞優化** — 向量檢索歷史案例，自動負向提示詞 |
| 🔒 | **一致性鎖定** — 角色 ID / 風格向量 / 場景約束跨片段鎖定 |
| 📊 | **企業級監控** — Prometheus + Grafana 全鏈路可觀測 |

---

## 🏗️ 系統架構

```mermaid
graph TB
    subgraph Client["🖥️ Client Layer"]
        WEB["Web App<br/><i>Next.js</i>"]
        MOB["Mobile App<br/><i>React Native</i>"]
        SDK["API Clients<br/><i>SDK / CLI</i>"]
    end

    subgraph Gateway["🔀 API Gateway (Kong)"]
        GW["Rate Limiting · Auth · Load Balancing"]
    end

    subgraph Services["⚡ FastAPI Cluster"]
        AUTH["Auth Service"]
        NARR["Narrative<br/>Engine"]
        PROM["Prompt<br/>Engine"]
        GEN["Generation<br/>Engine"]
    end

    subgraph Data["💾 Data Layer"]
        PG[("PostgreSQL<br/>業務數據")]
        N4J[("Neo4j<br/>知識圖譜")]
        MIL[("Milvus<br/>向量檢索")]
        RDS[("Redis<br/>緩存/隊列")]
    end

    subgraph Infra["☁️ Kubernetes Cluster"]
        GPU["GPU Workers<br/>SVD · AnimateDiff · ControlNet"]
        S3["MinIO / S3"]
        MON["Prometheus<br/>+ Grafana"]
    end

    WEB & MOB & SDK --> GW
    GW --> AUTH & NARR & PROM & GEN
    AUTH & NARR & PROM & GEN --> PG & N4J & MIL & RDS
    GEN --> GPU
    GPU --> S3
    MON -.-> Services
    MON -.-> GPU
```

<details>
<summary>📐 詳細架構圖 (展開)</summary>

```mermaid
graph LR
    subgraph NarrativeEngine["📖 Narrative Engine"]
        NE1["SceneObject<br/>敘事/對話/視覺/音頻/過渡"]
        NE2["KnowledgeGraph<br/>BFS 漣漪效應"]
        NE3["StateMachine<br/>7 態生命周期"]
        NE4["CRDT Engine<br/>LWW 字段級衝突"]
    end

    subgraph PromptEngine["🧠 Prompt Engineering"]
        PE1["RAG 檢索"]
        PE2["進化算法優化"]
        PE3["版本控制"]
    end

    subgraph VideoEngine["🎥 Video Generation"]
        VE1["SVD / AnimateDiff"]
        VE2["ControlNet / IP-Adapter"]
        VE3["無縫幀融合"]
    end

    subgraph MLOps["🔧 Production Control"]
        MO1["雙向同步"]
        MO2["GPU 調度"]
        MO3["C2PA 水印"]
        MO4["合規預檢"]
    end

    NE1 --> PE1
    PE2 --> VE1
    VE1 --> MO1
```

</details>

---

## 🧱 核心模組

### 📖 1. 敘事與劇本引擎 — ✅ 已完成

- **JSON 結構化場景** — SceneObject 完整模型（敘事/對話/視覺/音頻/過渡）
- **Neo4j 知識圖譜** — 角色/道具/場景依賴圖 + BFS 漣漪效應分析
- **狀態機** — 嚴格 7 態生命周期（`DRAFT→REVIEW→LOCKED→QUEUED→GENERATING→COMPLETED/FAILED`）
- **CRDT 協作** — LWW-Element-Set 字段級衝突解決 + 向量時鐘
- **RBAC 權限** — 5 角色（admin/director/writer/reviewer/viewer）字段級控制
- **版本分支** — 場景分支創建 + 父版本追蹤
- **小說改編** — 文本自動拆分為結構化場景
- **一致性檢查** — 全局圖完整性 + 漣漪效應分析
- **API 層** — FastAPI 完整 CRUD + 狀態轉換 + 分支端點
- **CI/CD** — GitHub Actions 自動化部署 pipeline

```
app/narrative_engine/
├── models/          # SceneObject, Character, Prop, StoryArc
├── graph/           # KnowledgeGraphService (漣漪效應分析)
├── services/        # NarrativeEngine (編排), StateMachine
├── crdt/            # CRDTEngine (LWW 字段級衝突解決)
└── api/             # FastAPI Routes (/api/v1/narrative/*)
```

### 🧠 2. 提示詞優化引擎 — 🔜 規劃中

`輸入解析 → 優化生成 (LLM + 進化算法) → 質量評估 → 輸出適配`

> **目標:** 一次成功率 > 85% · 提示詞復用率 > 60%

### 🎥 3. 視頻生成與擴展引擎 — 🔜 規劃中

> SVD · AnimateDiff · ControlNet · IP-Adapter — 線性延續 / 分支劇情 / 實時直播擴展

### 🔧 4. 生產控制與 MLOps — 🔜 規劃中

> 雙向同步 · K8s GPU 調度 · Prometheus 監控 · C2PA 數字水印 · Azure Content Safety

---

## 🛠️ 技術棧

<div align="center">

| 層級 | 技術 |
|:---:|:---|
| **Backend** | `FastAPI` `Python 3.10+` `PyTorch 2.6` |
| **Database** | `PostgreSQL 16` `Neo4j 5.x` `Milvus 2.5` `Redis 7` |
| **AI/ML** | `Diffusers` `Transformers` `OpenCV` |
| **Infra** | `Kubernetes 1.29` `Docker 25` `Terraform` |
| **Observability** | `Prometheus` `Grafana` `Structlog` |
| **Security** | `OAuth 2.0` `Vault` `C2PA` |

</div>

---

## 🚀 快速開始

### 前置需求

`Python 3.10+` · `PostgreSQL 16` · `Neo4j 5.x` · `Milvus 2.5` · `Redis 7` · `Docker 25` · `NVIDIA GPU (RTX 3090+)`

### 安裝與啟動

```bash
# 克隆
git clone https://github.com/iiooiioo888/AI_test.git && cd AI_test

# 虛擬環境
python3 -m venv venv && source venv/bin/activate

# 依賴
pip install -r requirements.txt

# 配置
cp .env.example .env   # ← 編輯此文件，填入資料庫連線等

# 初始化 & 啟動
python -m app.db.init
python -m app.main
```

```bash
# 生產環境 (多 worker)
uvicorn app.main:app --host 0.0.0.0 --port 8888 --workers 4

# Docker Compose
docker compose up -d
```

---

## 📡 API 端點

啟動後訪問 → [Swagger UI](http://localhost:8888/docs) · [ReDoc](http://localhost:8888/redoc) · [OpenAPI JSON](http://localhost:8888/openapi.json)

| 方法 | 路徑 | 說明 |
|:---:|:---|:---|
| `POST` | `/api/v1/scenes/` | 創建場景 |
| `GET` | `/api/v1/scenes/{id}` | 獲取場景詳情 |
| `POST` | `/api/v1/scenes/{id}/transition` | 狀態轉換 |
| `GET` | `/api/v1/scenes/{id}/impact-analysis` | 漣漪效應分析 |
| `POST` | `/api/v1/prompts/optimize` | 優化提示詞 |
| `POST` | `/api/v1/generation/submit` | 提交生成任務 |

---

## 🚢 部署

<details>
<summary>🐳 Docker Compose (開發環境)</summary>

```yaml
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
      POSTGRES_DB: avp
      POSTGRES_USER: avp
      POSTGRES_PASSWORD: password

  neo4j:
    image: neo4j:5
    environment:
      NEO4J_AUTH: neo4j/password

  milvus:
    image: milvusdb/milvus:v2.5.0

  redis:
    image: redis:7
```

</details>

<details>
<summary>☸️ Kubernetes (生產環境)</summary>

詳見 [`kubernetes/`](kubernetes/) 目錄。

</details>

---

## 🔐 安全合規

**SOC2 / ISO27001**

| ✅ | 控制項 |
|:---:|:---|
| 🔑 | 字段級加密 (AES-256) |
| 📝 | 不可篡改審計日誌 |
| 👥 | RBAC 權限控制 |
| 🔍 | 操作審計追蹤 |
| 💾 | 數據備份與災備恢復 |
| 🏷️ | C2PA 數字水印 |

**內容安全:** Azure Content Safety · 敏感詞過濾 · 圖像指紋版權保護

---

## 📊 開發進度

```mermaid
gantt
    title AVP 開發路線圖
    dateFormat  YYYY-MM
    axisFormat  %Y-%m

    section 核心引擎
    敘事與劇本引擎       :done,    m1, 2025-10, 2026-03
    提示詞優化引擎       :active,  m2, 2026-03, 2026-06
    視頻生成引擎         :         m3, 2026-06, 2026-09
    生產控制 MLOps       :         m4, 2026-09, 2026-12

    section 基礎設施
    CI/CD Pipeline      :done,    ci, 2025-10, 2026-01
    K8s GPU 調度         :active,  k8s, 2026-02, 2026-05
    監控 & 可觀測        :         mon, 2026-05, 2026-07
```

| 模塊 | 狀態 | 進度 |
|:---|:---:|:---:|
| 1. 敘事與劇本引擎 | ✅ 完成 | ██████████ 100% |
| 2. 提示詞優化引擎 | 🔜 規劃中 | ░░░░░░░░░░ 0% |
| 3. 視頻生成引擎 | 🔜 規劃中 | ░░░░░░░░░░ 0% |
| 4. 生產控制 MLOps | 🔜 規劃中 | ░░░░░░░░░░ 0% |

---

## 📋 任務待開發

### 構建企業級 AI 敘事與劇本管理核心

> **Role:** 高級後端架構師 · **Context:** 項目 Nexus

<details>
<summary><strong>1. 數據模型 (Data Model)</strong></summary>

- **PostgreSQL** — `scenes` 表，JSONB `content` / `metadata` / `status`，含 `version` (SemVer) + `audit_log`
- **Neo4j** — 節點 `Scene` · `Character` · `Prop`，關係 `LEADS_TO` / `CONTAINS` / `REQUIRES`，唯一約束 + 索引
- **Milvus** — 768 維場景語義向量，相似度檢索 + 衝突檢測

</details>

<details>
<summary><strong>2. 核心邏輯 (Core Logic)</strong></summary>

- **`SceneStateMachine`** — `DRAFT → REVIEW → LOCKED → COMPLETED`，非法轉移拋 `StateTransitionError`
- **`RippleEffectAnalyzer`** — 遍歷 `LEADS_TO` 關係，檢查角色/道具邏輯衝突，返回報告
- **CRDT 協作** — Yjs 多人實時編輯，字段級鎖 (Field-Level Lock)

</details>

<details>
<summary><strong>3. API 規範 (API Contract)</strong></summary>

| 方法 | 路徑 | 說明 |
|:---:|:---|:---|
| `PATCH` | `/scenes/{id}` | 部分更新 + 漣漪分析 → `200` / `409` |
| `GET` | `/scripts/{id}/graph` | 劇情依賴圖譜 JSON |
| `POST` | `/scenes/{id}/branch` | 劇情分支，複製節點 + 新版本 ID |

</details>

<details>
<summary><strong>4. CI/CD 與交付</strong></summary>

- **CI/CD** — GitHub Actions：lint → type-check → build → deploy
- **交付物** — Alembic 遷移腳本 · Neo4j 初始化 Cypher · FastAPI 服務代碼 · OpenAPI 文檔
- **代碼規範** — Type Hints · 錯誤處理 · 結構化日誌

</details>

---

## 🤝 貢獻

1. Fork 本倉庫
2. 創建特性分支 (`git checkout -b feat/amazing-feature`)
3. 提交變更 (`git commit -m 'feat: add amazing feature'`)
4. 推送分支 (`git push origin feat/amazing-feature`)
5. 開啟 Pull Request

請確保所有 PR 通過 CI/CD pipeline 並附帶對應文檔更新。

---

## 📄 授權

本專案以 [MIT](LICENSE) 授權條款釋出。

---

<div align="center">

[GitHub](https://github.com/iiooiioo888/AI_test) · [文檔](https://docs.openclaw.ai)

</div>
