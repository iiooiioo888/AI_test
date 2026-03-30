# 🎬 AVP Platform - 影片編輯功能完整詳解

**更新日期:** 2026-03-30 14:45  
**版本:** v2.1  
**GitHub:** https://github.com/iiooiioo888/AI_test

---

## 📋 目錄

1. [視頻剪輯](#1-視頻剪輯)
   - [創建片段](#創建片段)
   - [修剪片段](#修剪片段)
   - [分割片段](#分割片段)
   - [合併片段](#合併片段)
2. [濾鏡系統](#2-濾鏡系統)
   - [基礎濾鏡](#基礎濾鏡)
   - [特效濾鏡](#特效濾鏡)
   - [風格濾鏡](#風格濾鏡)
   - [濾鏡參數詳解](#濾鏡參數詳解)
3. [轉場效果](#3-轉場效果)
   - [轉場類型詳解](#轉場類型詳解)
   - [轉場參數](#轉場參數)
   - [使用建議](#使用建議)
4. [字幕系統](#4-字幕系統)
   - [字幕樣式](#字幕樣式)
   - [參數詳解](#參數詳解)
   - [動畫效果](#動畫效果)
5. [音頻編輯](#5-音頻編輯)
   - [音頻軌道](#音頻軌道)
   - [效果器詳解](#效果器詳解)
6. [專業調色](#6-專業調色)
   - [調色參數](#調色參數)
   - [預設詳解](#預設詳解)
7. [速度控制](#7-速度控制)
8. [畫幅調整](#8-畫幅調整)
9. [完整工作流程](#9-完整工作流程)
10. [最佳實踐](#10-最佳實踐)

---

## 1. 視頻剪輯

### 創建片段

#### API 參考

```python
def create_clip(
    self,
    scene_id: str,        # 場景 ID
    start_time: float,    # 開始時間 (秒)
    end_time: float,      # 結束時間 (秒)
    order: int = 0,       # 片段順序
) -> VideoClip
```

#### 參數詳解

| 參數 | 類型 | 必填 | 說明 | 示例 |
|------|------|------|------|------|
| **scene_id** | str | ✅ | 場景唯一標識 | `"scene-001"` |
| **start_time** | float | ✅ | 片段開始時間 | `0.0` (從頭開始) |
| **end_time** | float | ✅ | 片段結束時間 | `5.0` (5 秒處) |
| **order** | int | ❌ | 片段在時間線上的順序 | `0` (第一個) |

#### 返回值

```python
VideoClip(
    id="clip-001",              # 片段 ID
    scene_id="scene-001",       # 所屬場景
    start_time=0.0,             # 開始時間
    end_time=5.0,               # 結束時間
    duration=5.0,               # 時長 (自動計算)
    order=0,                    # 順序
    filters=[],                 # 已應用濾鏡
    transitions=[],             # 已應用轉場
)
```

#### 使用示例

```python
from app.services.video_editor import get_video_editor_service

editor = get_video_editor_service()

# 示例 1: 創建完整場景片段
clip = editor.create_clip(
    scene_id="scene-001",
    start_time=0.0,
    end_time=10.0,
    order=0,
)
print(f"創建片段：{clip.id}, 時長：{clip.duration}秒")

# 示例 2: 創建場景中間片段
clip = editor.create_clip(
    scene_id="scene-002",
    start_time=5.5,      # 從 5.5 秒開始
    end_time=12.3,       # 到 12.3 秒結束
    order=1,
)
print(f"時長：{clip.duration}秒")  # 輸出：6.8 秒

# 示例 3: 創建多片段 (連續場景)
clips = []
for i in range(5):
    clip = editor.create_clip(
        scene_id="scene-003",
        start_time=i * 3.0,
        end_time=(i + 1) * 3.0,
        order=i,
    )
    clips.append(clip)
    print(f"片段 {i+1}: {clip.duration}秒")
```

#### 錯誤處理

```python
try:
    clip = editor.create_clip(
        scene_id="invalid-scene",
        start_time=10.0,    # 開始時間大於結束時間
        end_time=5.0,
    )
except ValueError as e:
    print(f"錯誤：{e}")  # 錯誤：end_time 必須大於 start_time
```

---

### 修剪片段

#### API 參考

```python
def trim_clip(
    self,
    clip_id: str,         # 片段 ID
    new_start: float,     # 新開始時間
    new_end: float,       # 新結束時間
) -> VideoClip
```

#### 參數詳解

| 參數 | 類型 | 必填 | 說明 | 限制 |
|------|------|------|------|------|
| **clip_id** | str | ✅ | 要修剪的片段 ID | 必須存在 |
| **new_start** | float | ✅ | 新的開始時間 | ≥ 0 |
| **new_end** | float | ✅ | 新的結束時間 | > new_start |

#### 使用示例

```python
# 示例 1: 修剪開頭
clip = editor.trim_clip(
    clip_id="clip-001",
    new_start=2.0,       # 從 2 秒開始
    new_end=10.0,        # 到 10 秒結束
)
print(f"新時長：{clip.duration}秒")  # 8 秒

# 示例 2: 修剪結尾
clip = editor.trim_clip(
    clip_id="clip-001",
    new_start=0.0,
    new_end=7.5,         # 提前到 7.5 秒
)
print(f"新時長：{clip.duration}秒")  # 7.5 秒

# 示例 3: 兩端修剪
clip = editor.trim_clip(
    clip_id="clip-001",
    new_start=1.5,       # 去掉頭 1.5 秒
    new_end=8.5,         # 去掉尾 1.5 秒
)
print(f"新時長：{clip.duration}秒")  # 7 秒
```

#### 精確到幀

```python
# 假設 24fps
fps = 24

# 修剪 3 幀
frame_duration = 1 / fps
clip = editor.trim_clip(
    clip_id="clip-001",
    new_start=3 * frame_duration,    # 3 幀
    new_end=10.0,
)

# 修剪 10 幀
clip = editor.trim_clip(
    clip_id="clip-001",
    new_start=0.0,
    new_end=10.0 - (10 * frame_duration),  # 減少 10 幀
)
```

---

### 分割片段

#### API 參考

```python
def split_clip(
    self,
    clip_id: str,         # 片段 ID
    split_time: float,    # 分割點 (秒)
) -> Tuple[VideoClip, VideoClip]
```

#### 返回值

```python
(
    VideoClip(id="clip-001a", duration=2.5, ...),   # 前半部分
    VideoClip(id="clip-001b", duration=7.5, ...),   # 後半部分
)
```

#### 使用示例

```python
# 示例 1: 從中間分割
original = editor.create_clip("scene-001", 0.0, 10.0)
clip1, clip2 = editor.split_clip(
    clip_id=original.id,
    split_time=5.0,      # 從 5 秒處分割
)

print(f"片段 1: {clip1.duration}秒")  # 5 秒
print(f"片段 2: {clip2.duration}秒")  # 5 秒

# 示例 2: 三分割 (分割兩次)
original = editor.create_clip("scene-001", 0.0, 9.0)
clip1, temp = editor.split_clip(original.id, 3.0)
clip2, clip3 = editor.split_clip(temp.id, 3.0)

print(f"片段 1: {clip1.duration}秒")  # 3 秒
print(f"片段 2: {clip2.duration}秒")  # 3 秒
print(f"片段 3: {clip3.duration}秒")  # 3 秒

# 示例 3: 分割後應用不同濾鏡
clip1, clip2 = editor.split_clip(clip_id, 5.0)

# 前半段溫暖色調
editor.apply_filter(clip1.id, FilterType.WARM, intensity=0.6)

# 後半段冷色調
editor.apply_filter(clip2.id, FilterType.COOL, intensity=0.6)
```

---

### 合併片段

#### API 參考

```python
def merge_clips(
    self,
    clip_ids: List[str],  # 片段 ID 列表
) -> VideoClip
```

#### 使用示例

```python
# 示例 1: 合併兩個片段
clip1 = editor.create_clip("scene-001", 0.0, 5.0)
clip2 = editor.create_clip("scene-002", 0.0, 5.0)

merged = editor.merge_clips(
    clip_ids=[clip1.id, clip2.id]
)

print(f"合併後時長：{merged.duration}秒")  # 10 秒

# 示例 2: 合併多個片段
clips = [
    editor.create_clip("scene-001", 0.0, 3.0, order=0),
    editor.create_clip("scene-002", 0.0, 4.0, order=1),
    editor.create_clip("scene-003", 0.0, 5.0, order=2),
]

merged = editor.merge_clips(
    clip_ids=[c.id for c in clips]
)

print(f"合併後時長：{merged.duration}秒")  # 12 秒

# 示例 3: 合併並保留濾鏡
clip1 = editor.create_clip("scene-001", 0.0, 5.0)
editor.apply_filter(clip1.id, FilterType.CINEMATIC, intensity=0.8)

clip2 = editor.create_clip("scene-002", 0.0, 5.0)
editor.apply_filter(clip2.id, FilterType.VINTAGE, intensity=0.7)

merged = editor.merge_clips([clip1.id, clip2.id])
# 合併後的片段會保留兩個濾鏡
```

---

## 2. 濾鏡系統

### 基礎濾鏡

#### 亮度 (Brightness)

```python
editor.apply_filter(
    clip_id="clip-001",
    filter_type=FilterType.BRIGHTNESS,
    intensity=1.0,
    # 參數
    value=0.3,           # -1.0 (暗) 到 1.0 (亮)
)
```

**參數詳解:**

| 值 | 效果 | 適用場景 |
|----|------|---------|
| `-1.0` | 最暗 | 恐怖/懸疑 |
| `-0.5` | 較暗 | 夜晚/室內 |
| `0.0` | 原始 | - |
| `+0.5` | 較亮 | 日間/回憶 |
| `+1.0` | 最亮 | 夢幻/過曝 |

**使用示例:**

```python
# 提亮夜景
editor.apply_filter(clip_id, FilterType.BRIGHTNESS, value=0.4)

# 壓暗營造氛圍
editor.apply_filter(clip_id, FilterType.BRIGHTNESS, value=-0.3)

# 夢幻過曝效果
editor.apply_filter(clip_id, FilterType.BRIGHTNESS, value=0.8)
```

#### 對比度 (Contrast)

```python
editor.apply_filter(
    clip_id="clip-001",
    filter_type=FilterType.CONTRAST,
    value=0.5,           # -1.0 (灰) 到 1.0 (強烈)
)
```

**參數詳解:**

| 值 | 效果 | 適用場景 |
|----|------|---------|
| `-1.0` | 完全灰色 | 特殊效果 |
| `-0.5` | 低對比 | 夢幻/回憶 |
| `0.0` | 原始 | - |
| `+0.5` | 中等對比 | 一般場景 |
| `+1.0` | 高對比 | 戲劇/動作 |

#### 飽和度 (Saturation)

```python
editor.apply_filter(
    clip_id="clip-001",
    filter_type=FilterType.SATURATION,
    value=-0.5,          # -1.0 (黑白) 到 1.0 (過飽和)
)
```

**參數詳解:**

| 值 | 效果 | 適用場景 |
|----|------|---------|
| `-1.0` | 黑白 | 復古/藝術 |
| `-0.5` | 低飽和 | 憂鬱/冷淡 |
| `0.0` | 原始 | - |
| `+0.5` | 鮮艷 | 兒童/歡樂 |
| `+1.0` | 過飽和 | 超現實 |

---

### 特效濾鏡

#### 復古風 (Vintage)

```python
editor.apply_filter(
    clip_id="clip-001",
    filter_type=FilterType.VINTAGE,
    intensity=0.7,
    # 詳細參數
    sepia=0.4,           # 褐色調強度
    fade=0.3,            # 褪色效果
    vignette=0.4,        # 暗角
    grain=0.3,           # 顆粒感
)
```

**參數詳解:**

| 參數 | 範圍 | 說明 | 默認 |
|------|------|------|------|
| **sepia** | 0.0-1.0 | 褐色調強度 | 0.4 |
| **fade** | 0.0-1.0 | 褪色效果 | 0.3 |
| **vignette** | 0.0-1.0 | 暗角效果 | 0.4 |
| **grain** | 0.0-1.0 | 膠片顆粒 | 0.3 |

**使用場景:**
- 回憶片段
- 歷史題材
- 藝術短片
- MV 製作

#### 賽博朋克 (Cyberpunk)

```python
editor.apply_filter(
    clip_id="clip-001",
    filter_type=FilterType.CYBERPUNK,
    intensity=1.0,
    # 詳細參數
    neon_boost=1.5,      # 霓虹增強
    cyan_shift=0.3,      # 青色偏移
    magenta_shift=0.3,   # 洋紅偏移
    contrast=1.3,        # 對比度
)
```

**參數詳解:**

| 參數 | 範圍 | 說明 | 默認 |
|------|------|------|------|
| **neon_boost** | 0.0-2.0 | 霓虹燈增強 | 1.5 |
| **cyan_shift** | -1.0-1.0 | 青色偏移 | 0.3 |
| **magenta_shift** | -1.0-1.0 | 洋紅偏移 | 0.3 |
| **contrast** | 0.0-2.0 | 對比度 | 1.3 |

**使用場景:**
- 科幻題材
- 夜景街道
- 未來世界
- 遊戲 MV

---

### 風格濾鏡

#### 電影感 (Cinematic)

```python
editor.apply_filter(
    clip_id="clip-001",
    filter_type=FilterType.CINEMATIC,
    intensity=0.8,
    # 詳細參數
    contrast=1.2,          # 對比度 +20%
    saturation=0.9,        # 飽和度 -10%
    vignette=0.3,          # 暗角
    film_grain=0.2,        # 膠片顆粒
    color_temperature=0.1, # 色溫微調
)
```

**完整配置示例:**

```python
# 溫暖電影感
editor.apply_filter(
    clip_id="clip-001",
    filter_type=FilterType.CINEMATIC,
    intensity=0.8,
    contrast=1.15,
    saturation=0.85,
    vignette=0.25,
    film_grain=0.15,
    color_temperature=0.2,  # 偏暖
)

# 冷峻電影感
editor.apply_filter(
    clip_id="clip-002",
    filter_type=FilterType.CINEMATIC,
    intensity=0.8,
    contrast=1.25,
    saturation=0.8,
    vignette=0.35,
    film_grain=0.25,
    color_temperature=-0.15,  # 偏冷
)
```

---

## 3. 轉場效果

### 轉場類型詳解

#### 淡入淡出 (Fade)

```python
editor.add_transition(
    clip_id="clip-001",
    transition_type=TransitionType.FADE,
    duration=1.0,
    position="end",      # "start" 或 "end"
    # 詳細參數
    easing="ease_in_out",# 緩動函數
    fade_color="#000000",# 淡出顏色
)
```

**參數詳解:**

| 參數 | 選項 | 說明 | 默認 |
|------|------|------|------|
| **duration** | float | 轉場時長 (秒) | 1.0 |
| **position** | start/end | 轉場位置 | end |
| **easing** | 見下表 | 緩動函數 | ease_in_out |
| **fade_color** | hex | 淡出顏色 | #000000 |

**緩動函數選項:**

| 選項 | 說明 | 適用場景 |
|------|------|---------|
| `linear` | 線性 | 機械感 |
| `ease_in` | 慢入快出 | 開始 |
| `ease_out` | 快入慢出 | 結束 |
| `ease_in_out` | 慢入慢出 | 通用 |

**使用建議:**
- 情感場景：1.5-2.0 秒
- 動作場景：0.3-0.5 秒
- 對話場景：0.5-1.0 秒

#### 溶解 (Dissolve)

```python
editor.add_transition(
    clip_id="clip-001",
    transition_type=TransitionType.DISSOLVE,
    duration=0.5,
    # 詳細參數
    intensity=0.8,       # 溶解強度
    particles=100,       # 粒子數量
)
```

**使用場景:**
- 時間流逝
- 場景切換
- 回憶轉換
- 夢境切換

#### 縮放轉場 (Zoom)

```python
editor.add_transition(
    clip_id="clip-001",
    transition_type=TransitionType.ZOOM,
    duration=0.8,
    position="end",
    # 詳細參數
    zoom_factor=1.5,     # 縮放倍數
    direction="in",      # "in" 或 "out"
    easing="ease_out",
)
```

**參數詳解:**

| 參數 | 選項 | 說明 | 默認 |
|------|------|------|------|
| **zoom_factor** | 0.5-3.0 | 縮放倍數 | 1.5 |
| **direction** | in/out | 縮放方向 | in |

**使用場景:**
- 強調重點
- 場景轉換
- MV 製作
- 預告片

---

## 4. 字幕系統

### 字幕樣式詳解

#### 純文本 (Plain)

```python
editor.add_subtitle(
    clip_id="clip-001",
    text="故事開始",
    start_time=0.5,
    end_time=3.0,
    style=SubtitleStyle.PLAIN,
    # 詳細參數
    position="bottom",   # top/center/bottom
    font_size=24,
    font_color="#FFFFFF",
    font_family="Arial",
    bold=False,
    italic=False,
)
```

#### 霓虹 (Neon)

```python
editor.add_subtitle(
    clip_id="clip-001",
    text="賽博朋克 2077",
    start_time=1.0,
    end_time=4.0,
    style=SubtitleStyle.NEON,
    # 霓虹專用參數
    position="center",
    font_size=36,
    font_color="#00FFFF",
    glow_color="#00FFFF",
    glow_intensity=0.8,
    background_color="#000000",
    animation="pulse",   # pulse/flicker/glow
)
```

**動畫效果:**

| 動畫 | 說明 | 適用場景 |
|------|------|---------|
| `pulse` | 脈衝發光 | 霓虹燈 |
| `flicker` | 閃爍 | 故障效果 |
| `glow` | 漸變發光 | 夢幻 |
| `typewriter` | 打字機 | 敘述 |

---

## 5. 音頻編輯

### 效果器詳解

#### 降噪 (Noise Reduction)

```python
editor.apply_audio_effect(
    track_id="track-001",
    effect_type=AudioEffectType.NOISE_REDUCTION,
    # 詳細參數
    strength=0.7,        # 降噪強度 0.0-1.0
    threshold=-40,       # 閾值 dB
    reduction=12,        # 降噪量 dB
)
```

**參數詳解:**

| 參數 | 範圍 | 說明 | 默認 |
|------|------|------|------|
| **strength** | 0.0-1.0 | 降噪強度 | 0.7 |
| **threshold** | -60 to 0 | 噪聲閾值 (dB) | -40 |
| **reduction** | 0-20 | 降噪量 (dB) | 12 |

**使用建議:**
- 輕微噪聲：strength=0.3
- 中等噪聲：strength=0.5
- 嚴重噪聲：strength=0.8

#### 混響 (Reverb)

```python
editor.apply_audio_effect(
    track_id="track-001",
    effect_type=AudioEffectType.REVERB,
    # 詳細參數
    room_size=0.5,       # 房間大小
    dampening=0.3,       # 阻尼
   width=1.0,           # 寬度
    dry=0.5,             # 乾聲比例
    wet=0.5,             # 濕聲比例
)
```

**預設場景:**

```python
# 小房間
editor.apply_audio_effect(track_id, AudioEffectType.REVERB,
    room_size=0.2, dampening=0.5, dry=0.7, wet=0.3)

# 大教堂
editor.apply_audio_effect(track_id, AudioEffectType.REVERB,
    room_size=0.9, dampening=0.2, dry=0.3, wet=0.7)

# 音樂廳
editor.apply_audio_effect(track_id, AudioEffectType.REVERB,
    room_size=0.7, dampening=0.3, dry=0.5, wet=0.5)
```

---

## 6. 專業調色

### 調色參數詳解

```python
editor.apply_color_grade(
    clip_id="clip-001",
    # 基礎參數
    brightness=0.0,      # -1.0 到 1.0
    contrast=0.0,        # -1.0 到 1.0
    saturation=0.0,      # -1.0 到 1.0
    
    # 色調參數
    temperature=0.0,     # -1.0 (冷) 到 1.0 (暖)
    tint=0.0,            # -1.0 (綠) 到 1.0 (洋紅)
    
    # 進階參數
    highlights=0.0,      # -1.0 到 1.0
    shadows=0.0,         # -1.0 到 1.0
    midtones=0.0,        # -1.0 到 1.0
)
```

**參數影響範圍:**

| 參數 | 負值效果 | 正值效果 |
|------|---------|---------|
| **brightness** | 變暗 | 變亮 |
| **contrast** | 降低對比 | 增加對比 |
| **saturation** | 降低飽和 | 增加飽和 |
| **temperature** | 冷色調 (藍) | 暖色調 (黃) |
| **tint** | 綠色調 | 洋紅色調 |
| **highlights** | 壓暗高光 | 提亮高光 |
| **shadows** | 壓暗陰影 | 提亮陰影 |

### 預設詳解

#### 電影暖色調 (cinematic_warm)

```python
editor.apply_color_preset(
    clip_id="clip-001",
    preset="cinematic_warm",
)
```

**內部參數:**
```python
{
    "brightness": 0.05,
    "contrast": 0.15,
    "saturation": -0.1,
    "temperature": 0.2,
    "highlights": -0.1,
    "shadows": 0.1,
}
```

**適用場景:**
- 浪漫愛情
- 溫馨家庭
- 日落黃昏
- 室內暖光

#### 戲劇效果 (dramatic)

```python
editor.apply_color_preset(
    clip_id="clip-001",
    preset="dramatic",
)
```

**內部參數:**
```python
{
    "brightness": -0.1,
    "contrast": 0.3,
    "saturation": 0.1,
    "highlights": -0.3,
    "shadows": -0.2,
}
```

**適用場景:**
- 動作場面
- 懸疑驚悚
- 戲劇衝突
- 強烈情緒

---

## 7. 速度控制

### 慢動作詳解

```python
result = editor.create_slow_motion(
    clip_id="clip-001",
    factor=0.5,          # 0.1-1.0
)
```

**速度對應表:**

| factor | 速度 | 時長變化 | 適用場景 |
|--------|------|---------|---------|
| 0.1 | 10% | 10x | 極致慢動作 |
| 0.25 | 25% | 4x | 動作場面 |
| 0.5 | 50% | 2x | 通用慢作 |
| 0.75 | 75% | 1.33x | 微慢動作 |

**使用示例:**

```python
# 動作場面慢動作 (25% 速度)
editor.create_slow_motion(clip_id, factor=0.25)

# 情感場面微慢動作 (75% 速度)
editor.create_slow_motion(clip_id, factor=0.75)

# 極致慢動作 (10% 速度)
editor.create_slow_motion(clip_id, factor=0.1)
```

---

## 8. 畫幅調整

### 裁剪詳解

```python
result = editor.crop_clip(
    clip_id="clip-001",
    x=100,               # 起始 X 坐標 (像素)
    y=50,                # 起始 Y 坐標 (像素)
    width=1920,          # 裁剪寬度
    height=1080,         # 裁剪高度
)
```

**常見畫幅裁剪:**

```python
# 16:9 轉 9:16 (豎屏)
editor.crop_clip(clip_id, x=420, y=0, width=1080, height=1920)

# 16:9 轉 1:1 (正方形)
editor.crop_clip(clip_id, x=420, y=0, width=1080, height=1080)

# 16:9 轉 2.35:1 (電影寬銀幕)
editor.crop_clip(clip_id, x=0, y=207, width=1920, height=817)
```

---

## 9. 完整工作流程

### 專業剪輯流程

```python
from app.services.video_editor import (
    get_video_editor_service,
    FilterType,
    TransitionType,
    SubtitleStyle,
    AudioEffectType,
)

editor = get_video_editor_service()

# ===== 第一階段：素材準備 =====

# 1. 創建基礎片段
clip1 = editor.create_clip("scene-001", 0.0, 5.0, order=0)
clip2 = editor.create_clip("scene-002", 0.0, 8.0, order=1)
clip3 = editor.create_clip("scene-003", 0.0, 6.0, order=2)

# 2. 修剪片段
clip1 = editor.trim_clip(clip1.id, 0.5, 4.8)  # 去掉頭尾
clip2 = editor.trim_clip(clip2.id, 1.0, 7.5)

# ===== 第二階段：視覺效果 =====

# 3. 應用濾鏡
editor.apply_filter(clip1.id, FilterType.CINEMATIC, intensity=0.8)
editor.apply_filter(clip2.id, FilterType.WARM, intensity=0.5)
editor.apply_filter(clip3.id, FilterType.COOL, intensity=0.6)

# 4. 添加轉場
editor.add_transition(clip1.id, TransitionType.FADE, duration=1.0, position="end")
editor.add_transition(clip2.id, TransitionType.DISSOLVE, duration=0.5, position="end")

# ===== 第三階段：字幕 =====

# 5. 添加字幕
editor.add_subtitle(
    clip1.id,
    text="故事開始",
    start_time=0.5,
    end_time=3.0,
    style=SubtitleStyle.PLAIN,
    font_size=24,
)

editor.add_subtitle(
    clip2.id,
    text="高潮來臨",
    start_time=2.0,
    end_time=5.0,
    style=SubtitleStyle.NEON,
    font_color="#00FFFF",
)

# ===== 第四階段：音頻 =====

# 6. 添加背景音樂
bgm = editor.add_audio_track(
    clip1.id,
    file_path="/music/epic.mp3",
    audio_type="background",
    volume=0.3,
)

# 7. 音頻效果
editor.apply_audio_effect(bgm.id, AudioEffectType.FADE_IN, duration=2.0)
editor.apply_audio_effect(bgm.id, AudioEffectType.FADE_OUT, duration=3.0)

# ===== 第五階段：調色 =====

# 8. 統一調色
editor.apply_color_preset(clip1.id, "cinematic_warm")
editor.apply_color_preset(clip2.id, "cinematic_warm")
editor.apply_color_preset(clip3.id, "dramatic")

# ===== 第六階段：導出 =====

# 9. 獲取時間線
timeline = editor.get_edit_timeline("proj-001")
print(f"總時長：{timeline['total_duration']}秒")

# 10. 導出
result = editor.export_project("proj-001", format="mp4")
print(f"預計處理時間：{result['estimated_time']}秒")
```

---

## 10. 最佳實踐

### 性能優化

```python
# ✅ 好的做法：批量操作
clips = []
for i in range(10):
    clip = editor.create_clip(f"scene-{i:03d}", 0.0, 5.0, order=i)
    clips.append(clip)

# ❌ 避免：單次操作間隔過長
```

### 濾鏡使用建議

```python
# ✅ 好的做法：適度使用
editor.apply_filter(clip_id, FilterType.CINEMATIC, intensity=0.6)

# ❌ 避免：過度使用
editor.apply_filter(clip_id, FilterType.CINEMATIC, intensity=1.0)
editor.apply_filter(clip_id, FilterType.CONTRAST, intensity=1.0)
editor.apply_filter(clip_id, FilterType.SATURATION, intensity=1.0)
```

### 轉場使用建議

```python
# ✅ 好的做法：統一風格
transitions = [
    TransitionType.FADE,
    TransitionType.DISSOLVE,
    TransitionType.FADE,
]

# ❌ 避免：混用過多風格
transitions = [
    TransitionType.FADE,
    TransitionType.GLITCH,
    TransitionType.ZOOM,
    TransitionType.LIGHT_LEAK,
]
```

---

**更新日期:** 2026-03-30 14:45  
**版本:** v2.1  
**GitHub:** https://github.com/iiooiioo888/AI_test
