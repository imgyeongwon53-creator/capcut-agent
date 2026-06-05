import asyncio
import re
import subprocess
import sys
from datetime import datetime
from typing import Any, Dict, List

from .config import CAPCUT_DRAFT_FOLDER, DRAFT_WIDTH, DRAFT_HEIGHT, DRAFT_FPS, UPLOAD_DIR


def _subprocess_kwargs() -> dict:
    kwargs = {}
    if sys.platform == "win32":
        kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
    return kwargs


def generate_black_bg(output_path: str, duration: float) -> None:
    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi",
        "-i", f"color=c=black:s={DRAFT_WIDTH}x{DRAFT_HEIGHT}:r=1",
        "-t", str(max(duration, 1)),
        "-c:v", "libx264",
        "-preset", "ultrafast",
        "-tune", "stillimage",
        "-pix_fmt", "yuv420p",
        output_path,
    ]
    subprocess.run(
        cmd, capture_output=True, encoding="utf-8", errors="replace",
        **_subprocess_kwargs()
    )


def _split_subtitle_lines(text: str, max_chars: int = 22) -> List[str]:
    """Split script text into subtitle-sized Korean lines."""
    raw = re.split(r'[\n。.!?]+', text.strip())
    lines: List[str] = []
    for part in raw:
        part = part.strip()
        if not part:
            continue
        if len(part) <= max_chars:
            lines.append(part)
        else:
            # Break on commas or by length
            subs = re.split(r'[,，、]', part)
            for s in subs:
                s = s.strip()
                if s:
                    lines.append(s[:max_chars])
    return lines if lines else ([text[:max_chars]] if text.strip() else [])


def _build_script_draft_sync(script: Dict[str, Any], stem: str) -> str:
    from pycapcut import Draft, VideoMaterial, VideoSegment, TextSegment, TextStyle, trange, SEC  # type: ignore

    total_duration = float(script.get("total_duration", 300))
    sections = script.get("sections", [])
    title = script.get("title", "스크립트 영상")

    bg_path = str(UPLOAD_DIR / f"bg_{stem}.mp4")
    generate_black_bg(bg_path, total_duration + 5)

    # TRAP 6: unique draft name
    draft_name = f"script_{stem}_{datetime.now().strftime('%H%M%S')}"
    draft = Draft(
        draft_name,
        width=DRAFT_WIDTH,
        height=DRAFT_HEIGHT,
        fps=DRAFT_FPS,
        draft_folder=str(CAPCUT_DRAFT_FOLDER),
    )

    mat = VideoMaterial(bg_path)
    mat_duration = mat.duration

    draft.add_segment(VideoSegment(
        mat,
        trange=trange(0, mat_duration),
        source_timerange=trange(0, mat_duration),
    ))

    white_bold = TextStyle(color=(1.0, 1.0, 1.0), bold=True, border_color=(0.0, 0.0, 0.0))
    green_bold = TextStyle(color=(0.133, 0.773, 0.369), bold=True, border_color=(0.0, 0.0, 0.0))
    white_sub  = TextStyle(color=(1.0, 1.0, 1.0), border_color=(0.0, 0.0, 0.0))

    # Title card — adaptive duration (10% of total, max 4s)
    title_dur_s = min(4.0, max(1.0, total_duration * 0.1))
    draft.add_segment(TextSegment(
        text=title,
        trange=trange(0, int(title_dur_s * SEC)),
        style=white_bold,
        transform_y=0.0,
    ))

    cursor = title_dur_s

    for section in sections:
        heading    = section.get("heading", "")
        duration   = float(section.get("duration_seconds", 60))
        key_points = section.get("key_points", [])
        script_text = section.get("script", "").strip()

        if duration <= 0:
            continue

        # ── Section heading: upper area, first 20% of section (max 3s)
        heading_dur_s = min(3.0, max(0.5, duration * 0.2))
        draft.add_segment(TextSegment(
            text=heading,
            trange=trange(int(cursor * SEC), int(heading_dur_s * SEC)),
            style=green_bold,
            transform_y=0.7,   # top area (negative=down, positive=up)
        ))

        # ── Key points: center, evenly spread
        if key_points:
            pt_dur = duration / len(key_points)
            for i, point in enumerate(key_points):
                pt_start = cursor + i * pt_dur
                draft.add_segment(TextSegment(
                    text=f"• {point}",
                    trange=trange(int(pt_start * SEC), int(pt_dur * SEC)),
                    style=TextStyle(color=(0.9, 0.9, 0.9), border_color=(0.0, 0.0, 0.0)),
                    transform_y=0.0,   # center
                ))

        # ── 한글 자막: script text split into lines, bottom
        lines = _split_subtitle_lines(script_text)
        if lines:
            line_dur = duration / len(lines)
            for i, line in enumerate(lines):
                line_start = cursor + i * line_dur
                draft.add_segment(TextSegment(
                    text=line,
                    trange=trange(int(line_start * SEC), int(line_dur * SEC)),
                    style=white_sub,
                    transform_y=-0.8,   # TRAP 4: bottom subtitle position
                ))

        cursor += duration

    draft.save()
    return draft_name


async def build_script_draft(script: Dict[str, Any], stem: str) -> str:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _build_script_draft_sync, script, stem)
