import asyncio
import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List

from .config import CACHE_DIR, WHISPER_MODEL, WHISPER_LANGUAGE

_model = None
_model_lock = asyncio.Lock()


def _get_model():
    global _model
    if _model is None:
        from faster_whisper import WhisperModel
        # TRAP 1: force CPU — device="auto" crashes on Windows without full CUDA toolkit
        _model = WhisperModel(WHISPER_MODEL, device="cpu", compute_type="int8")
    return _model


def _file_hash(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _transcribe_sync(video_path: str) -> List[Dict[str, Any]]:
    model = _get_model()
    segments_iter, _ = model.transcribe(
        video_path,
        word_timestamps=True,
        vad_filter=True,
        language=WHISPER_LANGUAGE,
    )
    result = []
    for seg in segments_iter:
        words = []
        if seg.words:
            for w in seg.words:
                words.append({
                    "word": w.word,
                    "start": w.start,
                    "end": w.end,
                    "probability": w.probability,
                })
        result.append({
            "start": seg.start,
            "end": seg.end,
            "text": seg.text.strip(),
            "words": words,
        })
    return result


async def transcribe(video_path: str) -> List[Dict[str, Any]]:
    file_hash = _file_hash(video_path)
    cache_path = CACHE_DIR / f"{file_hash}.json"

    if cache_path.exists():
        with open(cache_path, "r", encoding="utf-8") as f:
            return json.load(f)

    # TRAP 1: asyncio.Lock prevents concurrent ASR (numba segfault risk)
    async with _model_lock:
        if cache_path.exists():
            with open(cache_path, "r", encoding="utf-8") as f:
                return json.load(f)

        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, _transcribe_sync, video_path)

    with open(cache_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    return result
