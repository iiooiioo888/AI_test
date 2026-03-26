#!/usr/bin/env python3
"""
AI Video Studio - AI 特效 / 视频扩展 Web 应用
"""
import asyncio
import json
import os
import re
import time
import uuid
import subprocess
import shutil
import logging
from pathlib import Path
from typing import Optional

import cv2
import numpy as np
from fastapi import FastAPI, File, UploadFile, WebSocket, WebSocketDisconnect, Form, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ai_video_studio")

# ── Paths ──────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent
UPLOAD_DIR = BASE_DIR / "uploads"
OUTPUT_DIR = BASE_DIR / "output"
UPLOAD_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

MAX_FILE_SIZE = 500 * 1024 * 1024  # 500MB
FFMPEG_TIMEOUT = 600  # 10 min max per FFmpeg operation
CLEANUP_AGE = 3600  # 1 hour

app = FastAPI(title="AI Video Studio")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

# ── Task tracker ───────────────────────────────────────────────
tasks: dict[str, dict] = {}
ws_clients: list[WebSocket] = []
_processing_locks: set[str] = set()  # file_ids currently being processed

# ── Effects & Modes Registry ───────────────────────────────────
EFFECTS = {
    "glitch":    {"name": "故障艺术 Glitch", "icon": "⚡", "desc": "数字故障、信号干扰效果"},
    "vhs":       {"name": "VHS 复古",       "icon": "📼", "desc": "90年代录像带质感"},
    "cyberpunk": {"name": "赛博朋克",       "icon": "🌆", "desc": "霓虹色调 + 扫描线"},
    "noir":      {"name": "黑色电影",       "icon": "🎬", "desc": "高对比黑白 + 暗角"},
    "dreamy":    {"name": "梦幻柔光",       "icon": "✨", "desc": "柔焦 + 光晕效果"},
    "neon":      {"name": "霓虹描边",       "icon": "💜", "desc": "边缘发光 + 深色背景"},
    "pixel":     {"name": "像素风",         "icon": "👾", "desc": "复古像素化效果"},
    "thermal":   {"name": "热成像",         "icon": "🔥", "desc": "红外热力图效果"},
    "sketch":    {"name": "素描风",         "icon": "✏️", "desc": "铅笔手绘效果"},
    "matrix":    {"name": "黑客帝国",       "icon": "💊", "desc": "绿色矩阵数字雨"},
    "comic":     {"name": "漫画风",         "icon": "💥", "desc": "波普漫画网点效果"},
    "wave":      {"name": "波浪扭曲",       "icon": "🌊", "desc": "正弦波形变动画"},
}

EXTEND_MODES = {
    "loop_smooth":   {"name": "无缝循环", "icon": "🔄", "desc": "首尾平滑过渡循环",      "has_param": False},
    "ping_pong":     {"name": "乒乓播放", "icon": "↔️", "desc": "正放+倒放",            "has_param": False},
    "slow_motion":   {"name": "AI 慢动作","icon": "🐢", "desc": "光流插帧慢放",          "has_param": True,
                      "param_label": "慢放倍率", "param_min": 2, "param_max": 8, "param_step": 1, "param_default": 2},
    "reverse":       {"name": "倒放",     "icon": "⏪", "desc": "完整倒放视频",          "has_param": False},
    "speed_ramp":    {"name": "速度渐变", "icon": "📈", "desc": "慢→快→慢节奏变化",      "has_param": False},
    "freeze_frame":  {"name": "定格延伸", "icon": "❄️", "desc": "结尾定格淡出",          "has_param": True,
                      "param_label": "定格秒数", "param_min": 1, "param_max": 10, "param_step": 1, "param_default": 3},
    "extend_repeat": {"name": "片段重复", "icon": "🔁", "desc": "视频整体重复播放",      "has_param": True,
                      "param_label": "重复次数", "param_min": 2, "param_max": 10, "param_step": 1, "param_default": 2},
    "time_slice":    {"name": "时间切片", "icon": "🔪", "desc": "多帧同屏时间冻结",      "has_param": False},
}


# ═══════════════════════════════════════════════════════════════
#  Utilities
# ═══════════════════════════════════════════════════════════════

