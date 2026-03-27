<div align="center">

<img src="https://raw.githubusercontent.com/iiooiioo888/AI_test/main/assets/avp-banner.svg" alt="AVP Banner" width="100%">

# AVP

**Enterprise AI Video Production Platform** · 企業級 AI 視頻生產平台

> 從劇本到銀幕 — 端到端 AI 視頻生成系統

&nbsp;

[![CI](https://img.shields.io/github/actions/workflow/status/iiooiioo888/AI_test/ci.yml?branch=main&style=flat-square&label=CI&color=2ea44f)](https://github.com/iiooiioo888/AI_test/actions)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.135-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![PyTorch](https://img.shields.io/badge/PyTorch-2.6-EE4C2C?style=flat-square&logo=pytorch&logoColor=white)](https://pytorch.org)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-336791?style=flat-square&logo=postgresql&logoColor=white)](https://www.postgresql.org)
[![Neo4j](https://img.shields.io/badge/Neo4j-5.x-018BFF?style=flat-square&logo=neo4j&logoColor=white)](https://neo4j.com)
[![License](https://img.shields.io/badge/License-MIT-blue?style=flat-square)](LICENSE)

&nbsp;

[**快速開始**](#-快速開始) · [**架構**](#️-架構) · [**API**](#-api) · [**路線圖**](#-路線圖) · [**貢獻**](#-貢獻)

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
- LLM + 進化算法自動優化
- 自動生成負向提示詞 + 權重
- 提示詞版本控制 (Git-like)

</td>
<td width="50%">

### 🎥 視頻生成 *(規劃中)*

- SVD · AnimateDiff · ControlNet · IP-Adapter
- 角色 ID (FaceID) + 風格向量 (LoRA) + 場景約束 (Depth Map) 鎖定
- 分塊流式生成 → 邊界融合 → 質量閉環
- 線性延續 / 分支劇情 / 實時直播擴展

</td>
</tr>
</table>

---

## 🏗️ 架構

```mermaid
graph LR
    subgraph clients[" "]
        direction LR
        WEB["🌐 Web<br/><code>Next.js</code>"]
        MOB["📱 Mobile<br/><code>RN</code>"]
        CLI["⌨️ CLI / SDK"]
    end

    subgraph api[" "]
        GW["🔀 Kong Gateway<br/>Rate Limit · Auth · LB"]
    end

    subgraph services[" "]
        direction TB
        S1["Auth"]
        S2["📖 Narrative"]
        S3["🧠 Prompt"]
        S4["🎥 Generation"]
    end

    subgraph data[" "]
        PG[("🐘 PostgreSQL")]
        N4J[("🕸️ Neo4j")]
        MIL[("🔍 Milvus")]
        RDS[("⚡ Redis")]
    end

    subgraph compute[" "]
        GPU["🖥️🖥️🖥️ GPU Cluster<br/>SVD · AnimateDiff · ControlNet"]
        S3B["📦 MinIO / S3"]
    end

    WEB & MOB & CLI --> GW
    GW --> S1 & S2 & S3 & S4
    S1 & S2 & S3 & S4 --> PG & N4J & MIL & RDS
    S4 --> GPU
    GPU --> S3B

    style clients fill:none,stroke:none
    style api fill:none,stroke:none
    style services fill:none,stroke:none
    style data fill:none,stroke:none
    style compute fill:none,stroke:none
```

<details>
<summary>📖 敘事引擎內部結構</summary>

```mermaid
graph TD
    A["SceneObject<br/><i>JSONB content · metadata · status</i>"] --> B["StateMachine<br/><i>7 態轉換</i>"]
    A --> C["KnowledgeGraph<br/><i>Neo4j LEADS_TO · CONTAINS · REQUIRES</i>"]
    A --> D["CRDT Engine<br/><i>Yjs 字段級同步</i>"]
    C --> E["RippleEffectAnalyzer<br/><i>BFS 遍歷衝突檢測</i>"]
    B --> F["StateTransitionError<br/><i>非法轉移攔截</i>"]
    E --> G["衝突報告<br/><i>409 Conflict</i>"]
```

</details>

---

## 🛠️ 技術棧

```
Backend     FastAPI 0.135  ·  Python 3.10+  ·  PyTorch 2.6
Database    PostgreSQL 16  ·  Neo4j 5.x  ·  Milvus 2.5  ·  Redis 7
AI / ML     Diffusers  ·  Transformers  ·  OpenCV
Infra       Kubernetes 1.29  ·  Docker 25  ·  Terraform
Observe     Prometheus  ·  Grafana  ·  Structlog
Security    OAuth 2.0  ·  Vault  ·  C2PA  ·  AES-256
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
cp .env.example .env        # ← 編輯填入資料庫連線

# 4 — 初始化 & 啟動
python -m app.db.init
python -m app.main          # → http://localhost:8888
```

**生產環境：**

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8888 --workers 4
docker compose up -d        # 或使用 Docker Compose
```

> **前置需求：** `Python 3.10+` · `PostgreSQL 16` · `Neo4j 5.x` · `Milvus 2.5` · `Redis 7` · `Docker 25` · `NVIDIA GPU (RTX 3090+)`

---

## 📡 API

啟動後 → [**Swagger UI**](http://localhost:8888/docs) · [ReDoc](http://localhost:8888/redoc) · [OpenAPI](http://localhost:8888/openapi.json)

| 方法 | 端點 | 說明 |
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

## 📊 路線圖

<div align="center">

| # | 模塊 | 狀態 | 進度 |
|:---:|:---|:---:|:---:|
| **M1** | 📖 敘事與劇本引擎 | ✅ 完成 | `██████████` 100% |
| **M2** | 🧠 提示詞優化引擎 | 🚧 進行中 | `████░░░░░░` 40% |
| **M3** | 🎥 視頻生成引擎 | 📋 規劃中 | `░░░░░░░░░░` 0% |
| **M4** | 🔧 生產控制 MLOps | 📋 規劃中 | `░░░░░░░░░░` 0% |

</div>

```mermaid
gantt
    title 2025–2026 路線圖
    dateFormat YYYY-MM
    axisFormat %b %Y

    section 核心引擎
    M1 敘事引擎          :done,    m1, 2025-10, 5m
    M2 提示詞優化        :active,  m2, 2026-03, 3m
    M3 視頻生成          :         m3, 2026-06, 3m
    M4 生產控制          :         m4, 2026-09, 3m

    section 基礎設施
    CI/CD Pipeline      :done,    ci, 2025-10, 3m
    K8s GPU 調度         :active,  k8s, 2026-02, 3m
    監控 & 可觀測        :         mon, 2026-05, 2m
```

---

## 📋 下一 Sprint

### 構建企業級 AI 敘事與劇本管理核心

> 高級後端架構師 · 項目 Nexus

<details>
<summary><b>1. 數據模型</b></summary>

| Store | Schema |
|:---|:---|
| **PostgreSQL** | `scenes` — JSONB `content` · `metadata` · `status` · `version` (SemVer) · `audit_log` |
| **Neo4j** | Nodes: `Scene` · `Character` · `Prop` / Relations: `LEADS_TO` · `CONTAINS` · `REQUIRES` / 唯一約束 + 索引 |
| **Milvus** | 768 維場景語義向量 — 相似度檢索 + 衝突檢測 |

</details>

<details>
<summary><b>2. 核心邏輯</b></summary>

- **`SceneStateMachine`** — `DRAFT → REVIEW → LOCKED → COMPLETED` · 非法轉移拋 `StateTransitionError`
- **`RippleEffectAnalyzer`** — 遍歷 `LEADS_TO` · 檢查角色/道具邏輯衝突 · 返回報告
- **CRDT 協作** — Yjs 多人實時編輯 · 字段級鎖 (Field-Level Lock)

</details>

<details>
<summary><b>3. API 規範</b></summary>

| 方法 | 端點 | → | 說明 |
|:---:|:---|:---:|:---|
| `PATCH` | `/scenes/{id}` | `200` / `409` | 部分更新 + 漣漪分析 |
| `GET` | `/scripts/{id}/graph` | `200` | 劇情依賴圖譜 JSON |
| `POST` | `/scenes/{id}/branch` | `201` | 劇情分支 + 新版本 ID |

</details>

<details>
<summary><b>4. CI/CD 與交付</b></summary>

- **Pipeline** — GitHub Actions：lint → type-check → build → deploy
- **交付物** — Alembic 遷移 · Neo4j Cypher · FastAPI 服務 · OpenAPI 文檔
- **規範** — Type Hints · 錯誤處理 · 結構化日誌

</details>

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
