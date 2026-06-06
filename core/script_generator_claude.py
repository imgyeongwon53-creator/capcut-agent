import json
import os
import re
import uuid
from typing import Any, Dict

import anthropic


def generate_script(topic: str, duration_minutes: float = 5, num_sections: int = 3) -> Dict[str, Any]:
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY 환경변수가 설정되지 않았습니다.")

    client = anthropic.Anthropic(api_key=api_key)
    total_seconds = int(duration_minutes * 60)

    prompt = f"""다음 주제로 {total_seconds}초 분량의 한국어 교육 영상 스크립트를 작성해주세요.

주제: {topic}
섹션 수: {num_sections}개

아래 JSON 형식으로만 응답하세요. JSON 외 다른 텍스트는 포함하지 마세요.

{{
  "title": "영상 제목",
  "sections": [
    {{
      "heading": "섹션 제목",
      "duration_seconds": 숫자,
      "script": "이 섹션에서 말할 내용을 자연스러운 한국어 문장으로 2-4문장 작성",
      "key_points": ["핵심 포인트 1", "핵심 포인트 2", "핵심 포인트 3"]
    }}
  ]
}}

규칙:
- 모든 섹션의 duration_seconds 합계가 {total_seconds}초가 되도록 할 것
- script는 실제로 말할 내용을 구체적으로 작성 (자막으로 사용됨)
- key_points는 2-3개로 간결하게
- 섹션은 도입 → 본론 → 마무리 구조로"""

    response = client.messages.create(
        model="claude-opus-4-8",
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = response.content[0].text.strip()

    json_match = re.search(r'\{[\s\S]*\}', raw)
    if not json_match:
        raise ValueError(f"Claude 응답에서 JSON을 찾을 수 없습니다: {raw[:200]}")

    data = json.loads(json_match.group())
    data["id"] = str(uuid.uuid4())
    data["topic"] = topic
    data["total_duration"] = total_seconds
    for sec in data.get("sections", []):
        sec["id"] = str(uuid.uuid4())

    return data
