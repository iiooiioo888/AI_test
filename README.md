<div align="center">

# AVP

**Enterprise AI Video Production Platform** · 企業級 AI 視頻生產平台

> 從劇本到銀幕 — 端到端 AI 視頻生成系統

&nbsp;

[![CI](https://img.shields.io/github/actions/workflow/status/iiooiioo888/AI_test/ci.yml?branch=main&style=flat-square&label=CI&color=2ea44f)](https://github.com/iiooiioo888/AI_test/actions)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.135-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-336791?style=flat-square&logo=postgresql&logoColor=white)](https://www.postgresql.org)
[![Neo4j](https://img.shields.io/badge/Neo4j-5.x-018BFF?style=flat-square&logo=neo4j&logoColor=white)](https://neo4j.com)
[![License](https://img.shields.io/badge/License-MIT-blue?style=flat-square)](LICENSE)

&nbsp;

[**快速開始**](#-快速開始) · [**架構**](#️-架構) · [**API**](#-api) · [**任務待開發**](#-任務待開發) · [**路線圖**](#-路線圖) · [**貢獻**](#-貢獻)

</div>

---

## 為什麼是 AVP？

| 傳統流程 | AVP 方式 |
|:---|:---|
| 手動剪輯、逐幀調整 | AI 端到端自動生成 |
| 劇本與視頻割裂管理 | JSON 結構化場景 ↔ 視圖雙向同步 |
| 改一個場景，全片重來 | 知識圖譜漣漪分析，精準定位影響範圍 |
| 單人作業，版本混亂 | CRDT 多人實時編輯，字段級鎖 |
| 無法追溯 | 不可篡改審計日誌 + C2PA 數字水印 |

---

## ✨ 特性

<table>
<tr>
<td width="50%">

### 📖 智能敘事引擎

- JSON 結構化場景（敘事/對話/視覺/音頻/過渡）
- Neo4j 知識圖譜 — 角色 · 道具 · 情節依賴
- BFS 漣漪效應分析 — 改一個場景，自動檢查全片連貫性
- 7 態嚴格生命周期：`DRAFT → REVIEW → LOCKED → QUEUED → GENERATING → COMPLETED / FAILED`

</td>
<td width="50%">

### 🤝 實時協作

- Yjs CRDT — 無衝突多人編輯
- 向量時鐘 + LWW-Element-Set 衝突解決
- 字段級鎖 — 精確到單一對白行
- RBAC 5 角色：admin · director · writer · reviewer · viewer

</td>
</tr>
<tr>
<td width="50%">

### 🧠 提示詞優化 *(規劃中)*

- RAG 檢索歷史成功案例
- LLM API 進化算法自動優化
- 自動生成負向提示詞 + 權重
- 提示詞版本控制 (Git-like)

</td>
<td width="50%">

### 🎥 AI 視頻生成 *(規劃中)*

- 調用外部 AI 視頻生成 API（Sora · Kling · Runway 等）
- 角色 ID + 風格約束 + 場景一致性鎖定
- 分塊流式生成 → 邊界融合 → 質量閉環
- 線性延續 / 分支劇情 / 實時直播擴展

</td>
</tr>
</table>

---

## 🏗️ 架構

```mermaid
graph LR
    subgraph clients["🖥️ Clients"]
        WEB["🌐 Web<br/><code>Next.js</code>"]
        MOB["📱 Mobile<br/><code>RN</code>"]
        CLI["⌨️ CLI / SDK"]
    end

    subgraph gateway["🔀 Gateway"]
        GW["Kong<br/>Rate Limit · Auth · LB"]
    end

    subgraph app["⚡ FastAPI Services"]
        S1["Auth"]
        S2["📖 Narrative<br/>Engine"]
        S3["🧠 Prompt<br/>Engine"]
        S4["🎥 Generation<br/>Orchestrator"]
    end

    subgraph store["💾 Data"]
        PG[("🐘 PostgreSQL")]
        N4J[("🕸️ Neo4j")]
        MIL[("🔍 Milvus")]
        RDS[("⚡ Redis")]
    end

    subgraph llm["🤖 AI Providers (External APIs)"]
        LLM1["OpenAI"]
        LLM2["Anthropic"]
        LLM3["Video API<br/><i>Sora · Kling · Runway</i>"]
    end

    WEB & MOB & CLI --> GW
    GW --> S1 & S2 & S3 & S4
    S1 & S2 & S3 & S4 --> PG & N4J & MIL & RDS
    S3 --> LLM1 & LLM2
    S4 --> LLM3

    style clients fill:none,stroke:none
    style gateway fill:none,stroke:none
    style app fill:none,stroke:none
    style store fill:none,stroke:none
    style llm fill:none,stroke:none
```

<details>
<summary>📖 敘事引擎內部結構</summary>

```mermaid
graph TD
    A["SceneObject<br/><i>JSONB content · metadata · status</i>"] --> B["StateMachine<br/><i>7 態轉換 + Guard 系統</i>"]
    A --> C["KnowledgeGraph<br/><i>Neo4j LEADS_TO · CONTAINS · REQUIRES</i>"]
    A --> D["CRDT Engine<br/><i>Yjs 字段級同步</i>"]
    C --> E["RippleEffectAnalyzer<br/><i>BFS 遍歷衝突檢測</i>"]
    B --> F["StateTransitionError<br/><i>非法轉移攔截 + 診斷上下文</i>"]
    E --> G["衝突報告<br/><i>角色 · 道具 · 時間線 · 情緒弧線</i>"]
    A --> H["Branching<br/><i>Git-like 版本分支</i>"]
```

</details>

---

## 🛠️ 技術棧

```
Backend       FastAPI 0.135  ·  Python 3.10+
Database      PostgreSQL 16  ·  Neo4j 5.x  ·  Milvus 2.5  ·  Redis 7
LLM           OpenAI API  ·  Anthropic API  ·  (多 provider 可擴展)
Video Gen     Sora · Kling · Runway (外部 API 調用)
Embeddings    OpenAI text-embedding-3-large (768 維)
Infra         Docker 25  ·  Docker Compose  ·  (可選 K8s)
Observe       Prometheus  ·  Grafana  ·  Structlog
Security      OAuth 2.0  ·  Vault  ·  C2PA  ·  AES-256
```

---

## 🚀 快速開始

```bash
# 1 — 克隆
git clone https://github.com/iiooiioo888/AI_test.git && cd AI_test

# 2 — 環境
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# 3 — 配置
cp .env.example .env        # ← 填入 API Key、資料庫連線等

# 4 — 初始化 & 啟動
python -m app.db.init
python -m app.main          # → http://localhost:8888
```

**生產環境：**

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8888 --workers 4
docker compose up -d
```

> **前置需求：** `Python 3.10+` · `PostgreSQL 16` · `Neo4j 5.x` · `Milvus 2.5` · `Redis 7` · `Docker 25` · `LLM API Key (OpenAI / Anthropic)`

---

## 📡 API

啟動後 → [**Swagger UI**](http://localhost:8888/docs) · [ReDoc](http://localhost:8888/redoc) · [OpenAPI](http://localhost:8888/openapi.json)

### 敘事引擎 (Narrative Engine)

| 方法 | 端點 | 狀態碼 | 說明 |
|:---:|:---|:---:|:---|
| `POST` | `/api/v1/narrative/scenes` | `201` | 創建場景 |
| `GET` | `/api/v1/narrative/scenes/{id}` | `200` | 獲取場景詳情 |
| `GET` | `/api/v1/narrative/scenes` | `200` | 列出場景 (支持 state / branch 過濾) |
| `PATCH` | `/api/v1/narrative/scenes/{id}` | `200` / `409` | 部分更新 + 漣漪分析 (衝突時返回 409) |
| `POST` | `/api/v1/narrative/scenes/{id}/transition` | `200` / `422` | 狀態轉換 (非法轉移返回 422) |
| `GET` | `/api/v1/narrative/scenes/{id}/valid-transitions` | `200` | 查詢可用的下一步狀態 |
| `GET` | `/api/v1/narrative/scenes/{id}/impact-analysis` | `200` | 漣漪效應完整分析報告 |
| `GET` | `/api/v1/narrative/scenes/{id}/graph` | `200` | 場景中心的依賴圖譜 |
| `POST` | `/api/v1/narrative/scenes/{id}/branch` | `201` | 創建劇情分支 → 新版本 ID |
| `GET` | `/api/v1/narrative/scripts/{id}/graph` | `200` | 完整劇情依賴圖譜 (JSON) |
| `GET` | `/api/v1/narrative/consistency/global` | `200` | 全局一致性檢查 |
| `GET` | `/api/v1/narrative/stats` | `200` | 引擎統計資訊 |

### 視頻處理

| 方法 | 端點 | 說明 |
|:---:|:---|:---|
| `POST` | `/api/upload` | 上傳視頻 |
| `POST` | `/api/process/effect` | 應用 AI 特效 |
| `POST` | `/api/process/extend` | 視頻擴展處理 |
| `GET` | `/api/download/{task_id}` | 下載處理結果 |
| `GET` | `/api/effects` | 特效列表 |

### 其他

| 方法 | 端點 | 說明 |
|:---:|:---|:---|
| `POST` | `/api/v1/scenes/` | 創建場景 (舊版) |
| `POST` | `/api/v1/prompts/optimize` | 優化提示詞 |
| `POST` | `/api/v1/generation/submit` | 提交生成任務 |
| `GET` | `/health` | 健康檢查 |

---

## 🚢 部署

<details>
<summary>🐳 Docker Compose — 開發環境</summary>

```yaml
services:
  api:
    build: .
    ports: ["8888:8888"]
    environment:
      DATABASE_URL: postgresql://avp:password@postgres:5432/avp
      NEO4J_URI: bolt://neo4j:7687
      MILVUS_HOST: milvus
      OPENAI_API_KEY: ${OPENAI_API_KEY}
      ANTHROPIC_API_KEY: ${ANTHROPIC_API_KEY}
    depends_on: [postgres, neo4j, milvus]

  postgres:
    image: postgres:16
    environment: { POSTGRES_DB: avp, POSTGRES_USER: avp, POSTGRES_PASSWORD: password }

  neo4j:
    image: neo4j:5
    environment: { NEO4J_AUTH: neo4j/password }

  milvus:
    image: milvusdb/milvus:v2.5.0

  redis:
    image: redis:7
```

</details>

<details>
<summary>☸️ Kubernetes — 生產環境</summary>

詳見 [`kubernetes/`](kubernetes/) 目錄。

</details>

---

## 🔐 安全

<div align="center">

| 🔑 加密 | 📝 審計 | 👥 RBAC | 🔍 追蹤 | 💾 備份 | 🏷️ 水印 |
|:---:|:---:|:---:|:---:|:---:|:---:|
| AES-256 | 不可篡改 | 5 角色 | 全操作 | 災備恢復 | C2PA |

</div>

合規：**SOC2** · **ISO27001** · 內容安全：Azure Content Safety · 敏感詞過濾 · 圖像指紋

---

## 📋 任務待開發

> **Role:** 高級後端架構師 (敘事系統專項) · **Context:** 項目 Nexus — 企業級 AI 視頻生產平台

### 1. 數據模型 (Data Model)

| 數據存儲 | Schema 定義 | 狀態 |
|:---|:---|:---:|
| **PostgreSQL** | `scenes` — JSONB `content` · `metadata` · `status` · `version` (SemVer) · `audit_log` | ✅ 已完成 |
| **Neo4j** | 節點: `Scene` · `Character` · `Prop` / 關係: `LEADS_TO` · `CONTAINS` · `REQUIRES` | ✅ 已完成 |
| **Milvus** | 768 維場景語義向量 — 相似度檢索 + 衝突檢測 | ✅ 已完成 |

### 2. 核心邏輯 (Core Logic)

| 模塊 | 類名 | 功能 | 狀態 |
|:---|:---|:---|:---:|
| 🔄 狀態機 | `StateMachineService` | `DRAFT → REVIEW → LOCKED → COMPLETED` · `StateTransitionError` + Guard 系統 + 批量驗證 + 最短路徑查詢 | ✅ |
| 🌊 漣漪效應 | `RippleEffectAnalyzer` | BFS 遍歷 `LEADS_TO` · 角色死亡/道具銷毀/時間線/情緒弧線衝突檢測 | ✅ |
| 🤝 協作同步 | `CRDTEngine` | Yjs CRDT · 字段級鎖 · Undo/Redo · 快照 | ✅ |

### 3. API 端點

| 方法 | 端點 | 狀態碼 | 狀態 |
|:---:|:---|:---:|:---:|
| `PATCH` | `/scenes/{id}` | `200` / `409` | ✅ |
| `GET` | `/scripts/{id}/graph` | `200` | ✅ |
| `POST` | `/scenes/{id}/branch` | `201` | ✅ |

### 4. 交付物

| 交付物 | 狀態 |
|:---|:---:|
| Alembic 遷移腳本 (PostgreSQL) | ✅ `app/db/migrations/001_create_scenes.py` |
| Neo4j 初始化 Cypher | ✅ `app/db/neo4j_init.cypher` |
| Milvus 向量庫 Schema | ✅ `app/db/milvus_schema.py` |
| FastAPI 服務代碼 | ✅ `app/narrative_engine/` |
| OpenAPI 文檔 | ✅ 自動生成 (`/docs`) |
| Type Hints · 錯誤處理 · 結構化日誌 | ✅ |

### 開發優先級

```
Phase 1 ✅ 更新前端 UI 代碼 (三欄式敘事管理 + 圖譜視圖)
Phase 2 ✅ 優化核心代碼 (狀態機 + 漣漪分析 + API 端點)
Phase 3 ✅ 數據庫遷移腳本與初始化
Phase 4   前端 → 後端 API 聯調 (fetch → 真實數據)
Phase 5   單元測試覆蓋 > 90%
```

---

## 📊 路線圖

<div align="center">

| # | 模塊 | 狀態 | 進度 |
|:---:|:---|:---:|:---:|
| **M1** | 📖 敘事與劇本引擎 | ✅ 完成 | `██████████` 100% |
| **M2** | 🧠 提示詞優化引擎 | 🚧 進行中 | `████░░░░░░` 40% |
| **M3** | 🎥 AI 視頻生成 | 📋 規劃中 | `░░░░░░░░░░` 0% |
| **M4** | 🔧 生產控制 | 📋 規劃中 | `░░░░░░░░░░` 0% |

</div>

```mermaid
gantt
    title 2025–2026 路線圖
    dateFormat YYYY-MM
    axisFormat %b %Y

    section 核心引擎
    M1 敘事引擎          :done,    m1, 2025-10, 5m
    M2 提示詞優化        :active,  m2, 2026-03, 3m
    M3 AI 視頻生成       :         m3, 2026-06, 3m
    M4 生產控制          :         m4, 2026-09, 3m

    section 基礎設施
    CI/CD Pipeline      :done,    ci, 2025-10, 3m
    LLM Provider 層     :active,  llm, 2026-02, 3m
    監控 & 可觀測        :         mon, 2026-05, 2m
```

---

## 📁 專案結構

```
AI_test/
├── app/
│   ├── api/v1/
│   │   ├── endpoints/          # REST 端點 (auth, scenes, characters...)
│   │   └── router.py           # 路由匯總
│   ├── core/
│   │   └── config.py           # 應用配置
│   ├── db/
│   │   ├── migrations/         # Alembic 遷移腳本
│   │   │   └── 001_create_scenes.py
│   │   ├── milvus_schema.py    # Milvus 向量庫 Schema
│   │   ├── neo4j_init.cypher   # Neo4j 初始化 (約束/索引/範例數據)
│   │   └── schema.sql          # PostgreSQL Schema
│   ├── narrative_engine/
│   │   ├── api/
│   │   │   └── routes.py       # 敘事 API (PATCH/GRAPH/BRANCH)
│   │   ├── crdt/
│   │   │   └── crdt_engine.py  # Yjs CRDT 協作引擎
│   │   ├── graph/
│   │   │   └── knowledge_graph.py  # Neo4j 知識圖譜服務
│   │   ├── models/
│   │   │   ├── scene.py        # SceneObject 數據模型
│   │   │   └── character.py    # Character / Prop 模型
│   │   └── services/
│   │       ├── state_machine.py      # 狀態機 (Guard + TransitionError)
│   │       ├── ripple_analyzer.py    # 漣漪效應分析器
│   │       └── narrative_service.py  # 敘事引擎編排器
│   ├── schemas/                # Pydantic Schema
│   ├── shared/
│   │   └── __init__.py         # 共享枚舉 (SceneState, Role, AuditEntry)
│   └── main.py                 # FastAPI 入口
├── static/
│   ├── css/style.css           # 前端樣式 (深色主題)
│   └── js/app.js               # 前端邏輯 (視頻 + 敘事 + 圖譜)
├── templates/
│   └── index.html              # 主頁面 (三欄式敘事管理)
├── tests/
│   └── narrative_engine/       # 測試 (待補充)
├── docker-compose.yml
├── Dockerfile
├── main.py                     # 入口 (視頻處理模式)
└── requirements.txt
```

---

## 🤝 貢獻

```
Fork → Branch → Commit → Push → PR
```

```bash
git checkout -b feat/your-feature
git commit -m "feat: your feature"
git push origin feat/your-feature
# → 開啟 Pull Request
```

請確保 PR 通過 CI pipeline 並附帶文檔更新。

---

## 📄 授權

[MIT](LICENSE)

---

<div align="center">

**[GitHub](https://github.com/iiooiioo888/AI_test)** · **[文檔](https://docs.openclaw.ai)**

<sub>Built with ⚡ by the AVP team</sub>

</div>
