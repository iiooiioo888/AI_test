# AI Video Studio

<p align="center">
  <strong>企業級 AI 影片後期處理平台</strong><br>
  <sub>18 種視覺特效 · 8 種影片擴展 · 智慧音訊保留 · 即時進度追蹤</sub>
</p>

<p align="center">
  <a href="https://fastapi.tiangolo.com"><img src="https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white" alt="FastAPI"></a>
  <a href="https://opencv.org"><img src="https://img.shields.io/badge/OpenCV-4.x-5C3EE8?style=for-the-badge&logo=opencv&logoColor=white" alt="OpenCV"></a>
  <a href="https://ffmpeg.org"><img src="https://img.shields.io/badge/FFmpeg-6.x-007808?style=for-the-badge&logo=ffmpeg&logoColor=white" alt="FFmpeg"></a>
  <a href="https://python.org"><img src="https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python"></a>
</p>

<p align="center">
  <a href="#功能特性">功能特性</a> ·
  <a href="#系統架構">系統架構</a> ·
  <a href="#快速開始">快速開始</a> ·
  <a href="#api-文件">API 文件</a> ·
  <a href="#部署指南">部署指南</a> ·
  <a href="#更新日誌">更新日誌</a>
</p>

---

## 概述

AI Video Studio 是一套基於非同步架構的影片後期處理系統，提供從視覺特效到時間軸操作的完整解決方案。系統採用管道式處理架構，透過 OpenCV 進行逐幀像素級運算，以 FFmpeg 完成編碼與音訊合併，實現零品質損失的端到端處理流程。

**設計原則**

- 無狀態伺服器架構，支援水平擴展
- 所有 CPU 密集型操作在獨立執行緒中運行，不阻塞事件迴圈
- 全鏈路音訊保留，確保輸出品質與來源一致
- WebSocket 雙向通訊，提供毫秒級進度回饋

---

## 功能特性

### 視覺特效引擎

系統內建 18 種可組合的視覺特效，覆蓋從故障藝術到傳統繪畫風格的完整光譜。

| 類別 | 特效 | 技術實現 |
|------|------|---------|
| **數位風格** | 故障藝術 · 賽博朋克 · 黑客帝國 | RGB 通道偏移、色彩映射、字元渲染 |
| **復古質感** | VHS 復古 · 黑色電影 · 老電影 | 色彩退化、CLAHE 對比增強、膠片模擬 |
| **繪畫風格** | 油畫風 · 水彩風 · 素描風 · 漫畫風 | 風格遷移濾波、邊緣保留、自適應閾值 |
| **幾何變換** | 像素風 · 波浪扭曲 · 卡通化 | 最近鄰插值、正弦位移場、色彩量化 |
| **色彩處理** | 夢幻柔光 · 霓虹描邊 · 雙調色 · 色散效果 | 高斯混合、Canny 邊緣發光、漸變映射 |
| **熱力視覺** | 熱成像 | 偽彩色映射 (Inferno / Jet) |

每種特效均支援 0.1 – 1.0 的強度參數連續調整。

### 影片擴展引擎

8 種時間軸操作模式，涵蓋循環、變速、定格等常見後期需求。

| 模式 | 演算法 | 音訊處理 |
|------|--------|---------|
| 無縫循環 | XFade 交叉淡化 | 音訊交叉淡化 |
| 乒乓播放 | 分離 + 反向 + 拼接 | areverse 同步反向 |
| AI 慢動作 | Minterpolate 光流插幀 | atempo 線性減速 |
| 倒放 | reverse / areverse | areverse |
| 速度漸變 | 分段 PTS 變換 | 分段 atempo |
| 定格延伸 | Loop 靜幀 + Fade Out | 原音軌道 + 漸出 |
| 片段重複 | Multi-input Concat | 音訊同步拼接 |
| 時間切片 | 抽幀 + Tile 馬賽克 | — |

### 智慧音訊處理

系統在處理全鏈路中保留原始音訊軌道：

```
輸入 ─┬─→ [FFmpeg demux] ─→ 音訊流 ─→ [AAC 128k encode] ─┐
      │                                                     ├→ [FFmpeg mux] → MP4 輸出
      └─→ [FFmpeg decode] ─→ raw BGR ─→ [OpenCV effect] ─→ H.264 encode ─┘
```

對於無音訊的來源檔案（如 GIF），系統自動偵測並降級為純視訊輸出，無需人工干預。

