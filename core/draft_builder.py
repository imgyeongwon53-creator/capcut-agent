import asyncio
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from .config import CAPCUT_DRAFT_FOLDER, DRAFT_WIDTH, DRAFT_HEIGHT, DRAFT_FPS


def _map_to_timeline(
    t: float, time_map: List[Tuple[float, float, float]]
) -> Optional[float]:
    for orig_start, orig_end, tl_start in time_map:
        if orig_start <= t <= orig_end:
            return tl_start + (t - orig_start)
    return None


def _find_timeline_range(
    start: float,
    end: float,
    time_map: List[Tuple[float, float, float]],
) -> Tuple[Optional[float], Optional[float]]:
    # TRAP 5: clamp subtitle timestamps that fall inside cut regions
    tl_start = _map_to_timeline(start, time_map)
    if tl_start is None:
        for orig_start, orig_end, tl_s in time_map:
            if orig_start >= start:
                tl_start = tl_s
                break

    tl_end = _map_to_timeline(end, time_map)
    if tl_end is None:
        for orig_start, orig_end, tl_s in reversed(time_map):
            if orig_end <= end:
                tl_end = tl_s + (orig_end - orig_start)
                break

    return tl_start, tl_end


def _build_draft_sync(
    video_path: str,
    keeps: List[Tuple[float, float]],
    segments: List[Dict[str, Any]],
    stem: str,
) -> str:
    from pycapcut import DraftFolder, VideoMaterial, VideoSegment, TextSegment, TextStyle, trange, SEC  # type: ignore

    # TRAP 6: unique name to avoid WinError 32 when CapCut has draft folder open
    draft_name = f"auto_{stem}_{datetime.now().strftime('%H%M%S')}"

    folder = DraftFolder(str(CAPCUT_DRAFT_FOLDER))
    draft = folder.create_draft(draft_name, width=DRAFT_WIDTH, height=DRAFT_HEIGHT, fps=DRAFT_FPS)

    mat = VideoMaterial(video_path)
    mat_duration = mat.duration  # microseconds

    time_map: List[Tuple[float, float, float]] = []
    tl_cursor = 0.0  # seconds

    for seg_start, seg_end in keeps:
        src_start_us = int(seg_start * SEC)
        # Clamp to material duration (pyCapCut rule 4)
        src_end_us = min(int(seg_end * SEC), mat_duration)
        if src_end_us <= src_start_us:
            continue

        duration_us = src_end_us - src_start_us
        duration_s = duration_us / SEC

        # pyCapCut rule 2: trange(start, duration) — 2nd arg is duration, NOT end
        video_seg = VideoSegment(
            mat,
            trange=trange(int(tl_cursor * SEC), duration_us),
            source_timerange=trange(src_start_us, duration_us),
        )
        draft.add_segment(video_seg)

        time_map.append((seg_start, seg_end, tl_cursor))
        tl_cursor += duration_s

    # Sentence-level subtitles (one per segment, not word-level)
    for seg in segments:
        tl_start, tl_end = _find_timeline_range(seg["start"], seg["end"], time_map)
        if tl_start is None or tl_end is None or tl_end <= tl_start:
            continue

        # pyCapCut rule 3: color is float 0.0-1.0, not 0-255
        style = TextStyle(
            color=(1.0, 1.0, 1.0),
            bold=True,
            border_color=(0.0, 0.0, 0.0),
        )
        text_seg = TextSegment(
            text=seg["text"],
            trange=trange(int(tl_start * SEC), int((tl_end - tl_start) * SEC)),
            style=style,
            transform_y=-0.8,  # TRAP 4: negative = bottom of screen
        )
        draft.add_segment(text_seg)

    draft.save()
    return draft_name


async def build_draft(
    video_path: str,
    keeps: List[Tuple[float, float]],
    segments: List[Dict[str, Any]],
    stem: str,
) -> str:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None, _build_draft_sync, video_path, keeps, segments, stem
    )
