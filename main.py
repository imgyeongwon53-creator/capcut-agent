import asyncio
import hashlib
import json
import os
import re
import subprocess
import sys
import uuid
from pathlib import Path
from typing import Any, Dict

from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse

from core.config import CAPCUT_DRAFT_FOLDER, UPLOAD_DIR
from core.silence import compute_keep_segments, detect_silence, get_duration
from core.asr import transcribe
from core.filler import compute_final_keeps
from core.draft_builder import build_draft
from core.text_draft_builder import build_script_draft

app = FastAPI(title="CapCut Agent")

# TRAP 3: CORS for file:// protocol access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_uploads: Dict[str, Dict[str, Any]] = {}
_autovideo_jobs: Dict[str, Dict[str, Any]] = {}
_generated: Dict[str, str] = {}  # file_id → output path


@app.get("/")
async def index():
    return FileResponse("static/index.html")


@app.post("/upload")
async def upload(file: UploadFile = File(...)):
    suffix = Path(file.filename).suffix.lower()
    if suffix not in (".mp4", ".mov"):
        raise HTTPException(400, "mp4 또는 mov 파일만 업로드할 수 있습니다.")

    file_id = str(uuid.uuid4())
    dest_path = UPLOAD_DIR / f"{file_id}{suffix}"

    # TRAP 2: chunked read to avoid blocking event loop + memory overflow
    hasher = hashlib.sha256()
    with open(dest_path, "wb") as f:
        while chunk := await file.read(1024 * 1024):
            f.write(chunk)
            hasher.update(chunk)

    _uploads[file_id] = {
        "path": str(dest_path),
        "filename": file.filename,
        "stem": Path(file.filename).stem,
        "hash": hasher.hexdigest(),
    }
    return {"file_id": file_id, "filename": file.filename}


@app.get("/process/{file_id}")
async def process(file_id: str):
    if file_id not in _uploads:
        raise HTTPException(404, "파일을 찾을 수 없습니다.")

    async def event_stream():
        info = _uploads[file_id]
        video_path = info["path"]
        stem = info["stem"]

        def sse(stage: str, status: str, **kwargs) -> str:
            return f"data: {json.dumps({'stage': stage, 'status': status, **kwargs}, ensure_ascii=False)}\n\n"

        try:
            # Stage 1: Silence detection
            yield sse("silence", "start")
            loop = asyncio.get_event_loop()
            duration = await loop.run_in_executor(None, get_duration, video_path)
            silences = await loop.run_in_executor(None, detect_silence, video_path)
            keeps = compute_keep_segments(silences, duration)
            yield sse("silence", "done",
                      duration=round(duration, 2),
                      silence_count=len(silences),
                      keep_count=len(keeps))

            # Stage 2: ASR
            yield sse("asr", "start")
            segments = await transcribe(video_path)
            yield sse("asr", "done", segment_count=len(segments))

            # Stage 3: Filler/NG detection
            yield sse("filler", "start")
            final_keeps, cuts = compute_final_keeps(keeps, segments)
            yield sse("filler", "done",
                      cut_count=len(cuts),
                      keep_count=len(final_keeps))

            # Stage 4: Draft generation
            yield sse("draft", "start")
            draft_name = await build_draft(video_path, final_keeps, segments, stem)

            edited_duration = sum(e - s for s, e in final_keeps)
            reduction = (1 - edited_duration / duration) * 100 if duration > 0 else 0

            yield sse(
                "draft", "done",
                draft_name=draft_name,
                original_duration=round(duration, 2),
                edited_duration=round(edited_duration, 2),
                clip_count=len(final_keeps),
                reduction_percent=round(reduction, 1),
                cuts=[{"start": round(s, 3), "end": round(e, 3)} for s, e in cuts],
                transcript=[
                    {"start": round(sg["start"], 2),
                     "end": round(sg["end"], 2),
                     "text": sg["text"]}
                    for sg in segments
                ],
            )

        except Exception as exc:
            yield sse("error", "error", message=str(exc))

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.get("/video/{file_id}")
async def video(file_id: str):
    if file_id not in _uploads:
        raise HTTPException(404, "파일을 찾을 수 없습니다.")
    return FileResponse(_uploads[file_id]["path"])


@app.post("/autovideo/start")
async def autovideo_start(request: Request):
    body = await request.json()
    topic = (body.get("topic") or "").strip()
    if not topic:
        raise HTTPException(400, "topic이 필요합니다.")
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise HTTPException(400, "ANTHROPIC_API_KEY 환경변수가 설정되지 않았습니다.")
    job_id = str(uuid.uuid4())
    _autovideo_jobs[job_id] = {
        "topic": topic,
        "duration_minutes": float(body.get("duration_minutes", 5)),
        "num_sections": int(body.get("num_sections", 3)),
    }
    return {"job_id": job_id}


