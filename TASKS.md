# AVP — 接下來任務清單

> 生成時間：2026-03-27 17:58 (GMT+8)
> 當前進度：Phase 1-3 完成，核心架構就緒，待聯調與測試

---

## Phase 4：前後端 API 聯調

> 目標：把前端的假資料(Demo)換成真實 API 調用

### 4.1 敘事管理 — 真實數據接入

| # | 任務 | 細節 | 優先級 |
|:--:|:---|:---|:---:|
| 4.1.1 | `loadScenes()` → `GET /narrative/scenes` | 替換 `loadDemoScenes()`，頁面載入時從 API 拉取場景列表 | P0 |
| 4.1.2 | `selectScene()` → `GET /narrative/scenes/{id}` | 點擊場景時從 API 獲取完整詳情（含對白/視覺/審計日誌） | P0 |
| 4.1.3 | `_saveScene()` → `PATCH /narrative/scenes/{id}` | 保存按鈕改為 PATCH 請求，處理 409 衝突響應並顯示漣漪報告 | P0 |
| 4.1.4 | `_createNewScene()` → `POST /narrative/scenes` | 新建場景調用 API，拿到真實 UUID | P0 |
| 4.1.5 | 狀態轉換 → `POST /narrative/scenes/{id}/transition` | 狀態按鈕改為 API 調用，處理 422 非法轉換錯誤 | P0 |
| 4.1.6 | `analyzeRipple()` → `GET /narrative/scenes/{id}/impact-analysis` | 漣漪分析改為真實 API，渲染完整衝突報告 | P1 |
| 4.1.7 | 刪除場景 → `DELETE /narrative/scenes/{id}` | 加刪除確認彈窗 + API 調用 | P2 |

### 4.2 劇情圖譜 — 真實渲染

| # | 任務 | 細節 | 優先級 |
|:--:|:---|:---|:---:|
| 4.2.1 | `renderGraph()` → `GET /narrative/scripts/{id}/graph` | 從 API 獲取 nodes + edges，替換硬編碼數據 | P0 |
| 4.2.2 | 節點詳情面板 → `GET /narrative/scenes/{id}/graph` | 點擊節點時查詢上下游依賴 + 角色共現 | P1 |
| 4.2.3 | 力導向動畫 | 節點拖拽 + 物理模擬（可用 D3.js 或自寫） | P2 |
| 4.2.4 | 佈局切換 | 實現 tree / radial 佈局算法 | P3 |

### 4.3 視頻處理 — 錯誤處理加強

| # | 任務 | 細節 | 優先級 |
|:--:|:---|:---|:---:|
| 4.3.1 | 上傳失敗重試 | XHR timeout + retry 邏輯 | P1 |
| 4.3.2 | WebSocket 斷線恢復 | 重連後自動查詢進行中任務狀態 | P1 |
| 4.3.3 | 佇列顯示 | 同時提交多個任務時顯示佇列位置 | P2 |

---

## Phase 5：單元測試 (>90% 覆蓋率)

> 目標：滿足 spec 要求的 90% 測試覆蓋

### 5.1 狀態機測試

| # | 測試場景 | 說明 |
|:--:|:---|:---|
| 5.1.1 | 合法轉移 | 驗證 DRAFT→REVIEW→LOCKED→COMPLETED 全路徑 |
| 5.1.2 | 非法轉移 | DRAFT→COMPLETED 應拋 StateTransitionError |
| 5.1.3 | Guard 攔截 | 註冊 Guard 後，條件不滿足時應拒絕轉移 |
| 5.1.4 | 批量驗證 | `validate_batch()` 對混合合法/非法轉移的正確性 |
| 5.1.5 | 最短路徑 | `shortest_path()` 跨多步轉移的正確性 |
| 5.1.6 | `can_reach()` | 不可達狀態對的正確判斷 |
| 5.1.7 | Pre/Post Hook | 轉移前後 hook 被正確調用 |
| 5.1.8 | 審計日誌 | 每次轉移寫入正確的 AuditEntry |

### 5.2 漣漪分析器測試

| # | 測試場景 | 說明 |
|:--:|:---|:---|
| 5.2.1 | 角色死亡衝突 | 標記死亡的角色在後續場景出現 → HIGH 衝突 |
| 5.2.2 | 道具銷毀衝突 | 銷毀的道具在後續場景使用 → MEDIUM 衝突 |
| 5.2.3 | 時間線跳躍 | 非閃回場景時間倒退 → LOW 衝突 |
| 5.2.4 | 情緒弧線斷裂 | joy→sorrow 無過渡 → LOW 衝突 |
| 5.2.5 | 無衝突場景 | 乾淨修改 → 返回 safe |
| 5.2.6 | 深度限制 | 超過 max_depth 的 BFS 正確停止 |
| 5.2.7 | `quick_check()` | 只檢查相關字段變更的輕量分析 |

