import asyncio
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from .config import DRAFT_WIDTH, DRAFT_HEIGHT, DRAFT_FPS, UPLOAD_DIR


def _sp_kwargs() -> dict:
    return {"creationflags": subprocess.CREATE_NO_WINDOW} if sys.platform == "win32" else {}


def _korean_font() -> str:
    if sys.platform == "win32":
        return "Malgun Gothic"
    elif sys.platform == "darwin":
        return "AppleGothic"
    return "DejaVu Sans"


def _audio_duration(path: str) -> float:
    res = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", path],
        capture_output=True, text=True, **_sp_kwargs()
    )
    try:
        return float(res.stdout.strip())
    except ValueError:
        return 0.0


def _srt_ts(secs: float) -> str:
    h = int(secs // 3600)
    m = int((secs % 3600) // 60)
    s = int(secs % 60)
    ms = int((secs % 1) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def _build_srt(items: List[Dict]) -> str:
    lines: List[str] = []
    idx = 1
    for item in items:
        text = item["script"]
        start = item["start"]
        end = item["end"]
        # split into sentence-sized chunks
        sentences = [s.strip() for s in re.split(r'(?<=[.!?。,，])\s*', text) if s.strip()]
        if not sentences:
            sentences = [text]
        chunk_dur = (end - start) / len(sentences)
        for j, sentence in enumerate(sentences):
            t0 = start + j * chunk_dur
            t1 = t0 + chunk_dur
            lines += [str(idx), f"{_srt_ts(t0)} --> {_srt_ts(t1)}", sentence, ""]
            idx += 1
    return "\n".join(lines)


def _ffmpeg_srt_path(p: Path) -> str:
    """Return srt path escaped for ffmpeg subtitle filter."""
    s = str(p).replace("\\", "/")
    # Escape colon in Windows drive letter  C:/... → C\:/...
    if len(s) > 1 and s[1] == ":":
        s = s[0] + "\\:" + s[2:]
    return s


async def _tts(text: str, out_path: str, voice: str = "ko-KR-SunHiNeural") -> None:
    import edge_tts
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(out_path)


async def generate_video(
    script: Dict[str, Any],
    on_progress: Optional[Callable] = None,
) -> str:
    """Generate an mp4 from a script. Returns the output file path."""

    sections = script.get("sections", [])
    stem = re.sub(r"[^\w가-힣]", "_", script.get("topic", "video"))[:24]
    tag = datetime.now().strftime("%H%M%S")
    output_path = UPLOAD_DIR / f"gen_{stem}_{tag}.mp4"
    tmp_prefix = UPLOAD_DIR / f"tmp_{tag}"

    loop = asyncio.get_event_loop()

    async def progress(stage: str, status: str, **kwargs):
        if on_progress:
            await on_progress(stage, status, kwargs)

    try:
        # ── Stage 1: TTS ────────────────────────────────────────────────────
        await progress("tts", "start")
        audio_files: List[tuple] = []
        for i, section in enumerate(sections):
            text = section.get("script", "").strip()
            if not text:
                continue
            audio_path = str(tmp_prefix) + f"_sec{i}.mp3"
            await _tts(text, audio_path)
            audio_files.append((audio_path, section))
        await progress("tts", "done", count=len(audio_files))

        if not audio_files:
            raise ValueError("TTS로 변환할 스크립트가 없습니다.")

        # ── Stage 2: Concat audio ────────────────────────────────────────────
        await progress("audio", "start")
        concat_txt = str(tmp_prefix) + "_concat.txt"
        with open(concat_txt, "w", encoding="utf-8") as f:
            for ap, _ in audio_files:
                f.write(f"file '{ap}'\n")

        combined = str(tmp_prefix) + "_combined.mp3"
        await loop.run_in_executor(None, lambda: subprocess.run(
            ["ffmpeg", "-y", "-f", "concat", "-safe", "0",
             "-i", concat_txt, "-c", "copy", combined],
            capture_output=True, check=True, **_sp_kwargs()
        ))

        cursor = 0.0
        timed_sections: List[Dict] = []
        for ap, section in audio_files:
            dur = await loop.run_in_executor(None, _audio_duration, ap)
            timed_sections.append({"script": section.get("script", ""), "start": cursor, "end": cursor + dur})
            cursor += dur
        total_dur = cursor
        await progress("audio", "done", duration=round(total_dur, 1))

        # ── Stage 3: Render ─────────────────────────────────────────────────
        await progress("render", "start")

        srt_path = Path(str(tmp_prefix) + "_subs.srt")
        srt_path.write_text(_build_srt(timed_sections), encoding="utf-8-sig")

        sub_filter = (
            f"subtitles='{_ffmpeg_srt_path(srt_path)}':"
            f"force_style='FontName={_korean_font()},FontSize=26,"
            f"PrimaryColour=&H00FFFFFF&,OutlineColour=&H00000000&,"
            f"Outline=2,Alignment=2,MarginV=40'"
        )

        base_cmd = [
            "ffmpeg", "-y",
            "-f", "lavfi",
            "-i", f"color=c=black:s={DRAFT_WIDTH}x{DRAFT_HEIGHT}:r={DRAFT_FPS}:d={total_dur + 1}",
            "-i", combined,
            "-c:v", "libx264", "-preset", "fast", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-shortest",
        ]

        result = await loop.run_in_executor(None, lambda: subprocess.run(
            base_cmd[:8] + ["-vf", sub_filter] + base_cmd[8:] + [str(output_path)],
            capture_output=True, **_sp_kwargs()
        ))

        if result.returncode != 0:
            # Subtitle rendering failed → fallback without subtitles
            await loop.run_in_executor(None, lambda: subprocess.run(
                base_cmd + [str(output_path)],
                capture_output=True, check=True, **_sp_kwargs()
            ))

        await progress("render", "done")
        return str(output_path)

    finally:
        # Clean up temp files
        for p in UPLOAD_DIR.glob(f"tmp_{tag}_*"):
            try:
                p.unlink()
            except OSError:
                pass