@app.get("/autovideo/stream/{job_id}")
async def autovideo_stream(job_id: str):
    if job_id not in _autovideo_jobs:
        raise HTTPException(404, "작업을 찾을 수 없습니다.")
    params = _autovideo_jobs.pop(job_id)

    queue: asyncio.Queue = asyncio.Queue()

    def sse(stage: str, status: str, **kwargs) -> str:
        return f"data: {json.dumps({'stage': stage, 'status': status, **kwargs}, ensure_ascii=False)}\n\n"

    async def run_pipeline():
        try:
            from core.script_generator_claude import generate_script
            from core.video_generator import generate_video

            # Step 1: Script
            await queue.put(sse("script", "start"))
            loop = asyncio.get_event_loop()
            script = await loop.run_in_executor(
                None, generate_script,
                params["topic"], params["duration_minutes"], params["num_sections"]
            )
            await queue.put(sse("script", "done",
                               title=script.get("title", params["topic"]),
                               sections=len(script.get("sections", []))))

            # Step 2-4: TTS + audio concat + render (progress via on_progress)
            async def on_progress(stage: str, status: str, data: dict):
                await queue.put(sse(stage, status, **data))

            output_path = await generate_video(script, on_progress=on_progress)

            file_id = str(uuid.uuid4())
            _generated[file_id] = output_path
            await queue.put(sse("done", "done",
                               file_id=file_id,
                               title=script.get("title", params["topic"]),
                               script=script))
        except Exception as exc:
            await queue.put(sse("error", "error", message=str(exc)))
        finally:
            await queue.put(None)

    async def event_stream():
        asyncio.create_task(run_pipeline())
        while True:
            item = await queue.get()
            if item is None:
                break
            yield item

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.get("/autovideo/download/{file_id}")
async def autovideo_download(file_id: str):
    if file_id not in _generated:
        raise HTTPException(404, "파일을 찾을 수 없습니다.")
    path = _generated[file_id]
    filename = Path(path).name
    return FileResponse(path, media_type="video/mp4", filename=filename)


@app.get("/script/capabilities")
async def script_capabilities():
    has_key = bool(os.environ.get("ANTHROPIC_API_KEY", ""))
    return {"claude": has_key}


@app.post("/script/generate")
async def script_generate(request: Request):
    body = await request.json()
    topic = (body.get("topic") or "").strip()
    if not topic:
        raise HTTPException(400, "topic이 필요합니다.")
    duration_minutes = float(body.get("duration_minutes", 5))
    num_sections = int(body.get("num_sections", 3))

    from core.script_generator_claude import generate_script
    loop = asyncio.get_event_loop()
    try:
        script = await loop.run_in_executor(
            None, generate_script, topic, duration_minutes, num_sections
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    return script


@app.post("/script/draft")
async def script_draft(request: Request):
    body = await request.json()
    script = body.get("script")
    if not script:
        raise HTTPException(400, "script가 필요합니다.")
    stem = re.sub(r"[^\w가-힣]", "_", script.get("topic", "script"))[:32]
    draft_name = await build_script_draft(script, stem)
    return {"draft_name": draft_name}


@app.get("/config")
async def config():
    return {
        "draft_folder": str(CAPCUT_DRAFT_FOLDER),
        "exists": CAPCUT_DRAFT_FOLDER.exists(),
    }


@app.post("/open-capcut")
async def open_capcut(request: Request):
    body = await request.json() if request.headers.get("content-type") == "application/json" else {}
    kwargs: dict = {}
    if sys.platform == "win32":
        kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW

    try:
        if sys.platform == "win32":
            capcut_exe = (
                Path(os.environ.get("LOCALAPPDATA", "")) / "CapCut" / "Apps" / "CapCut.exe"
            )
            if capcut_exe.exists():
                subprocess.Popen([str(capcut_exe)], **kwargs)
            else:
                os.startfile(str(CAPCUT_DRAFT_FOLDER))
        elif sys.platform == "darwin":
            subprocess.Popen(["open", "-a", "CapCut"], **kwargs)
        else:
            subprocess.Popen(["xdg-open", str(CAPCUT_DRAFT_FOLDER)], **kwargs)
        return {"status": "ok"}
    except Exception as exc:
        return {"status": "error", "message": str(exc)}