### 5.3 知識圖譜測試

| # | 測試場景 | 說明 |
|:--:|:---|:---|
| 5.3.1 | 節點 CRUD | upsert_scene / upsert_character / upsert_prop |
| 5.3.2 | 邊建立 | LEADS_TO / CONTAINS / REQUIRES 邊正確建立 |
| 5.3.3 | 重複邊防護 | 同一邊不會被重複建立 |
| 5.3.4 | 傳遞依賴 | `get_transitive_dependencies()` 多層鏈路 |
| 5.3.5 | 孤立場景檢測 | `find_orphan_scenes()` 正確識別 |
| 5.3.6 | 循環依賴 | `_has_circular_dependency()` DFS 檢測 |
| 5.3.7 | 角色共現 | `get_character_co_appearances()` 跨場景統計 |
| 5.3.8 | 連通分量 | `find_isolated_subgraphs()` 多組件檢測 |

### 5.4 敘事引擎整合測試

| # | 測試場景 | 說明 |
|:--:|:---|:---|
| 5.4.1 | 場景 CRUD 全流程 | 創建→查詢→更新→刪除 |
| 5.4.2 | RBAC 權限 | WRITER 可編輯 narrative.*，VIEWER 不可 |
| 5.4.3 | 分支創建 | `create_branch()` 複製場景 + 獨立版本線 |
| 5.4.4 | 全局一致性 | `check_global_consistency()` 多場景掃描 |
| 5.4.5 | 小說改編 | `adapt_from_text()` 段落解析 + 對白提取 |

### 5.5 API 端點測試

| # | 測試場景 | 說明 |
|:--:|:---|:---|
| 5.5.1 | `PATCH /scenes/{id}` 200 | 成功更新 + 無衝突 |
| 5.5.2 | `PATCH /scenes/{id}` 409 | 更新觸發漣漪衝突 |
| 5.5.3 | `GET /scripts/{id}/graph` | 返回完整 nodes + edges |
| 5.5.4 | `POST /scenes/{id}/branch` 201 | 成功創建分支 |
| 5.5.5 | 狀態轉移 200 / 422 | 合法與非法轉移的正確響應 |
| 5.5.6 | 驗證錯誤 422 | 缺少必填欄位的請求 |

---

## Phase 6：CRDT 實時協作

> 目標：實現多人同時編輯同一劇本

| # | 任務 | 說明 | 優先級 |
|:--:|:---|:---|:---:|
| 6.1 | Yjs WebSocket Provider | 後端 WS 端點接收 CRDT 更新 | P1 |
| 6.2 | 前端 Yjs 綁定 | 編輯器欄位 ↔ Yjs document 雙向同步 | P1 |
| 6.3 | 字段級鎖 UI | 他人編輯中的欄位顯示鎖定狀態 + 使用者名稱 | P1 |
| 6.4 | 衝突指示器 | CRDT merge 後高亮衝突欄位 | P2 |
| 6.5 | 在線使用者列表 | Header 顯示當前協作者 | P2 |

---

## Phase 7：生產就緒

| # | 任務 | 說明 | 優先級 |
|:--:|:---|:---|:---:|
| 7.1 | Alembic 自動遷移 | `docker-compose up` 時自動執行 migration | P1 |
| 7.2 | Neo4j 初始化掛載 | Docker entrypoint 自動跑 `neo4j_init.cypher` | P1 |
| 7.3 | Milvus Collection 初始化 | 啟動時自動創建 collection + index | P1 |
| 7.4 | 健康檢查完善 | `/health` 檢查 PG / Neo4j / Milvus / Redis 連接 | P1 |
| 7.5 | 環境變數文檔 | `.env.example` 補全所有配置項 + 說明 | P2 |
| 7.6 | CI Pipeline | GitHub Actions: lint → mypy → pytest → build | P2 |
| 7.7 | 結構化日誌統一 | 所有模塊使用 structlog，統一欄位格式 | P2 |
| 7.8 | Prometheus 指標 | 敘事引擎操作計數 + 漣漪分析耗時 + API 延遲 | P3 |

---

## 建議執行順序

```
優先做 (本週)           接下來 (下週)          之後
─────────────────    ─────────────────    ─────────────────
4.1 前端 API 聯調     5.1-5.3 核心測試      6.1 CRDT WebSocket
4.2 圖譜真實渲染      5.4-5.5 整合+API測試   6.2-6.5 協作 UI
5.1 狀態機測試        7.1-7.3 Docker 初始化  7.6 CI Pipeline
                      7.4 健康檢查           7.8 Prometheus
```

**預估工時：** Phase 4 (3天) + Phase 5 (4天) + Phase 6 (3天) + Phase 7 (2天) ≈ **12 工作日**
