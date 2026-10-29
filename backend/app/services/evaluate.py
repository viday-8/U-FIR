"""Scores the rule-based extractor on the held-out set. Reports counts, precision, recall and the actual misses."""
import re

from ..eval_data import EVAL_DOCS
from . import rules
from .brief import _parse
from .normalise import norm_name, norm_value

TYPES = ["person", "vehicle", "date", "quantity", "item", "legal_section", "place"]


def _key(type_: str, value: str) -> str:
    if type_ == "person":
        return norm_name(value)
    if type_ == "vehicle":
        return norm_value("vehicle", value)
    if type_ == "date":
        return _parse(value) or value
    if type_ == "legal_section":
        return re.sub(r"[^a-z0-9()]", "", re.sub(r"\bthe\b", "", value.lower()))
    return norm_value(type_, value)


def evaluate() -> dict:
    stats = {t: {"tp": 0, "fp": 0, "fn": 0} for t in TYPES}
    misses, spurious = [], []
    for d in EVAL_DOCS:
        pred = {(f["type"], _key(f["type"], f["value"])): f["value"] for f in rules.extract_rules(d["text"]) if f["type"] in TYPES}
        gold = {(t, _key(t, v)): v for t, v in d["gold"]}
        for k, v in gold.items():
            if k in pred:
                stats[k[0]]["tp"] += 1
            else:
                stats[k[0]]["fn"] += 1
                misses.append({"doc": d["id"], "type": k[0], "expected": v})
        for k, v in pred.items():
            if k not in gold:
                stats[k[0]]["fp"] += 1
                spurious.append({"doc": d["id"], "type": k[0], "extracted": v})
    rows, tp, fp, fn = [], 0, 0, 0
    for t, s in stats.items():
        p = s["tp"] / (s["tp"] + s["fp"]) if s["tp"] + s["fp"] else None
        r = s["tp"] / (s["tp"] + s["fn"]) if s["tp"] + s["fn"] else None
        rows.append({"type": t, **s, "precision": p and round(p, 2), "recall": r and round(r, 2)})
        tp, fp, fn = tp + s["tp"], fp + s["fp"], fn + s["fn"]
    return {"extractor": "rules-v1", "documents": len(EVAL_DOCS), "gold_facts": tp + fn,
            "overall": {"precision": round(tp / (tp + fp), 2), "recall": round(tp / (tp + fn), 2)},
            "by_type": rows, "missed": misses, "spurious": spurious,
            "limits": ["Small hand-labelled set (6 documents) written by the developer, not double-annotated.",
                       "Synthetic text; real records will differ, especially scans, handwriting and Telugu script.",
                       "The rules were developed on the seed cases; this set was written afterwards and not used to tune them."]}
