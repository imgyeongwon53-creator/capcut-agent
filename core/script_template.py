import uuid
from typing import Any, Dict

_TEMPLATES = {
    3: [
        ("도입",   0.20, ["주제 소개", "오늘의 학습 목표", "영상 구성 안내"]),
        ("본론",   0.60, ["핵심 개념 설명", "예시 및 실습", "주요 포인트 정리"]),
        ("마무리", 0.20, ["오늘 배운 내용 요약", "다음 시간 예고", "질문 및 과제"]),
    ],
    4: [
        ("도입",   0.15, ["주제 소개", "학습 목표"]),
        ("본론 1", 0.35, ["핵심 개념 1", "예시 설명", "실습"]),
        ("본론 2", 0.35, ["핵심 개념 2", "심화 내용", "응용"]),
        ("마무리", 0.15, ["요약 정리", "다음 시간 예고"]),
    ],
    5: [
        ("도입",   0.10, ["주제 소개", "학습 목표"]),
        ("본론 1", 0.22, ["개념 1 설명", "예시"]),
        ("본론 2", 0.22, ["개념 2 설명", "예시"]),
        ("본론 3", 0.22, ["개념 3 설명", "실습"]),
        ("마무리", 0.24, ["요약", "다음 시간"]),
    ],
}


def generate_template(topic: str, duration_minutes: float = 5, num_sections: int = 3) -> Dict[str, Any]:
    total_seconds = duration_minutes * 60
    templates = _TEMPLATES.get(num_sections, _TEMPLATES[3])

    sections = []
    for heading, ratio, key_points in templates:
        sections.append({
            "id": str(uuid.uuid4()),
            "heading": heading,
            "duration_seconds": round(total_seconds * ratio),
            "script": f"[{heading}] {topic} 관련 내용을 여기에 직접 작성하세요.",
            "key_points": key_points,
        })

    return {
        "id": str(uuid.uuid4()),
        "title": topic,
        "topic": topic,
        "total_duration": total_seconds,
        "sections": sections,
    }
