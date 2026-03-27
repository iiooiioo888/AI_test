<div align="center">

# 🎬 AI Video Studio

**企業級 AI 影片特效 & 影片擴展平台**

[![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=flat&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![OpenCV](https://img.shields.io/badge/OpenCV-4.x-5C3EE8?style=flat&logo=opencv&logoColor=white)](https://opencv.org)
[![FFmpeg](https://img.shields.io/badge/FFmpeg-6.x-007808?style=flat&logo=ffmpeg&logoColor=white)](https://ffmpeg.org)
[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat&logo=python&logoColor=white)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

一款基於 AI 的影片後期處理工具，支援 **18 種視覺特效**、**8 種影片擴展模式**，全程保留原始音訊。

[功能亮點](#-功能亮點) ·
[快速開始](#-快速開始) ·
[技術架構](#-技術架構) ·
[API 文件](#-api-文件) ·
[更新日誌](#-更新日誌)

</div>

---

## ✨ 功能亮點

### 🎨 AI 視覺特效（18 種）

<table>
<tr>
<td width="50%">

#### 經典特效
| 圖示 | 特效 | 說明 |
|:---:|------|------|
| ⚡ | 故障藝術 | RGB 位移 + 訊號干擾 |
| 📼 | VHS 復古 | 90 年代錄影帶質感 |
| 🌆 | 賽博朋克 | 霓虹色調 + 掃描線 |
| 🎬 | 黑色電影 | 高對比黑白 + 暗角 |
| ✨ | 夢幻柔光 | 柔焦 + 光暈效果 |
| 💜 | 霓虹描邊 | 邊緣發光 + 深色背景 |

</td>
<td width="50%">

#### 藝術風格
| 圖示 | 特效 | 說明 |
|:---:|------|------|
| 👾 | 像素風 | 復古像素化效果 |
| 🔥 | 熱成像 | 紅外熱力圖效果 |
| ✏️ | 素描風 | 鉛筆手繪效果 |
| 💊 | 黑客帝國 | 綠色矩陣數字雨 |
| 💥 | 漫畫風 | 波普漫畫網點效果 |
| 🌊 | 波浪扭曲 | 正弦波形變動畫 |

</td>
</tr>
<tr>
<td colspan="2">

#### 🆕 v2.0 新增

| 圖示 | 特效 | 實現方式 |
|:---:|------|---------|
| 🎨 | 油畫風 | `cv2.stylization` 筆觸模擬 + 雙邊濾波降級 |
| 🖌️ | 水彩風 | 邊緣保留濾波 + 飽和度增強 |
| 📽️ | 老電影 | 去色 + 暗褐調 + 亮度閃爍 + 膠片噪點 + 垂直劃痕 |
| 🎭 | 雙調色 | 亮度映射到雙色漸變（深藍紫 → 暖金橙） |
| 🌈 | 色散效果 | R/B 通道偏移 + 光暈疊加 |
| 🎪 | 卡通化 | 自適應閾值邊緣 + 色彩量化 |

</td>
</tr>
</table>

### 📐 影片擴展（8 種）

| 圖示 | 模式 | 說明 | 音訊處理 |
|:---:|------|------|---------|
| 🔄 | 無縫循環 | 首尾平滑過渡循環 | 交叉淡入淡出 |
| ↔️ | 乒乓播放 | 正放 + 倒放 | 音訊同步反向 |
| 🐢 | AI 慢動作 | 光流插幀慢放 | `atempo` 同步減速 |
| ⏪ | 倒放 | 完整倒放影片 | `areverse` |
| 📈 | 速度漸變 | 慢 → 快 → 慢節奏 | 各段獨立變速 |
| ❄️ | 定格延伸 | 結尾定格淡出 | 原音 + 漸出 |
| 🔁 | 片段重複 | 影片整體重複播放 | 音訊同步拼接 |
| 🔪 | 時間切片 | 多幀同屏時間凍結 | — |

### 🔊 智慧音訊保留

所有特效與擴展模式均支援 **自動音訊保留**：

```
原始影片 ──→ FFmpeg 解封裝 ──→ 音訊軌道 ──┐
                                          ├──→ FFmpeg 複封裝 ──→ 輸出影片
特效/擴展處理 ──→ OpenCV 逐幀處理 ──→ 視訊軌道 ─┘
```

- 🎯 特效處理：自動提取源音訊，視訊處理完畢後合併（AAC 128k）
- 🎯 擴展模式：音訊隨視訊同步處理（反向、變速、拼接）
- 🎯 降級策略：無音訊源自動降級為純視訊輸出，不中斷流程

---

## 🚀 快速開始

### 環境需求

- Python 3.10+
- FFmpeg 6.x+（系統已安裝）
- 512MB+ 可用記憶體

### 安裝與啟動

```bash
# 克隆專案
git clone https://github.com/iiooiioo888/AI_test.git
cd AI_test

# 建立虛擬環境
python3 -m venv venv
source venv/bin/activate

# 安裝依賴
pip install -r requirements.txt

# 啟動服務
python app.py
```

服務啟動後訪問 👉 **http://localhost:8888**

### 使用流程

```
 上傳影片  →  選擇特效/擴展  →  即時預覽進度  →  下載 / 繼續編輯
   Step 1        Step 2           Step 3          Step 4
```

1. **上傳** — 拖拽或選擇影片檔案（MP4 / AVI / MOV / MKV / WebM / GIF，最大 500MB）
2. **編輯** — 切換「AI 特效」或「影片擴展」頁籤，調整強度後套用
3. **處理** — 即時 WebSocket 推送進度，支援斷線重連
4. **完成** — 預覽結果、下載影片、或一鍵載入繼續編輯

---

## 🏗 技術架構

```
┌─────────────────────────────────────────────────────────┐
│                   瀏覽器 (暗色 UI)                        │
│  ┌──────────┐  ┌──────────┐  ┌───────────────────────┐  │
│  │ 拖拽上傳  │  │ 特效選卡  │  │  WebSocket 即時進度   │  │
│  └────┬─────┘  └────┬─────┘  └───────────▲───────────┘  │
└───────┼─────────────┼────────────────────┼──────────────┘
        │ REST API    │ POST /process      │ ws://
┌───────▼─────────────▼────────────────────┼──────────────┐
│              FastAPI (Uvicorn)            │              │
│  ┌──────────┐  ┌──────────────┐  ┌──────┴──────┐       │
│  │ Upload   │  │ Task Manager │  │  WS Broadcast│       │
│  └────┬─────┘  └──────┬───────┘  └─────────────┘       │
│       │               │                                  │
│  ┌────▼─────┐  ┌──────▼───────┐                         │
│  │  OpenCV  │  │   FFmpeg     │   ← executor (thread)   │
│  │ 逐幀特效  │  │ 編碼/擴展/合併 │                         │
│  └──────────┘  └──────────────┘                         │
└─────────────────────────────────────────────────────────┘
```

### 核心依賴

| 元件 | 用途 |
|------|------|
| **FastAPI** | 非同步 Web 框架，REST + WebSocket |
| **OpenCV** | CPU 逐幀影像處理（18 種特效） |
| **FFmpeg** | 視訊編碼、音訊合併、複雜濾鏡鏈 |
| **NumPy** | 向量化像素運算 |
| **Uvicorn** | ASGI 伺服器 |

---

## 📡 API 文件

| 方法 | 端點 | 說明 |
|------|------|------|
| `GET` | `/` | 主頁面 |
| `GET` | `/api/effects` | 取得特效 & 擴展模式列表 |
| `POST` | `/api/upload` | 上傳影片（multipart） |
| `POST` | `/api/process/effect` | 啟動特效處理 |
| `POST` | `/api/process/extend` | 啟動擴展處理 |
| `GET` | `/api/task/{task_id}` | 查詢任務狀態 |
| `GET` | `/api/download/{task_id}` | 下載處理結果 |
| `POST` | `/api/import-result` | 導入結果作為新編輯源 |
| `GET` | `/api/preview/{file_id}` | 預覽上傳影片 |
| `WS` | `/ws` | 即時進度推送 |

### 範例：套用賽博朋克特效

```bash
# 1. 上傳
curl -F "file=@video.mp4" http://localhost:8888/api/upload
# → {"file_id": "a1b2c3d4", "info": {...}}

# 2. 套用特效
curl -F "file_id=a1b2c3d4" -F "effect=cyberpunk" -F "intensity=0.7" \
     http://localhost:8888/api/process/effect
# → {"task_id": "e5f6g7h8", "effect": "cyberpunk"}

# 3. 查詢進度
curl http://localhost:8888/api/task/e5f6g7h8

# 4. 下載
curl -O http://localhost:8888/api/download/e5f6g7h8
```

---

## 📁 專案結構

```
AI_test/
├── app.py                  # 主應用（FastAPI + 全部處理邏輯）
├── requirements.txt        # Python 依賴
├── whitepaper.md           # 企業級 AI 提示詞優化引擎白皮書
├── templates/
│   └── index.html          # 主頁面模板
└── static/
    ├── css/style.css       # 暗色主題樣式
    └── js/app.js           # 前端邏輯（上傳/選卡/進度/下載）
```

---

## 📋 支援格式

| 類型 | 格式 |
|------|------|
| **輸入** | MP4, AVI, MOV, MKV, WebM, GIF |
| **輸出** | MP4 (H.264 + AAC) |

---

## 📝 更新日誌

### v2.0 — 音訊保留 + 6 種新特效（2026-03-27）

- 🔊 **音訊保留** — 所有特效和擴展模式支援音訊自動提取與合併
- 🎨 **6 種新特效** — 油畫風、水彩風、老電影、雙調色、色散、卡通化
- 📊 **進度追蹤** — 特效處理支援逐幀進度回報（每 ~5%）
- 🛡️ **健壯性** — 改進錯誤處理、資源清理、FFmpeg 超時保護
- 🔧 **工具函數** — 新增 `_has_audio_stream()` 等輔助方法

### v1.0 — 初始版本

- 12 種視覺特效 + 8 種影片擴展模式
- FastAPI + WebSocket 即時進度推送
- 暗色主題 UI + 拖拽上傳 + 繼續編輯

---

<div align="center">

**Built with FastAPI · OpenCV · FFmpeg**

</div>