def parse_fps(raw: str) -> float:
    """Safely parse frame rate string like '30000/1001'."""
    if "/" in raw:
        num, den = raw.split("/")
        den_f = float(den)
        return float(num) / den_f if den_f else 30.0
    return float(raw) if raw else 30.0


def get_video_info(path: str) -> dict:
    """Get video metadata via ffprobe."""
    cmd = [
        "ffprobe", "-v", "quiet", "-print_format", "json",
        "-show_format", "-show_streams", str(path)
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    info = json.loads(result.stdout)
    video_stream = next((s for s in info.get("streams", []) if s["codec_type"] == "video"), {})
    fmt = info.get("format", {})
    return {
        "duration": float(fmt.get("duration", 0)),
        "width": int(video_stream.get("width", 0)),
        "height": int(video_stream.get("height", 0)),
        "fps": parse_fps(video_stream.get("r_frame_rate", "30")),
        "codec": video_stream.get("codec_name", "unknown"),
        "size": int(fmt.get("size", 0)),
    }


def _run_ffmpeg(cmd: list, timeout: int = FFMPEG_TIMEOUT) -> subprocess.CompletedProcess:
    """Run FFmpeg with timeout protection."""
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)


def _run_ffmpeg_progress(cmd: list, task_id: str, timeout: int = FFMPEG_TIMEOUT) -> subprocess.CompletedProcess:
    """Run FFmpeg with -progress pipe:1 to parse real-time progress."""
    # Insert -progress pipe:1 before output file (last arg)
    full_cmd = cmd[:-1] + ["-progress", "pipe:1", "-nostats", cmd[-1]]
    proc = subprocess.Popen(full_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    start = time.time()
    duration_re = re.compile(r"out_time_us=(\d+)")
    total_re = re.compile(r"total_size=(\d+)")

    try:
        for line in proc.stdout:
            line = line.strip()
            m = duration_re.search(line)
            if m:
                elapsed_us = int(m.group(1))
                # We don't know total duration here, so just report activity
                if time.time() - start > 0.5:
                    # Rough progress based on time elapsed (will be capped at 99%)
                    asyncio.get_event_loop().create_task(
                        _broadcast_progress(task_id, elapsed_us)
                    )
            if line == "progress=end":
                break
        proc.wait(timeout=max(1, timeout - int(time.time() - start)))
    except subprocess.TimeoutExpired:
        proc.kill()
        raise TimeoutError(f"FFmpeg timed out after {timeout}s")

    return subprocess.CompletedProcess(proc.args, proc.returncode, proc.stdout.read(), proc.stderr.read())


async def _broadcast_progress(task_id: str, elapsed_us: int):
    """Quick progress tick during FFmpeg operations."""
    if task_id in tasks:
        cur = tasks[task_id].get("progress", 0)
        # Incremental: don't go backwards
        new_progress = min(95, cur + 2)
        tasks[task_id]["progress"] = new_progress
        await broadcast(task_id, new_progress, "processing", "编码中...")


async def broadcast(task_id: str, progress: float, status: str, message: str = ""):
    """Push progress to all WS clients with dead-client cleanup."""
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
        if ws in ws_clients:
            ws_clients.remove(ws)


def _find_input(file_id: str) -> Optional[Path]:
    """Find uploaded file by file_id."""
    matches = list(UPLOAD_DIR.glob(f"{file_id}.*"))
    return matches[0] if matches else None


# ═══════════════════════════════════════════════════════════════
#  Effect Processors (CPU-bound, run in executor)
# ═══════════════════════════════════════════════════════════════

def apply_glitch(frame: np.ndarray, intensity: float = 0.5) -> np.ndarray:
    h, w = frame.shape[:2]
    result = frame.copy()
    shift = int(w * 0.02 * intensity)
    result[:, :, 0] = np.roll(result[:, :, 0], shift, axis=1)
    result[:, :, 2] = np.roll(result[:, :, 2], -shift, axis=1)
    for _ in range(int(5 * intensity)):
        y = np.random.randint(0, h)
        slice_h = np.random.randint(5, max(6, int(30 * intensity)))
        x_shift = np.random.randint(-int(50 * intensity), int(50 * intensity))
        y_end = min(y + slice_h, h)
        result[y:y_end] = np.roll(result[y:y_end], x_shift, axis=1)
    for y in range(0, h, 3):
        result[y] = (result[y] * 0.7).astype(np.uint8)
    noise = np.random.randint(0, max(1, int(50 * intensity)), (h, w, 3), dtype=np.uint8)
    return cv2.add(result, noise)


def apply_vhs(frame: np.ndarray, intensity: float = 0.5) -> np.ndarray:
    h, w = frame.shape[:2]
    result = cv2.GaussianBlur(frame, (3, 3), 0).astype(np.float32)
    result[:, :, 2] = np.clip(result[:, :, 2] * (1 + 0.15 * intensity), 0, 255)
    result[:, :, 0] = np.clip(result[:, :, 0] * (1 - 0.1 * intensity), 0, 255)
    result = result.astype(np.uint8)
    for y in range(0, h, 2):
        result[y] = (result[y] * 0.85).astype(np.uint8)
    for _ in range(max(1, int(3 * intensity))):
        y = np.random.randint(0, h)
        result[y:min(y+2, h)] = 255
    noise = np.random.randint(0, max(1, int(20 * intensity)), (h, w, 1), dtype=np.uint8)
    return cv2.add(result, np.repeat(noise, 3, axis=2))


def apply_cyberpunk(frame: np.ndarray, intensity: float = 0.5) -> np.ndarray:
    result = frame.astype(np.float32)
    result[:, :, 0] = np.clip(result[:, :, 0] * (1 + 0.3 * intensity), 0, 255)
    result[:, :, 1] = np.clip(result[:, :, 1] * (1 - 0.1 * intensity), 0, 255)
    result[:, :, 2] = np.clip(result[:, :, 2] * (1 + 0.2 * intensity), 0, 255)
    result = result.astype(np.uint8)
    for y in range(0, result.shape[0], 4):
        result[y] = (result[y] * 0.8).astype(np.uint8)
    return cv2.convertScaleAbs(result, alpha=1.3, beta=10)


def apply_noir(frame: np.ndarray, intensity: float = 0.5) -> np.ndarray:
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    clahe = cv2.createCLAHE(clipLimit=3.0 * intensity, tileGridSize=(8, 8))
    result = cv2.cvtColor(clahe.apply(gray), cv2.COLOR_GRAY2BGR)
    h, w = result.shape[:2]
    Y, X = np.ogrid[:h, :w]
    cy, cx = h / 2, w / 2
    dist = np.sqrt((X - cx) ** 2 + (Y - cy) ** 2)
    max_dist = np.sqrt(cx ** 2 + cy ** 2)
    vignette = np.clip(1 - (dist / max_dist) * 0.7 * intensity, 0, 1)
    result = (result * vignette[:, :, np.newaxis]).astype(np.uint8)
    grain = np.random.randint(0, max(1, int(30 * intensity)), result.shape, dtype=np.uint8)
    return cv2.add(result, grain)


def apply_dreamy(frame: np.ndarray, intensity: float = 0.5) -> np.ndarray:
    blur = cv2.GaussianBlur(frame, (0, 0), sigmaX=10 * intensity)
    result = cv2.addWeighted(frame, 0.6, blur, 0.5, 10 * intensity).astype(np.float32)
    result[:, :, 2] = np.clip(result[:, :, 2] * 1.1, 0, 255)
    return result.astype(np.uint8)


def apply_neon(frame: np.ndarray, intensity: float = 0.5) -> np.ndarray:
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    edges = cv2.dilate(cv2.Canny(gray, 50, 150), None, iterations=1)
    h, w = edges.shape
    colored = np.zeros((h, w, 3), dtype=np.uint8)
    colored[:, :, 0] = edges
    colored[:, :, 1] = np.roll(edges, w // 3, axis=1)
    colored[:, :, 2] = np.roll(edges, 2 * w // 3, axis=1)
    glow = cv2.GaussianBlur(colored, (0, 0), sigmaX=5 * intensity)
    glow = cv2.addWeighted(colored, 0.7, glow, 0.5, 0)
    return cv2.add((frame * 0.15).astype(np.uint8), glow)


def apply_pixel(frame: np.ndarray, intensity: float = 0.5) -> np.ndarray:
    h, w = frame.shape[:2]
    pixel_size = max(2, int(16 * intensity))
    small = cv2.resize(frame, (max(1, w // pixel_size), max(1, h // pixel_size)), interpolation=cv2.INTER_LINEAR)
    result = cv2.resize(small, (w, h), interpolation=cv2.INTER_NEAREST)
    return (result // 32) * 32


def apply_thermal(frame: np.ndarray, intensity: float = 0.5) -> np.ndarray:
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    cmap = cv2.COLORMAP_INFERNO if intensity > 0.5 else cv2.COLORMAP_JET
    result = cv2.applyColorMap(gray, cmap)
    h = result.shape[0]
    scan_y = int(time.time() * 30) % h
    result[scan_y:min(scan_y+2, h)] = [255, 255, 255]
    return result


def apply_sketch(frame: np.ndarray, intensity: float = 0.5) -> np.ndarray:
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    inv = 255 - gray
    blur = cv2.GaussianBlur(inv, (21, 21), 0)
    sketch = cv2.divide(gray, 255 - blur, scale=256)
    result = cv2.cvtColor(sketch, cv2.COLOR_GRAY2BGR)
    if intensity > 0.3:
        noise = np.random.randint(230, 255, result.shape, dtype=np.uint8)
        result = cv2.addWeighted(result, 0.85, noise, 0.15, 0)
    return result


def apply_matrix(frame: np.ndarray, intensity: float = 0.5) -> np.ndarray:
    h, w = frame.shape[:2]
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    result = np.zeros_like(frame)
    result[:, :, 1] = gray
    result = (result * 0.4).astype(np.uint8)
    font = cv2.FONT_HERSHEY_SIMPLEX
    chars = "01アイウエオカキクケコサシスセソ"
    char_list = list(chars)
    n_cols = max(1, int(w / 15 * intensity))
    for _ in range(n_cols):
        x = np.random.randint(0, w)
        char_len = np.random.randint(3, 15)
        for j in range(char_len):
            y_offset = (int(time.time() * 100) + j * 20) % h
            brightness = int(255 * (1 - j / char_len))
            if 0 <= y_offset < h and 0 <= x < w:
                cv2.putText(result, np.random.choice(char_list), (x, y_offset), font, 0.4, (0, brightness, 0), 1, cv2.LINE_AA)
    return result


def apply_comic(frame: np.ndarray, intensity: float = 0.5) -> np.ndarray:
    color = cv2.bilateralFilter(frame, 9, 300, 300)
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    edges = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY, 9, 10 * intensity)
    result = cv2.bitwise_and(color, cv2.cvtColor(edges, cv2.COLOR_GRAY2BGR))
    hsv = cv2.cvtColor(result, cv2.COLOR_BGR2HSV).astype(np.float32)
    hsv[:, :, 1] = np.clip(hsv[:, :, 1] * (1.5 + intensity), 0, 255)
    return cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR)


def apply_wave(frame: np.ndarray, intensity: float = 0.5, t: float = 0) -> np.ndarray:
    h = frame.shape[0]
    result = np.zeros_like(frame)
    # Vectorized wave — much faster than per-row loop
    y_indices = np.arange(h)
    shifts = (20 * intensity * np.sin(2 * np.pi * y_indices / 60 + t)).astype(int)
    for y in range(h):
        result[y] = np.roll(frame[y], shifts[y], axis=0)
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


# ═══════════════════════════════════════════════════════════════
#  Synchronous processing (runs in thread executor)
# ═══════════════════════════════════════════════════════════════

def _process_effect_sync(task_id: str, input_path: str, effect: str, intensity: float):
    """CPU-bound effect processing — runs in executor."""
    cap = cv2.VideoCapture(input_path)
    if not cap.isOpened():
        return None, "无法打开视频文件"

    fps = cap.get(cv2.CAP_PROP_FPS)
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    output_path = str(OUTPUT_DIR / f"{task_id}.mp4")
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

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            t = frame_idx / fps if fps > 0 else 0
            processed = fn(frame, intensity, t)
            proc.stdin.write(processed.tobytes())
            frame_idx += 1
    except Exception as e:
        cap.release()
        proc.stdin.close()
        proc.wait()
        return None, str(e)

    cap.release()
    proc.stdin.close()
    proc.wait()
    return output_path, None


def _run_ffmpeg_sync(cmd: list) -> tuple[bool, str]:
    """Run FFmpeg synchronously, return (success, error_msg)."""
    try:
        result = _run_ffmpeg(cmd, timeout=FFMPEG_TIMEOUT)
        if result.returncode != 0:
            return False, result.stderr[-200:] if result.stderr else "FFmpeg failed"
        return True, ""
    except subprocess.TimeoutExpired:
        return False, "FFmpeg 处理超时"
    except Exception as e:
        return False, str(e)


# ═══════════════════════════════════════════════════════════════
#  Async processing orchestrators
# ═══════════════════════════════════════════════════════════════

async def process_effect(task_id: str, input_path: str, effect: str, intensity: float):
    """Orchestrate effect processing without blocking event loop."""
    tasks[task_id]["status"] = "processing"
    tasks[task_id]["progress"] = 0
    await broadcast(task_id, 0, "processing", "处理中...")

    loop = asyncio.get_event_loop()
    output_path, error = await loop.run_in_executor(
        None, _process_effect_sync, task_id, input_path, effect, intensity
    )

    if error:
        tasks[task_id]["status"] = "error"
        tasks[task_id]["error"] = error
        await broadcast(task_id, tasks[task_id].get("progress", 0), "error", f"处理出错: {error}")
        return

    tasks[task_id]["status"] = "done"
    tasks[task_id]["progress"] = 100
    tasks[task_id]["output"] = output_path
    await broadcast(task_id, 100, "done", "处理完成！")


async def process_extend(task_id: str, input_path: str, mode: str, extra_param: float = 2.0):
    """Orchestrate extend processing."""
    tasks[task_id]["status"] = "processing"
    tasks[task_id]["progress"] = 5
    await broadcast(task_id, 5, "processing", "分析视频...")

    loop = asyncio.get_event_loop()
    output_path = str(OUTPUT_DIR / f"{task_id}.mp4")

    try:
        info = await loop.run_in_executor(None, get_video_info, input_path)
        tasks[task_id]["progress"] = 10
        await broadcast(task_id, 10, "processing", "视频分析完成，开始处理...")

        dispatch = {
            "loop_smooth":   lambda: _extend_loop_smooth(input_path, output_path, info),
            "ping_pong":     lambda: _extend_ping_pong(input_path, output_path),
            "slow_motion":   lambda: _extend_slow_motion(input_path, output_path, info, extra_param),
            "reverse":       lambda: _extend_reverse(input_path, output_path),
            "speed_ramp":    lambda: _extend_speed_ramp(input_path, output_path, info),
            "freeze_frame":  lambda: _extend_freeze(input_path, output_path, info, extra_param),
            "extend_repeat": lambda: _extend_repeat(input_path, output_path, extra_param),
            "time_slice":    lambda: _extend_time_slice(input_path, output_path, info),
        }

        sync_fn = dispatch.get(mode, dispatch["loop_smooth"])
        ok, err = await loop.run_in_executor(None, sync_fn)

        if not ok:
            tasks[task_id]["status"] = "error"
            tasks[task_id]["error"] = err
            await broadcast(task_id, tasks[task_id].get("progress", 10), "error", f"处理出错: {err}")
            return

    except Exception as e:
        tasks[task_id]["status"] = "error"
        tasks[task_id]["error"] = str(e)
        await broadcast(task_id, 10, "error", f"处理出错: {e}")
        return

    tasks[task_id]["status"] = "done"
    tasks[task_id]["progress"] = 100
    tasks[task_id]["output"] = output_path
    await broadcast(task_id, 100, "done", "扩展完成！")


# ── Synchronous extend functions ───────────────────────────────

def _extend_loop_smooth(inp, out, info) -> tuple[bool, str]:
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
    return _run_ffmpeg_sync(cmd)


def _extend_ping_pong(inp, out) -> tuple[bool, str]:
    cmd = [
        "ffmpeg", "-y", "-i", inp,
        "-filter_complex",
        "[0]split[fwd][tmp];[tmp]reverse[rev];[fwd][rev]concat=n=2:v=1:a=0",
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-pix_fmt", "yuv420p", out
    ]
    return _run_ffmpeg_sync(cmd)


def _extend_slow_motion(inp, out, info, factor=2.0) -> tuple[bool, str]:
    factor = max(2, min(8, int(factor)))
    new_fps = info["fps"] * factor
    cmd = [
        "ffmpeg", "-y", "-i", inp,
        "-filter_complex", f"minterpolate=fps={new_fps}:mi_mode=blend",
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-pix_fmt", "yuv420p", out
    ]
    ok, err = _run_ffmpeg_sync(cmd)
    if not ok:
        # Fallback
        cmd = [
            "ffmpeg", "-y", "-i", inp,
            "-filter_complex", f"setpts={factor}*PTS",
            "-c:v", "libx264", "-preset", "fast", "-crf", "23",
            "-pix_fmt", "yuv420p", out
        ]
        return _run_ffmpeg_sync(cmd)
    return ok, err


def _extend_reverse(inp, out) -> tuple[bool, str]:
    cmd = [
        "ffmpeg", "-y", "-i", inp,
        "-vf", "reverse", "-af", "areverse",
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-pix_fmt", "yuv420p", out
    ]
    return _run_ffmpeg_sync(cmd)


def _extend_speed_ramp(inp, out, info) -> tuple[bool, str]:
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
    return _run_ffmpeg_sync(cmd)


def _extend_freeze(inp, out, info, freeze_sec=3.0) -> tuple[bool, str]:
    freeze_sec = max(1, min(10, int(freeze_sec)))
    last_t = max(0, info["duration"] - 0.04)
    cmd = [
        "ffmpeg", "-y", "-i", inp,
        "-filter_complex",
        f"[0]split[vid][still];"
        f"[still]trim=start={last_t},setpts=PTS-STARTPTS,loop=loop=-1:size=2:start=0[frz];"
        f"[frz]fade=t=out:st={freeze_sec-1}:d=1[frzf];"
        f"[vid][frzf]concat=n=2:v=1:a=0",
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-pix_fmt", "yuv420p", out
    ]
    return _run_ffmpeg_sync(cmd)


def _extend_repeat(inp, out, times=2.0) -> tuple[bool, str]:
    times = max(2, min(10, int(times)))
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
    return _run_ffmpeg_sync(cmd)


def _extend_time_slice(inp, out, info) -> tuple[bool, str]:
    n_slices = 6
    timestamps = [i * info["duration"] / n_slices for i in range(n_slices)]
    temp_dir = OUTPUT_DIR / f"ts_{uuid.uuid4().hex[:8]}"
    temp_dir.mkdir(exist_ok=True)

    try:
        for i, ts in enumerate(timestamps):
            cmd = [
                "ffmpeg", "-y", "-ss", str(ts), "-i", inp,
                "-frames:v", "1", str(temp_dir / f"slice_{i:02d}.png")
            ]
            _run_ffmpeg(cmd, timeout=30)

        cmd = [
            "ffmpeg", "-y",
            "-i", str(temp_dir / "slice_%02d.png"),
            "-filter_complex", "tile=3x2",
            "-c:v", "libx264", "-preset", "fast", "-crf", "23",
            "-pix_fmt", "yuv420p", out
        ]
        return _run_ffmpeg_sync(cmd)
    finally:
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

    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(400, f"文件过大（{len(content)/1024/1024:.0f}MB），最大支持 500MB")

    file_id = str(uuid.uuid4())[:8]
    save_path = UPLOAD_DIR / f"{file_id}{ext}"
    with open(save_path, "wb") as f:
        f.write(content)

    info = get_video_info(str(save_path))
    return {"file_id": file_id, "filename": file.filename, "info": info}


@app.post("/api/process/effect")
async def start_effect(file_id: str = Form(...), effect: str = Form(...), intensity: float = Form(0.5)):
    """Start applying an effect."""
    if effect not in EFFECTS:
        raise HTTPException(400, f"未知特效: {effect}")
    intensity = max(0.1, min(1.0, intensity))

    inp = _find_input(file_id)
    if not inp:
        raise HTTPException(404, "找不到上传的文件")

    task_id = str(uuid.uuid4())[:8]
    tasks[task_id] = {
        "type": "effect", "mode": effect, "file_id": file_id,
        "intensity": intensity, "status": "queued", "progress": 0,
    }
    asyncio.create_task(process_effect(task_id, str(inp), effect, intensity))
    return {"task_id": task_id, "effect": effect}


@app.post("/api/process/extend")
async def start_extend(file_id: str = Form(...), mode: str = Form(...), param: float = Form(2.0)):
    """Start video extension."""
    if mode not in EXTEND_MODES:
        raise HTTPException(400, f"未知模式: {mode}")

    mode_cfg = EXTEND_MODES[mode]
    if mode_cfg.get("has_param"):
        param = max(mode_cfg.get("param_min", 1), min(mode_cfg.get("param_max", 10), param))

    inp = _find_input(file_id)
    if not inp:
        raise HTTPException(404, "找不到上传的文件")

    task_id = str(uuid.uuid4())[:8]
    tasks[task_id] = {
        "type": "extend", "mode": mode, "file_id": file_id,
        "param": param, "status": "queued", "progress": 0,
    }
    asyncio.create_task(process_extend(task_id, str(inp), mode, param))
    return {"task_id": task_id, "mode": mode}


@app.get("/api/task/{task_id}")
async def get_task(task_id: str):
    """Get task status (safe subset)."""
    if task_id not in tasks:
        raise HTTPException(404, "任务不存在")
    t = tasks[task_id]
    return {
        "task_id": task_id, "type": t.get("type"), "mode": t.get("mode"),
        "file_id": t.get("file_id"), "status": t.get("status"),
        "progress": t.get("progress", 0), "error": t.get("error"),
    }


@app.get("/api/download/{task_id}")
async def download(task_id: str):
    """Download processed video."""
    if task_id not in tasks or tasks[task_id]["status"] != "done":
        raise HTTPException(404, "文件未就绪")
    path = tasks[task_id]["output"]
    return FileResponse(path, media_type="video/mp4", filename=f"ai_video_{task_id}.mp4")


@app.post("/api/import-result")
async def import_result(task_id: str = Form(...)):
    """Import a processed result as a new editable source (for 'continue editing')."""
    if task_id not in tasks or tasks[task_id]["status"] != "done":
        raise HTTPException(404, "结果文件未就绪")

    src_path = tasks[task_id]["output"]
    if not os.path.exists(src_path):
        raise HTTPException(404, "结果文件不存在")

    # Copy to uploads as new file_id
    new_file_id = str(uuid.uuid4())[:8]
    ext = Path(src_path).suffix or ".mp4"
    dst_path = UPLOAD_DIR / f"{new_file_id}{ext}"
    shutil.copy2(src_path, dst_path)

    info = get_video_info(str(dst_path))
    return {"file_id": new_file_id, "info": info}


@app.get("/api/preview/{file_id}")
async def preview(file_id: str):
    """Stream uploaded video for preview."""
    inp = _find_input(file_id)
    if not inp:
        raise HTTPException(404)
    return FileResponse(str(inp))


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    ws_clients.append(ws)
    try:
        while True:
            msg = await ws.receive_text()
            try:
                req = json.loads(msg)
                if req.get("action") == "query_task" and req.get("task_id"):
                    tid = req["task_id"]
                    if tid in tasks:
                        t = tasks[tid]
                        await ws.send_text(json.dumps({
                            "task_id": tid,
                            "progress": t.get("progress", 0),
                            "status": t["status"],
                            "message": t.get("error", ""),
                        }))
            except (json.JSONDecodeError, Exception):
                pass
    except WebSocketDisconnect:
        pass
    finally:
        if ws in ws_clients:
            ws_clients.remove(ws)


# ── Startup cleanup ────────────────────────────────────────────
@app.on_event("startup")
async def startup():
    now = time.time()
    for d in [UPLOAD_DIR, OUTPUT_DIR]:
        for f in d.iterdir():
            if f.is_file() and now - f.stat().st_mtime > CLEANUP_AGE:
                try:
                    f.unlink()
                except OSError:
                    pass


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8888)
