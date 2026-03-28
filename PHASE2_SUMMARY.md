# Phase 2: 敘事與劇本引擎 - 完成總結

**完成時間:** 2026-03-29  
**提交:** 5836bc6  
**代碼行數:** +2,500+  
**測試覆蓋:** 35 個單元測試用例

---

## 📋 交付物清單

### 核心服務 (6 個文件)

| 文件 | 行數 | 功能 |
|------|------|------|
| `app/services/narrative/scene_state_machine.py` | 250+ | 場景区生命周期狀態機 |
| `app/services/narrative/knowledge_graph.py` | 400+ | Neo4j 知識圖譜服務 |
| `app/services/narrative/crdt_editor.py` | 350+ | CRDT 協作編輯 |
| `app/services/narrative/narrative_engine.py` | 300+ | 敘事引擎統一接口 |
| `app/services/auth/rbac.py` | 350+ | RBAC 權限控制 |
| `app/services/narrative/__init__.py` | 10 | 模塊導出 |

### 測試套件 (3 個文件)

| 文件 | 測試用例 | 覆蓋範圍 |
|------|---------|---------|
| `tests/unit/test_scene_state_machine.py` | 15 | 狀態機邏輯 |
| `tests/unit/test_crdt_editor.py` | 20 | CRDT 算法 |
| `tests/conftest.py` | - | Pytest 配置 |

---

## 🎯 核心功能實現

### 1. 場景区生命周期狀態機

**7 種狀態:**
```
DRAFT → REVIEW → LOCKED → QUEUED → GENERATING → COMPLETED
                                     ↓
                                   FAILED → QUEUED/DRAFT
```

**關鍵特性:**
- ✅ 嚴格的狀態轉換規則
- ✅ 轉換合法性驗證
- ✅ 審計日誌記錄
- ✅ 特權轉換檢查 (Director 角色)
- ✅ 自動狀態機 (生成任務)

**測試覆蓋:**
- 合法轉換驗證
- 非法轉換阻止
- 完整工作流程
- 失敗重試流程
- 邊界條件

---

### 2. Neo4j 知識圖譜

**核心功能:**
- ✅ 場景/角色/道具節點 CRUD
- ✅ 場景序列關係 (NEXT/PREVIOUS)
- ✅ 角色關係網絡 (RELATED_TO)
- ✅ 漣漪效應分析 (遞歸查詢)
- ✅ 連貫性檢查 (角色/地點一致性)

**Cypher 查詢模板:**
```cypher
// 漣漪效應分析
MATCH path = (s:Scene {id: $scene_id})-[:NEXT*1..10]->(affected:Scene)
WHERE affected.status <> 'completed'
RETURN affected, length(path) as distance

// 角色關係網絡
MATCH (c:Character {projectId: $project_id})-[r:RELATED_TO]-(other:Character)
RETURN c, r, other
```

---

### 3. CRDT 協作編輯

**數據結構:**
- **VectorClock**: 分布式事件順序追蹤
- **LWWRegister**: Last-Writer-Wins 單值字段
- **ORSet**: Observed-Remove 集合

**關鍵特性:**
- ✅ 冪等性 (同一操作不重複應用)
- ✅ 並發合併 (自動解決衝突)
- ✅ 操作歷史記錄
- ✅ 實時廣播 (WebSocket)

**測試場景:**
- 向量時鐘合併
- LWW 時間戳衝突解決
- ORSet 添加/刪除/合併
- SceneCRDT 狀態同步
- 協作服務集成

---

### 4. RBAC 權限控制

**5 種角色:**
| 角色 | 權限 |
|------|------|
| Viewer | 只讀 |
| Editor | 創建/編輯/刪除 |
| Director | 審核/鎖定/取消生成 |
| Admin | 項目管理/用戶管理 |
| Super Admin | 系統設置 |

**權限層級:**
- ✅ 角色權限 (基於角色定義)
- ✅ 資源級權限 (項目/場景級別)
- ✅ 字段級權限 (細粒度控制)
- ✅ 權限繼承 (Director 繼承 Editor)

**FastAPI 集成:**
```python
@router.post("/scenes", dependencies=[
    Depends(require_permission(Permission.SCENE_CREATE))
])
async def create_scene(...):
    ...
```

---

### 5. 敘事引擎統一接口

**整合服務:**
- SceneStateMachine (狀態機)
- KnowledgeGraphService (知識圖譜)
- CollaborativeEditingService (CRDT)
- RBACService (權限控制)

**核心 API:**
```python
# 創建場景
await engine.create_scene(scene_data, user_context, project_id)

# 更新場景 (CRDT)
await engine.update_scene(scene_id, updates, user_context)

# 狀態轉換
await engine.transition_scene(scene_id, SceneStatus.REVIEW, user_context)

# 漣漪效應分析
analysis = await engine.analyze_impact(scene_id)

# 連貫性檢查
continuity = await engine.check_scene_continuity(scene_id)

# 加入協作
await engine.join_collaboration(scene_id, user_id, websocket)
```

---

## 🧪 測試覆蓋率

### 場景狀態機測試 (15 個用例)

