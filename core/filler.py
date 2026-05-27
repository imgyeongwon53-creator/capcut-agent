from typing import Any, Dict, List, Tuple

from .config import (
    FILLER_WORDS,
    FILLER_PROBABILITY_THRESHOLD,
    NG_MATCH_CHARS,
    CUT_MERGE_GAP,
)


def detect_filler_cuts(segments: List[Dict[str, Any]]) -> List[Tuple[float, float]]:
    cuts = []
    for seg in segments:
        for w in seg.get("words", []):
            word = w["word"].strip()
            if word in FILLER_WORDS or w["probability"] < FILLER_PROBABILITY_THRESHOLD:
                cuts.append((w["start"], w["end"]))
    return cuts


def detect_repeat_cuts(segments: List[Dict[str, Any]]) -> List[Tuple[float, float]]:
    cuts = []
    for seg in segments:
        words = seg.get("words", [])
        for i in range(len(words) - 1):
            if words[i]["word"].strip() == words[i + 1]["word"].strip():
                cuts.append((words[i]["start"], words[i]["end"]))
    return cuts


def detect_ng_cuts(segments: List[Dict[str, Any]]) -> List[Tuple[float, float]]:
    cuts = []
    for i in range(len(segments) - 1):
        text_a = segments[i]["text"][:NG_MATCH_CHARS]
        text_b = segments[i + 1]["text"][:NG_MATCH_CHARS]
        if text_a and text_b and text_a == text_b:
            cuts.append((segments[i]["start"], segments[i]["end"]))
    return cuts


def _merge_overlapping(cuts: List[Tuple[float, float]]) -> List[Tuple[float, float]]:
    if not cuts:
        return []
    merged: List[List[float]] = [list(cuts[0])]
    for start, end in sorted(cuts)[1:]:
        if start <= merged[-1][1] + CUT_MERGE_GAP:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])
    return [(s, e) for s, e in merged]


def apply_cuts_to_keeps(
    keeps: List[Tuple[float, float]],
    cuts: List[Tuple[float, float]],
) -> List[Tuple[float, float]]:
    result = list(keeps)
    for cut_start, cut_end in cuts:
        new_result = []
        for keep_start, keep_end in result:
            if cut_end <= keep_start or cut_start >= keep_end:
                new_result.append((keep_start, keep_end))
                continue
            if keep_start < cut_start:
                new_result.append((keep_start, cut_start))
            if cut_end < keep_end:
                new_result.append((cut_end, keep_end))
        result = new_result
    return result


def compute_final_keeps(
    keeps: List[Tuple[float, float]],
    segments: List[Dict[str, Any]],
) -> Tuple[List[Tuple[float, float]], List[Tuple[float, float]]]:
    all_cuts = _merge_overlapping(
        detect_filler_cuts(segments)
        + detect_repeat_cuts(segments)
        + detect_ng_cuts(segments)
    )
    final_keeps = apply_cuts_to_keeps(keeps, all_cuts)
    final_keeps = [(s, e) for s, e in final_keeps if e - s >= 0.1]
    return final_keeps, all_cuts
