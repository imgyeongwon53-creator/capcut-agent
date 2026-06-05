import asyncio
import subprocess
import sys
from datetime import datetime
from typing import Any, Dict

from .config import CAPCUT_DRAFT_FOLDER, DRAFT_WIDTH, DRAFT_HEIGHT, DRAFT_FPS, UPLOAD_DIR


def _subprocess_kwargs() -> dict:
    kwargs = {}
    if sys.platform == "win32":
        kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
    return kwargs


def generate_black_bg(output_path: str, duration: int) -> None:
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


def _build_script_draft_sync(script: Dict[str, Any], stem: str) -> str:
    from pycapcut import Draft, VideoMaterial, VideoSegment, TextSegment, TextStyle, trange, SEC  # type: ignore

    total_duration = int(script.get("total_duration", 300))
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

    # Full background track
    draft.add_segment(VideoSegment(
        mat,
        trange=trange(0, mat_duration),
        source_timerange=trange(0, mat_duration),
    ))

    white = TextStyle(color=(1.0, 1.0, 1.0), bold=True, border_color=(0.0, 0.0, 0.0))
    green = TextStyle(color=(0.133, 0.773, 0.369), bold=True, border_color=(0.0, 0.0, 0.0))  # #22c55e

    # Title card: 0 ~ 4s
    draft.add_segment(TextSegment(
        text=title,
        trange=trange(0, 4 * SEC),
        style=white,
        transform_y=0.0,
    ))

    cursor = 4.0  # seconds

    for section in sections:
        heading = section.get("heading", "")
        duration = float(section.get("duration_seconds", 60))
        key_points = section.get("key_points", [])

        # Section heading: first 3s of section
        heading_dur = min(3 * SEC, int(duration * SEC))
        draft.add_segment(TextSegment(
            text=heading,
            trange=trange(int(cursor * SEC), heading_dur),
            style=green,
            transform_y=0.0,
        ))

        # Key points evenly spread across section
        if key_points:
            pt_dur = duration / len(key_points)
            for i, point in enumerate(key_points):
                pt_start = cursor + i * pt_dur
                draft.add_segment(TextSegment(
                    text=f"• {point}",
                    trange=trange(int(pt_start * SEC), int(pt_dur * SEC)),
                    style=TextStyle(color=(1.0, 1.0, 1.0), border_color=(0.0, 0.0, 0.0)),
                    transform_y=-0.8,  # TRAP 4: bottom
                ))

        cursor += duration

    draft.save()
    return draft_name


async def build_script_draft(script: Dict[str, Any], stem: str) -> str:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _build_script_draft_sync, script, stem)
