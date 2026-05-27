import os
import sys
from pathlib import Path

UPLOAD_DIR = Path("uploads")
CACHE_DIR = Path("cache")
DRAFT_DIR = Path("drafts")

for _d in (UPLOAD_DIR, CACHE_DIR, DRAFT_DIR):
    _d.mkdir(exist_ok=True)


def _detect_capcut_folder() -> Path:
    if sys.platform == "win32":
        local = os.environ.get("LOCALAPPDATA", "")
        p = Path(local) / "CapCut" / "User Data" / "Projects" / "com.lveditor.draft"
        if p.exists():
            return p
    elif sys.platform == "darwin":
        p = Path.home() / "Movies" / "CapCut" / "User Data" / "Projects" / "com.lveditor.draft"
        if p.exists():
            return p
    return DRAFT_DIR


CAPCUT_DRAFT_FOLDER = Path(os.environ.get("CAPCUT_DRAFT_FOLDER", str(_detect_capcut_folder())))

SILENCE_NOISE_DB = float(os.environ.get("SILENCE_NOISE_DB", "-35"))
SILENCE_MIN_DURATION = float(os.environ.get("SILENCE_MIN_DURATION", "0.5"))
SILENCE_PADDING = 0.05

WHISPER_MODEL = os.environ.get("WHISPER_MODEL", "large-v3")
WHISPER_LANGUAGE = os.environ.get("WHISPER_LANGUAGE", "ko")

DRAFT_WIDTH = 1920
DRAFT_HEIGHT = 1080
DRAFT_FPS = 30

FILLER_WORDS = {
    "어", "음", "그", "아", "에", "이", "뭐", "저", "이제",
    "그니까", "그러니까", "뭐냐", "뭐지", "아니", "근데",
    "약간", "진짜", "막", "좀", "되게", "엄청",
}

FILLER_PROBABILITY_THRESHOLD = 0.85
NG_MATCH_CHARS = 10
CUT_MERGE_GAP = 0.05