---

## 系統架構

```
┌─────────────────────────────────────────────────────────────────┐
│                         Client Layer                            │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────────────────┐  │
│  │  Drag/Drop   │  │  Effect Grid │  │  WebSocket Progress    │  │
│  │  Upload      │  │  Selector    │  │  (auto-reconnect)      │  │
│  └──────┬──────┘  └──────┬───────┘  └───────────▲────────────┘  │
└─────────┼───────────────┼────────────────────────┼──────────────┘
          │ HTTP POST     │ HTTP POST              │ ws://
┌─────────▼───────────────▼────────────────────────┼──────────────┐
│                    FastAPI (ASGI)                 │              │
│  ┌──────────────┐  ┌────────────────┐  ┌────────┴───────────┐  │
│  │  Upload      │  │  Task          │  │  WebSocket          │  │
│  │  Controller  │  │  Dispatcher    │  │  Broadcast Hub      │  │
│  └──────┬───────┘  └───────┬────────┘  └────────────────────┘  │
│         │                  │                                    │
│         │           ┌──────▼────────┐                           │
│         │           │  Thread Pool  │  (non-blocking)           │
│         │           └──┬─────────┬──┘                           │
│         │              │         │                              │
│  ┌──────▼───────┐  ┌───▼────┐  ┌▼─────────────┐               │
│  │  File I/O    │  │ OpenCV │  │  FFmpeg CLI   │               │
│  │  (uploads/)  │  │ Engine │  │  Pipeline     │               │
│  └──────────────┘  └────────┘  └───────────────┘               │
└─────────────────────────────────────────────────────────────────┘
```

**處理模式**

| 操作類型 | 執行緒模型 | 瓶頸點 | 預期耗時 |
|---------|-----------|--------|---------|
| 視覺特效 | `run_in_executor` + OpenCV 逐幀 | CPU (幀率 × 解析度) | 0.5–3× 即時長度 |
| 影片擴展 | `run_in_executor` + FFmpeg 子行程 | I/O + 編碼 | 取決於模式複雜度 |
| 音訊合併 | FFmpeg stream copy → mux | I/O | < 5s |

---

## 快速開始

### 環境需求

| 依賴 | 最低版本 | 用途 |
|------|---------|------|
| Python | 3.10 | 執行環境 |
| FFmpeg | 6.0 | 編解碼與濾鏡 |
| 磁碟空間 | 1 GB | 暫存檔案（自動清理） |
| 記憶體 | 512 MB | 逐幀處理緩衝 |

### 安裝

```bash
git clone https://github.com/iiooiioo888/AI_test.git
cd AI_test
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
```

### 啟動

```bash
python app.py
# → Uvicorn running on http://0.0.0.0:8888
```

### 使用流程

```
Step 1          Step 2            Step 3           Step 4
┌─────────┐    ┌──────────┐     ┌───────────┐    ┌────────────┐
│ 上傳影片 │ →  │ 選擇特效  │  →  │ 即時進度  │ →  │ 下載結果   │
│ (拖拽)   │    │ 調整強度  │     │ WebSocket │    │ 繼續編輯   │
└─────────┘    └──────────┘     └───────────┘    └────────────┘
```

1. **上傳** — 支援拖拽、檔案選擇、剪貼簿貼上。格式：MP4 / AVI / MOV / MKV / WebM / GIF，上限 500 MB
2. **編輯** — 切換「AI 特效」或「影片擴展」頁籤，設定強度 / 參數
3. **監控** — 即時進度條 + WebSocket 推送，斷線自動重連並查詢任務狀態
4. **輸出** — 線上預覽、下載 MP4、或一鍵載入結果作為新的編輯來源

---

## API 文件

### 端點一覽

| 方法 | 路徑 | 說明 | 回應格式 |
|------|------|------|---------|
| `GET` | `/` | Web 主頁 | HTML |
| `GET` | `/api/effects` | 取得所有特效與擴展模式定義 | JSON |
| `POST` | `/api/upload` | 上傳影片檔案 | `file_id` + `info` |
| `POST` | `/api/process/effect` | 啟動特效處理任務 | `task_id` |
| `POST` | `/api/process/extend` | 啟動擴展處理任務 | `task_id` |
| `GET` | `/api/task/{id}` | 查詢任務狀態與進度 | JSON |
| `GET` | `/api/download/{id}` | 下載處理完成的影片 | MP4 |
| `POST` | `/api/import-result` | 將結果導入為新編輯源 | `file_id` + `info` |
| `GET` | `/api/preview/{id}` | 串流預覽上傳影片 | Video |
| `WS` | `/ws` | 即時進度推送 | JSON |