| 測試類別 | 用例數 | 說明 |
|---------|-------|------|
| 基本轉換 | 5 | DRAFT→REVIEW 等單步轉換 |
| 完整流程 | 2 | 完整工作流程、失敗重試 |
| 狀態檢查 | 4 | is_editable, is_generating 等 |
| 歷史記錄 | 2 | 轉換歷史查詢 |
| 配置測試 | 2 | 默認配置、自定義配置 |

### CRDT 編輯測試 (20 個用例)

| 測試類別 | 用例數 | 說明 |
|---------|-------|------|
| VectorClock | 4 | increment, merge, happens-before |
| LWWRegister | 4 | set/get, 時間戳衝突，合併 |
| ORSet | 5 | add/remove, 合併，墓碑 |
| SceneCRDT | 5 | 操作創建，應用，冪等性 |
| 協作服務 | 2 | join/leave, 遠程操作 |

---

## 📊 設計決策與理由

### 為什麼選擇狀態機模式？

**理由:**
1. **明確的業務流程**: 視頻生成有嚴格的順序要求
2. **狀態不可跳跃**: 防止非法狀態轉換
3. **易於審計**: 所有轉換都有記錄
4. **自動化支持**: 系統可自動觸發某些轉換

**潛在風險:**
- 狀態不一致 → 使用事務保證
- 並發轉換 → 需要分布式鎖
- 審計遺失 → 預寫日誌

### 為什麼選擇 CRDT？

**理由:**
1. **無衝突合併**: 數學保證最終一致性
2. **去中心化**: 不需要中央協調服務
3. **低延遲**: 本地操作立即生效
4. **離線支持**: 離線編輯後可合併

**取捨:**
- 複雜度增加 → 需要理解 CRDT 原理
- 存儲開銷 → 需要保存操作歷史

### 為什麼使用 Neo4j？

**理由:**
1. **關係查詢優勢**: 漣漪效應需要遞歸查詢
2. **圖可視化**: 角色關係網絡天然適合圖形表示
3. **靈活的 Schema**: 容易擴展新的節點/關係類型

**替代方案:**
- PostgreSQL (pggraph): SQL 團隊更熟悉，但圖查詢性能較弱
- ArangoDB: 多模型，但生態系統較小

---

## 🔗 依賴關係

```
Phase 2 (敘事引擎)
├── Phase 1 (數據模型) ✅
│   ├── SceneObject Schema
│   ├── PostgreSQL Schema
│   └── Neo4j/Milvus Schema
│
├── Phase 3 (提示詞優化) ⏳
│   └── 依賴場景的 positive_prompt 字段
│
└── Phase 4 (視頻生成) ⏳
    └── 依賴場景狀態轉換到 QUEUED
```

---

## 🚀 下一步：Phase 3

### 提示詞優化模組

1. **輸入解析與優化生成**
   - LLM 提示詞重寫
   - 結構化轉換 (自然語言 → 標準格式)
   - 負向提示詞自動生成

2. **RAG 檢索系統**
   - Milvus 向量檢索
   - 歷史成功案例檢索
   - 智能推薦

3. **提示詞版本控制**
   - Git-like 版本管理
   - 分支與合併
   - Diff 比對

4. **質量評估指標**
   - CLIP Score 預測
   - 成本估算
   - 可執行性驗證

---

## 📝 使用示例

### 創建場景並加入協作

```python
from app.services.narrative import get_narrative_engine
from app.services.auth import UserContext, Role

# 創建引擎
engine = await create_narrative_engine(db_session)

# 用戶上下文
user = UserContext(
    user_id="user-001",
    email="user@example.com",
    roles=[Role.DIRECTOR],
)

# 創建場景
success, error, scene = await engine.create_scene(
    scene_data={
        "title": "英雄登場",
        "description": "主角在黎明時分登上山巔",
        "narrative_text": "晨光熹微，英雄獨自登上山巔...",
    },
    user_context=user,
    project_id="proj-001",
)

# 加入協作編輯
state = await engine.join_collaboration(
    scene_id=scene["id"],
    user_id=user.user_id,
    websocket=ws,
)

# 更新場景
await engine.update_scene(
    scene_id=scene["id"],
    updates={"title": "新標題"},
    user_context=user,
)

# 狀態轉換 (提交審核)
await engine.transition_scene(
    scene_id=scene["id"],
    target_status=SceneStatus.REVIEW,
    user_context=user,
    reason="提交審核",
)

# 漣漪效應分析
analysis = await engine.analyze_impact(scene["id"])
print(f"Affected scenes: {analysis['total_affected']}")

# 清理資源
await engine.cleanup()
```

---

## ✅ Phase 2 完成確認

- [x] 場景狀態機實現
- [x] Neo4j 知識圖譜集成
- [x] CRDT 協作編輯
- [x] RBAC 權限控制
- [x] 敘事引擎統一接口
- [x] 單元測試套件
- [x] 文檔與示例
- [x] GitHub 推送

**Phase 2 狀態:** ✅ 完成  
**下一步:** Phase 3 - 提示詞優化模組
