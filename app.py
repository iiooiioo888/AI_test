#!/usr/bin/env python3
"""
AI Video Studio - AI 特效 / 视频扩展 Web 应用
"""
import asyncio
import json
import os
import time
import uuid
import subprocess
import shutil
from pathlib import Path
from typing import Optional

import cv2
import numpy as np
from fastapi import FastAPI, File, UploadFile, WebSocket, WebSocketDisconnect, Form, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware

# ── Paths ──────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent
UPLOAD_DIR = BASE_DIR / "uploads"
OUTPUT_DIR = BASE_DIR / "output"
UPLOAD_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

app = FastAPI(title="AI Video Studio")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

# ── Task tracker ───────────────────────────────────────────────
tasks: dict[str, dict] = {}
ws_clients: list[WebSocket] = []

# ── Effects Registry ───────────────────────────────────────────
EFFECTS = {
    "glitch": {"name": "故障艺术 Glitch", "icon": "⚡", "desc": "数字故障、信号干扰效果"},
    "vhs": {"name": "VHS 复古", "icon": "📼", "desc": "90年代录像带质感"},
    "cyberpunk": {"name": "赛博朋克", "icon": "🌆", "desc": "霓虹色调 + 扫描线"},
    "noir": {"name": "黑色电影", "icon": "🎬", "desc": "高对比黑白 + 暗角"},
    "dreamy": {"name": "梦幻柔光", "icon": "✨", "desc": "柔焦 + 光晕效果"},
    "neon": {"name": "霓虹描边", "icon": "💜", "desc": "边缘发光 + 深色背景"},
    "pixel": {"name": "像素风", "icon": "👾", "desc": "复古像素化效果"},
    "thermal": {"name": "热成像", "icon": "🔥", "desc": "红外热力图效果"},
    "sketch": {"name": "素描风", "icon": "✏️", "desc": "铅笔手绘效果"},
    "matrix": {"name": "黑客帝国", "icon": "💊", "desc": "绿色矩阵数字雨"},
    "comic": {"name": "漫画风", "icon": "💥", "desc": "波普漫画网点效果"},
    "wave": {"name": "波浪扭曲", "icon": "🌊", "desc": "正弦波形变动画"},
}

EXTEND_MODES = {
    "loop_smooth": {"name": "无缝循环", "icon": "🔄", "desc": "首尾平滑过渡循环"},
    "ping_pong": {"name": "乒乓播放", "icon": "↔️", "desc": "正放+倒放"},
    "slow_motion": {"name": "AI 慢动作", "icon": "🐢", "desc": "光流插帧慢放"},
    "reverse": {"name": "倒放", "icon": "⏪", "desc": "完整倒放视频"},
    "speed_ramp": {"name": "速度渐变", "icon": "📈", "desc": "慢→快→慢节奏变化"},
    "freeze_frame": {"name": "定格延伸", "icon": "❄️", "desc": "结尾定格淡出"},
    "extend_repeat": {"name": "片段重复", "icon": "🔁", "desc": "精彩片段智能重复"},
    "time_slice": {"name": "时间切片", "icon": "🔪", "desc": "多帧同屏时间冻结"},
}


# ═══════════════════════════════════════════════════════════════
#  Video Processing Engine
# ═══════════════════════════════════════════════════════════════