### 任務狀態流

```
queued → processing → done
                    ↘ error
```

### 範例

```bash
# 上傳影片
curl -s -F "file=@sample.mp4" http://localhost:8888/api/upload | jq .
# {"file_id": "a1b2c3d4", "filename": "sample.mp4", "info": {"duration": 12.5, ...}}

# 套用賽博朋克特效（強度 0.7）
curl -s -F "file_id=a1b2c3d4" -F "effect=cyberpunk" -F "intensity=0.7" \
     http://localhost:8888/api/process/effect | jq .
# {"task_id": "e5f6g7h8", "effect": "cyberpunk"}

# 輪詢任務狀態
curl -s http://localhost:8888/api/task/e5f6g7h8 | jq .
# {"task_id": "e5f6g7h8", "status": "done", "progress": 100, ...}

# 下載結果
curl -O http://localhost:8888/api/download/e5f6g7h8
```

---

## 部署指南

### 開發環境

```bash
python app.py
```

### 生產部署

```bash
# 使用 Uvicorn 直接啟動（多 worker）
uvicorn app:app --host 0.0.0.0 --port 8888 --workers 4

# 或使用 Gunicorn + Uvicorn
gunicorn app:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8888
```

### 環境變數

| 變數 | 預設值 | 說明 |
|------|--------|------|
| `MAX_FILE_SIZE` | `524288000` | 最大上傳檔案大小 (bytes) |
| `FFMPEG_TIMEOUT` | `600` | FFmpeg 操作逾時 (秒) |
| `CLEANUP_AGE` | `3600` | 暫存檔案自動清理閾值 (秒) |

### 磁碟管理

系統在 `uploads/` 和 `output/` 目錄下建立暫存檔案，每次啟動時自動清理超過 `CLEANUP_AGE` 秒的舊檔案。建議定期監控磁碟使用量，或搭配 cron 排程清理：

```bash
# 每日清理超過 6 小時的暫存檔案
0 */6 * * * find /path/to/AI_test/uploads /path/to/AI_test/output -type f -mmin +360 -delete
```

---

## 專案結構

```
AI_test/
├── app.py                      # 主應用（路由 + 特效邏輯 + 擴展邏輯）
├── requirements.txt            # Python 相依套件
├── README.md                   # 本文件
├── whitepaper.md               # 企業級 AI 提示詞優化引擎白皮書
├── uploads/                    # 使用者上傳影片（自動管理）
├── output/                     # 處理輸出影片（自動管理）
├── templates/
│   └── index.html              # SPA 入口
└── static/
    ├── css/
    │   └── style.css           # 暗色主題 UI
    └── js/
        └── app.js              # 前端邏輯
```

---

## 技術棧

| 層級 | 技術 | 角色 |
|------|------|------|
| Web 框架 | FastAPI 0.135 + Uvicorn | 非同步 REST / WebSocket |
| 影像處理 | OpenCV 4.x + NumPy | 逐幀像素運算 |
| 影音編解碼 | FFmpeg 6.x | H.264 編碼、AAC 音訊、濾鏡鏈 |
| 前端 | Vanilla HTML/CSS/JS | SPA 介面、粒子動畫背景 |
| 即時通訊 | WebSocket | 雙向進度推送 |

---

## 更新日誌

### v2.0 — 2026-03-27

**新功能**
- 全鏈路音訊保留機制：特效與擴展模式自動提取、處理、合併音訊軌道
- 6 種新視覺特效：油畫風、水彩風、老電影、雙調色、色散效果、卡通化
- `_has_audio_stream()` 音訊偵測工具函數

**改進**
- 特效處理支援逐幀進度回報（~5% 粒度）
- FFmpeg 操作逾時保護（預設 600 秒）
- 資源清理機制強化

### v1.0 — 初始版本

- 12 種視覺特效 + 8 種影片擴展模式
- FastAPI + WebSocket 非同步架構
- 暗色主題 UI，支援拖拽上傳與結果再編輯

---

## 授權

本專案以 MIT 授權條款釋出。詳見 [LICENSE](LICENSE)。
