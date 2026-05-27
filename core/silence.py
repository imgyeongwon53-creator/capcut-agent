import re
import subprocess
import sys
from typing import List, Tuple

from .config import SILENCE_NOISE_DB, SILENCE_MIN_DURATION, SILENCE_PADDING


def _subprocess_kwargs() -> dict:
    kwargs = {}
    if sys.platform == "win32":
        kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
    return kwargs


def get_duration(video_path: str) -> float:
    cmd = [
        "ffprobe", "-v", "quiet",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        video_path,
    ]
    result = subprocess.run(
        cmd, capture_output=True, encoding="utf-8", errors="replace",
        **_subprocess_kwargs()
    )
    duration_str = result.stdout.strip()
    if not duration_str:
        # TRAP 7: fallback to stream duration
        cmd2 = [
            "ffprobe", "-v", "quiet",
            "-show_entries", "stream=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            video_path,
        ]
        result2 = subprocess.run(
            cmd2, capture_output=True, encoding="utf-8", errors="replace",
            **_subprocess_kwargs()
        )
        duration_str = result2.stdout.strip().split("\n")[0]
    return float(duration_str) if duration_str else 0.0


def detect_silence(video_path: str) -> List[Tuple[float, float]]:
    cmd = [
        "ffmpeg", "-i", video_path,
        "-af", f"silencedetect=noise={SILENCE_NOISE_DB}dB:d={SILENCE_MIN_DURATION}",
        "-f", "null", "-",
    ]
    result = subprocess.run(
        cmd, capture_output=True, encoding="utf-8", errors="replace",
        **_subprocess_kwargs()
    )
    output = result.stderr

    starts = re.findall(r"silence_start: ([0-9.]+)", output)
    ends = re.findall(r"silence_end: ([0-9.]+)", output)

    silences = [(float(s), float(e)) for s, e in zip(starts, ends)]

    # Trailing silence with no silence_end
    if len(starts) > len(ends):
        duration = get_duration(video_path)
        silences.append((float(starts[-1]), duration))

    return silences


def compute_keep_segments(
    silences: List[Tuple[float, float]], duration: float
) -> List[Tuple[float, float]]:
    if not silences:
        return [(0.0, duration)]

    keeps = []
    prev_end = 0.0

    for s_start, s_end in silences:
        if s_start > prev_end:
            keeps.append((
                max(0.0, prev_end - SILENCE_PADDING),
                min(duration, s_start + SILENCE_PADDING),
            ))
        prev_end = s_end

    if prev_end < duration:
        keeps.append((max(0.0, prev_end - SILENCE_PADDING), duration))

    # Merge overlapping
    merged: List[List[float]] = []
    for s, e in sorted(keeps):
        if merged and s <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], e)
        else:
            merged.append([s, e])

    return [(s, e) for s, e in merged]