def get_video_info(path: str) -> dict:
    """Get video metadata via ffprobe."""
    cmd = [
        "ffprobe", "-v", "quiet", "-print_format", "json",
        "-show_format", "-show_streams", str(path)
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    info = json.loads(result.stdout)
    video_stream = next((s for s in info.get("streams", []) if s["codec_type"] == "video"), {})
    return {
        "duration": float(info.get("format", {}).get("duration", 0)),
        "width": int(video_stream.get("width", 0)),
        "height": int(video_stream.get("height", 0)),
        "fps": eval(video_stream.get("r_frame_rate", "30/1")),
        "codec": video_stream.get("codec_name", "unknown"),
        "size": int(info.get("format", {}).get("size", 0)),
    }


async def broadcast(task_id: str, progress: float, status: str, message: str = ""):
    """Push progress to all WS clients."""
    payload = json.dumps({
        "task_id": task_id,
        "progress": round(progress, 1),
        "status": status,
        "message": message,
    })
    dead = []
    for ws in ws_clients:
        try:
            await ws.send_text(payload)
        except Exception:
            dead.append(ws)
    for ws in dead:
        ws_clients.remove(ws)


# ── Effect Processors ──────────────────────────────────────────

def apply_glitch(frame: np.ndarray, intensity: float = 0.5) -> np.ndarray:
    h, w = frame.shape[:2]
    result = frame.copy()
    # RGB shift
    shift = int(w * 0.02 * intensity)
    result[:, :, 0] = np.roll(result[:, :, 0], shift, axis=1)
    result[:, :, 2] = np.roll(result[:, :, 2], -shift, axis=1)
    # Random horizontal slices
    for _ in range(int(5 * intensity)):
        y = np.random.randint(0, h)
        slice_h = np.random.randint(5, int(30 * intensity))
        x_shift = np.random.randint(-int(50 * intensity), int(50 * intensity))
        y_end = min(y + slice_h, h)
        result[y:y_end] = np.roll(result[y:y_end], x_shift, axis=1)
    # Scanlines
    for y in range(0, h, 3):
        result[y] = (result[y] * 0.7).astype(np.uint8)
    # Noise
    noise = np.random.randint(0, int(50 * intensity), (h, w, 3), dtype=np.uint8)
    result = cv2.add(result, noise)
    return result


def apply_vhs(frame: np.ndarray, intensity: float = 0.5) -> np.ndarray:
    h, w = frame.shape[:2]
    # Slight blur + warm tint
    result = cv2.GaussianBlur(frame, (3, 3), 0)
    result = result.astype(np.float32)
    result[:, :, 2] = np.clip(result[:, :, 2] * (1 + 0.15 * intensity), 0, 255)  # Red boost
    result[:, :, 0] = np.clip(result[:, :, 0] * (1 - 0.1 * intensity), 0, 255)   # Blue reduce
    result = result.astype(np.uint8)
    # Scanlines
    for y in range(0, h, 2):
        result[y] = (result[y] * 0.85).astype(np.uint8)
    # Tracking lines
    for _ in range(int(3 * intensity)):
        y = np.random.randint(0, h)
        result[y:y+2] = 255
    # Slight noise
    noise = np.random.randint(0, int(20 * intensity), (h, w, 1), dtype=np.uint8)
    noise = np.repeat(noise, 3, axis=2)
    result = cv2.add(result, noise)
    return result


def apply_cyberpunk(frame: np.ndarray, intensity: float = 0.5) -> np.ndarray:
    result = frame.astype(np.float32)
    # Teal shadows, magenta highlights
    result[:, :, 0] = np.clip(result[:, :, 0] * (1 + 0.3 * intensity), 0, 255)  # Blue
    result[:, :, 1] = np.clip(result[:, :, 1] * (1 - 0.1 * intensity), 0, 255)  # Green
    result[:, :, 2] = np.clip(result[:, :, 2] * (1 + 0.2 * intensity), 0, 255)  # Red
    result = result.astype(np.uint8)
    # Scanlines
    h = result.shape[0]
    for y in range(0, h, 4):
        result[y] = (result[y] * 0.8).astype(np.uint8)
    # Contrast boost
    result = cv2.convertScaleAbs(result, alpha=1.3, beta=10)
    return result


def apply_noir(frame: np.ndarray, intensity: float = 0.5) -> np.ndarray:
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    # High contrast
    clahe = cv2.createCLAHE(clipLimit=3.0 * intensity, tileGridSize=(8, 8))
    gray = clahe.apply(gray)
    result = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
    # Vignette
    h, w = result.shape[:2]
    Y, X = np.ogrid[:h, :w]
    center_y, center_x = h / 2, w / 2
    dist = np.sqrt((X - center_x) ** 2 + (Y - center_y) ** 2)
    max_dist = np.sqrt(center_x ** 2 + center_y ** 2)
    vignette = 1 - (dist / max_dist) * 0.7 * intensity
    vignette = np.clip(vignette, 0, 1)
    result = (result * vignette[:, :, np.newaxis]).astype(np.uint8)
    # Film grain
    grain = np.random.randint(0, int(30 * intensity), result.shape, dtype=np.uint8)
    result = cv2.add(result, grain)
    return result


def apply_dreamy(frame: np.ndarray, intensity: float = 0.5) -> np.ndarray:
    # Soft glow
    blur = cv2.GaussianBlur(frame, (0, 0), sigmaX=10 * intensity)
    result = cv2.addWeighted(frame, 0.6, blur, 0.5, 10 * intensity)
    # Warm tint
    result = result.astype(np.float32)
    result[:, :, 2] = np.clip(result[:, :, 2] * 1.1, 0, 255)
    return result.astype(np.uint8)


def apply_neon(frame: np.ndarray, intensity: float = 0.5) -> np.ndarray:
    # Edge detection
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 50, 150)
    edges = cv2.dilate(edges, None, iterations=1)
    # Color edges
    h, w = edges.shape
    colored = np.zeros((h, w, 3), dtype=np.uint8)
    # Multi-color neon
    colored[:, :, 0] = edges  # Blue
    colored[:, :, 1] = np.roll(edges, w // 3, axis=1)  # Green shifted
    colored[:, :, 2] = np.roll(edges, 2 * w // 3, axis=1)  # Red shifted
    # Glow effect
    glow = cv2.GaussianBlur(colored, (0, 0), sigmaX=5 * intensity)
    glow = cv2.addWeighted(colored, 0.7, glow, 0.5, 0)
    # Dark background blend
    dark_bg = (frame * 0.15).astype(np.uint8)
    result = cv2.add(dark_bg, glow)
    return result


def apply_pixel(frame: np.ndarray, intensity: float = 0.5) -> np.ndarray:
    h, w = frame.shape[:2]
    pixel_size = max(2, int(16 * intensity))
    small = cv2.resize(frame, (w // pixel_size, h // pixel_size), interpolation=cv2.INTER_LINEAR)
    result = cv2.resize(small, (w, h), interpolation=cv2.INTER_NEAREST)
    # Reduce colors
    result = (result // 32) * 32
    return result


def apply_thermal(frame: np.ndarray, intensity: float = 0.5) -> np.ndarray:
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    # Apply colormap
    result = cv2.applyColorMap(gray, cv2.COLORMAP_JET)
    if intensity > 0.5:
        result = cv2.applyColorMap(gray, cv2.COLORMAP_INFERNO)
    # Add temperature readout effect
    h, w = result.shape[:2]
    # Scan line
    scan_y = (int(time.time() * 30) % h)
    result[scan_y:scan_y+2] = [255, 255, 255]
    return result


def apply_sketch(frame: np.ndarray, intensity: float = 0.5) -> np.ndarray:
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    inv = 255 - gray
    blur = cv2.GaussianBlur(inv, (21, 21), 0)
    sketch = cv2.divide(gray, 255 - blur, scale=256)
    result = cv2.cvtColor(sketch, cv2.COLOR_GRAY2BGR)
    # Paper texture
    if intensity > 0.3:
        noise = np.random.randint(230, 255, result.shape, dtype=np.uint8)
        result = cv2.addWeighted(result, 0.85, noise, 0.15, 0)
    return result


def apply_matrix(frame: np.ndarray, intensity: float = 0.5) -> np.ndarray:
    h, w = frame.shape[:2]
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    # Green tint base
    result = np.zeros_like(frame)
    result[:, :, 1] = gray  # Green channel
    result = (result * 0.4).astype(np.uint8)
    # Matrix rain overlay
    font = cv2.FONT_HERSHEY_SIMPLEX
    chars = "01アイウエオカキクケコサシスセソ"
    for _ in range(int(w / 15 * intensity)):
        x = np.random.randint(0, w)
        char_len = np.random.randint(3, 15)
        for j in range(char_len):
            y_offset = (int(time.time() * 100) + j * 20) % h
            char = np.random.choice(list(chars))
            brightness = int(255 * (1 - j / char_len))
            color = (0, brightness, 0)
            if 0 <= y_offset < h and 0 <= x < w:
                cv2.putText(result, char, (x, y_offset), font, 0.4, color, 1, cv2.LINE_AA)
    return result


def apply_comic(frame: np.ndarray, intensity: float = 0.5) -> np.ndarray:
    # Edge-preserving filter for cartoon effect
    color = cv2.bilateralFilter(frame, 9, 300, 300)
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    edges = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C,
                                   cv2.THRESH_BINARY, 9, 10 * intensity)
    edges = cv2.cvtColor(edges, cv2.COLOR_GRAY2BGR)
    result = cv2.bitwise_and(color, edges)
    # Boost saturation
    hsv = cv2.cvtColor(result, cv2.COLOR_BGR2HSV).astype(np.float32)
    hsv[:, :, 1] = np.clip(hsv[:, :, 1] * (1.5 + intensity), 0, 255)
    result = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR)
    return result


def apply_wave(frame: np.ndarray, intensity: float = 0.5, t: float = 0) -> np.ndarray:
    h, w = frame.shape[:2]
    result = np.zeros_like(frame)
    for y in range(h):
        shift = int(20 * intensity * np.sin(2 * np.pi * y / 60 + t))
        result[y] = np.roll(frame[y], shift, axis=0)
    return result


EFFECT_FN = {
    "glitch": lambda f, i, t: apply_glitch(f, i),
    "vhs": lambda f, i, t: apply_vhs(f, i),
    "cyberpunk": lambda f, i, t: apply_cyberpunk(f, i),
    "noir": lambda f, i, t: apply_noir(f, i),
    "dreamy": lambda f, i, t: apply_dreamy(f, i),
    "neon": lambda f, i, t: apply_neon(f, i),
    "pixel": lambda f, i, t: apply_pixel(f, i),
    "thermal": lambda f, i, t: apply_thermal(f, i),
    "sketch": lambda f, i, t: apply_sketch(f, i),
    "matrix": lambda f, i, t: apply_matrix(f, i),
    "comic": lambda f, i, t: apply_comic(f, i),
    "wave": lambda f, i, t: apply_wave(f, i, t),
}


# ── Core Processing ────────────────────────────────────────────

async def process_effect(task_id: str, input_path: str, effect: str, intensity: float):
    """Apply effect to entire video."""
    tasks[task_id] = {"status": "processing", "progress": 0}
    await broadcast(task_id, 0, "processing", "读取视频...")

    cap = cv2.VideoCapture(input_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    output_path = str(OUTPUT_DIR / f"{task_id}.mp4")
    # Use FFmpeg pipe for output
    cmd = [
        "ffmpeg", "-y",
        "-f", "rawvideo", "-pix_fmt", "bgr24",
        "-s", f"{w}x{h}", "-r", str(fps),
        "-i", "-",
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-pix_fmt", "yuv420p",
        output_path
    ]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    fn = EFFECT_FN.get(effect, apply_glitch)
    frame_idx = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break
        t = frame_idx / fps
        processed = fn(frame, intensity, t)
        proc.stdin.write(processed.tobytes())
        frame_idx += 1
        if frame_idx % 10 == 0:
            progress = (frame_idx / total) * 100
            tasks[task_id]["progress"] = progress
            await broadcast(task_id, progress, "processing", f"处理帧 {frame_idx}/{total}")

    cap.release()
    proc.stdin.close()
    proc.wait()

    tasks[task_id] = {"status": "done", "progress": 100, "output": output_path}
    await broadcast(task_id, 100, "done", "处理完成！")
    return output_path


async def process_extend(task_id: str, input_path: str, mode: str, extra_param: float = 2.0):
    """Extend video using selected mode."""
    tasks[task_id] = {"status": "processing", "progress": 0}
    await broadcast(task_id, 0, "processing", "分析视频...")

    output_path = str(OUTPUT_DIR / f"{task_id}.mp4")
    info = get_video_info(input_path)

    if mode == "loop_smooth":
        await _extend_loop_smooth(task_id, input_path, output_path, info)
    elif mode == "ping_pong":
        await _extend_ping_pong(task_id, input_path, output_path)
    elif mode == "slow_motion":
        await _extend_slow_motion(task_id, input_path, output_path, info, extra_param)
    elif mode == "reverse":
        await _extend_reverse(task_id, input_path, output_path)
    elif mode == "speed_ramp":
        await _extend_speed_ramp(task_id, input_path, output_path, info)
    elif mode == "freeze_frame":
        await _extend_freeze(task_id, input_path, output_path, info, extra_param)
    elif mode == "extend_repeat":
        await _extend_repeat(task_id, input_path, output_path, extra_param)
    elif mode == "time_slice":
        await _extend_time_slice(task_id, input_path, output_path, info)
    else:
        await _extend_loop_smooth(task_id, input_path, output_path, info)

    tasks[task_id] = {"status": "done", "progress": 100, "output": output_path}
    await broadcast(task_id, 100, "done", "扩展完成！")
    return output_path


async def _extend_loop_smooth(task_id, inp, out, info):
    """Create seamless loop with cross-fade at join point."""
    await broadcast(task_id, 20, "processing", "生成无缝循环...")
    fade_dur = min(1.0, info["duration"] / 4)
    cmd = [
        "ffmpeg", "-y", "-i", inp,
        "-filter_complex",
        f"[0]split[orig][copy];"
        f"[copy]trim=start=0:end={fade_dur},setpts=PTS-STARTPTS[fadeclip];"
        f"[orig][fadeclip]xfade=transition=fade:duration={fade_dur}:offset={info['duration']-fade_dur}",
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-pix_fmt", "yuv420p", out
    ]
    subprocess.run(cmd, capture_output=True)
    await broadcast(task_id, 80, "processing", "编码完成")


async def _extend_ping_pong(task_id, inp, out):
    """Forward + reverse playback."""
    await broadcast(task_id, 20, "processing", "生成乒乓播放...")
    cmd = [
        "ffmpeg", "-y", "-i", inp,
        "-filter_complex",
        "[0]split[fwd][tmp];[tmp]reverse[rev];[fwd][rev]concat=n=2:v=1:a=0",
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-pix_fmt", "yuv420p", out
    ]
    subprocess.run(cmd, capture_output=True)


async def _extend_slow_motion(task_id, inp, out, info, factor=2.0):
    """Slow motion with frame interpolation via minterpolate."""
    await broadcast(task_id, 10, "processing", "AI 插帧慢放中（耗时较长）...")
    new_fps = info["fps"] * factor
    cmd = [
        "ffmpeg", "-y", "-i", inp,
        "-filter_complex",
        f"minterpolate=fps={new_fps}:mi_mode=blend",
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-pix_fmt", "yuv420p", out
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        # Fallback: simple framerate change
        cmd = [
            "ffmpeg", "-y", "-i", inp,
            "-filter_complex", f"setpts={factor}*PTS",
            "-c:v", "libx264", "-preset", "fast", "-crf", "23",
            "-pix_fmt", "yuv420p", out
        ]
        subprocess.run(cmd, capture_output=True)


async def _extend_reverse(task_id, inp, out):
    """Full reverse."""
    await broadcast(task_id, 30, "processing", "生成倒放...")
    cmd = [
        "ffmpeg", "-y", "-i", inp,
        "-vf", "reverse", "-af", "areverse",
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-pix_fmt", "yuv420p", out
    ]
    subprocess.run(cmd, capture_output=True)


async def _extend_speed_ramp(task_id, inp, out, info):
    """Slow → Fast → Slow speed ramp."""
    await broadcast(task_id, 20, "processing", "生成速度渐变...")
    dur = info["duration"]
    third = dur / 3
    cmd = [
        "ffmpeg", "-y", "-i", inp,
        "-filter_complex",
        f"[0]split=3[p1][p2][p3];"
        f"[p1]trim=0:{third},setpts=1.5*(PTS-STARTPTS)[s1];"
        f"[p2]trim={third}:{2*third},setpts=0.5*(PTS-STARTPTS)[s2];"
        f"[p3]trim={2*third}:,setpts=1.5*(PTS-STARTPTS)[s3];"
        f"[s1][s2][s3]concat=n=3:v=1:a=0",
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-pix_fmt", "yuv420p", out
    ]
    subprocess.run(cmd, capture_output=True)


async def _extend_freeze(task_id, inp, out, info, freeze_sec=3.0):
    """Freeze last frame with fade out."""
    await broadcast(task_id, 20, "processing", "生成定格延伸...")
    last_frame_time = info["duration"] - 0.04
    cmd = [
        "ffmpeg", "-y", "-i", inp,
        "-filter_complex",
        f"[0]split[vid][still];"
        f"[still]trim=start={last_frame_time},setpts=PTS-STARTPTS,loop=loop=-1:size=2:start=0[frz];"
        f"[frz]fade=t=out:st={freeze_sec-1}:d=1[frzf];"
        f"[vid][frzf]concat=n=2:v=1:a=0",
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-pix_fmt", "yuv420p", out
    ]
    subprocess.run(cmd, capture_output=True)


async def _extend_repeat(task_id, inp, out, times=2.0):
    """Repeat video N times."""
    times = int(times)
    await broadcast(task_id, 20, "processing", f"重复 {times} 次...")
    inputs = []
    filter_parts = []
    for i in range(times):
        inputs.extend(["-i", inp])
        filter_parts.append(f"[{i}:v]")
    filter_str = "".join(filter_parts) + f"concat=n={times}:v=1:a=0"
    cmd = ["ffmpeg", "-y"] + inputs + [
        "-filter_complex", filter_str,
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-pix_fmt", "yuv420p", out
    ]
    subprocess.run(cmd, capture_output=True)


async def _extend_time_slice(task_id, inp, out, info):
    """Extract key frames and tile them."""
    await broadcast(task_id, 20, "processing", "生成时间切片...")
    # Extract 6 evenly spaced frames and create a grid
    n_slices = 6
    timestamps = [i * info["duration"] / n_slices for i in range(n_slices)]
    temp_dir = OUTPUT_DIR / f"ts_{task_id}"
    temp_dir.mkdir(exist_ok=True)

    for i, ts in enumerate(timestamps):
        cmd = [
            "ffmpeg", "-y", "-ss", str(ts), "-i", inp,
            "-frames:v", "1", str(temp_dir / f"slice_{i:02d}.png")
        ]
        subprocess.run(cmd, capture_output=True)

    # Create montage with ffmpeg
    cmd = [
        "ffmpeg", "-y",
        "-i", str(temp_dir / "slice_%02d.png"),
        "-filter_complex", "tile=3x2",
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-pix_fmt", "yuv420p", out
    ]
    subprocess.run(cmd, capture_output=True)
    shutil.rmtree(temp_dir, ignore_errors=True)


# ═══════════════════════════════════════════════════════════════
#  API Routes
# ═══════════════════════════════════════════════════════════════

@app.get("/", response_class=HTMLResponse)
async def index():
    return (BASE_DIR / "templates" / "index.html").read_text()


@app.get("/api/effects")
async def list_effects():
    return {"effects": EFFECTS, "extend_modes": EXTEND_MODES}


@app.post("/api/upload")
async def upload_video(file: UploadFile = File(...)):
    """Upload a video file."""
    ext = Path(file.filename).suffix.lower()
    if ext not in {".mp4", ".avi", ".mov", ".mkv", ".webm", ".gif"}:
        raise HTTPException(400, "不支持的格式。请上传 MP4/AVI/MOV/MKV/WebM/GIF")

    file_id = str(uuid.uuid4())[:8]
    save_path = UPLOAD_DIR / f"{file_id}{ext}"
    content = await file.read()
    async with open(save_path, "wb") as f:
        await f.write(content)

    info = get_video_info(str(save_path))
    return {
        "file_id": file_id,
        "filename": file.filename,
        "path": str(save_path),
        "info": info,
    }


@app.post("/api/process/effect")
async def start_effect(
    file_id: str = Form(...),
    effect: str = Form(...),
    intensity: float = Form(0.5),
):
    """Start applying an effect."""
    if effect not in EFFECTS:
        raise HTTPException(400, f"未知特效: {effect}")

    input_files = list(UPLOAD_DIR.glob(f"{file_id}.*"))
    if not input_files:
        raise HTTPException(404, "找不到上传的文件")

    task_id = str(uuid.uuid4())[:8]
    asyncio.create_task(process_effect(task_id, str(input_files[0]), effect, intensity))
    return {"task_id": task_id, "effect": effect}


@app.post("/api/process/extend")
async def start_extend(
    file_id: str = Form(...),
    mode: str = Form(...),
    param: float = Form(2.0),
):
    """Start video extension."""
    if mode not in EXTEND_MODES:
        raise HTTPException(400, f"未知模式: {mode}")

    input_files = list(UPLOAD_DIR.glob(f"{file_id}.*"))
    if not input_files:
        raise HTTPException(404, "找不到上传的文件")

    task_id = str(uuid.uuid4())[:8]
    asyncio.create_task(process_extend(task_id, str(input_files[0]), mode, param))
    return {"task_id": task_id, "mode": mode}


@app.get("/api/task/{task_id}")
async def get_task(task_id: str):
    """Get task status."""
    if task_id not in tasks:
        raise HTTPException(404, "任务不存在")
    return tasks[task_id]


@app.get("/api/download/{task_id}")
async def download(task_id: str):
    """Download processed video."""
    if task_id not in tasks or tasks[task_id]["status"] != "done":
        raise HTTPException(404, "文件未就绪")
    path = tasks[task_id]["output"]
    return FileResponse(path, media_type="video/mp4", filename=f"ai_video_{task_id}.mp4")


@app.get("/api/preview/{file_id}")
async def preview(file_id: str):
    """Stream uploaded video for preview."""
    input_files = list(UPLOAD_DIR.glob(f"{file_id}.*"))
    if not input_files:
        raise HTTPException(404)
    return FileResponse(str(input_files[0]))


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    ws_clients.append(ws)
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        ws_clients.remove(ws)


# ── Cleanup old files periodically ─────────────────────────────
@app.on_event("startup")
async def startup():
    # Clean files older than 1 hour
    now = time.time()
    for d in [UPLOAD_DIR, OUTPUT_DIR]:
        for f in d.iterdir():
            if f.is_file() and now - f.stat().st_mtime > 3600:
                f.unlink()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8888)
