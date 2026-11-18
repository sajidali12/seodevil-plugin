"""Issue collection and scoring shared by every analyzer."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

SEVERITY_POINTS = {"critical": 15, "high": 8, "medium": 4, "low": 1, "info": 0}
SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}


class Report:
    def __init__(self) -> None:
        self.issues: List[Dict[str, Any]] = []
        self.data: Dict[str, Any] = {}
        self.passed: List[str] = []

    def add(
        self,
        id: str,
        severity: str,
        category: str,
        title: str,
        detail: str = "",
        fix: str = "",
        affected: Optional[list] = None,
        scope: str = "page",
    ) -> None:
        issue: Dict[str, Any] = {"id": id, "severity": severity, "category": category, "title": title}
        if detail:
            issue["detail"] = detail
        if fix:
            issue["fix"] = fix
        if affected:
            issue["affected"] = affected[:15]
            if len(affected) > 15:
                issue["affected_total"] = len(affected)
        if scope != "page":
            issue["scope"] = scope
        self.issues.append(issue)

    def ok(self, what: str) -> None:
        self.passed.append(what)

    def sorted_issues(self) -> List[Dict[str, Any]]:
        return sorted(self.issues, key=lambda i: (SEVERITY_ORDER.get(i["severity"], 9), i["category"], i["id"]))

    def score(self) -> int:
        return score_for(self.issues)

    def counts(self) -> Dict[str, int]:
        return severity_counts(self.issues)


def score_for(issues: List[Dict[str, Any]]) -> int:
    total = sum(SEVERITY_POINTS.get(i["severity"], 0) for i in issues)
    return max(0, 100 - total)


def severity_counts(issues: List[Dict[str, Any]]) -> Dict[str, int]:
    out = {k: 0 for k in ("critical", "high", "medium", "low", "info")}
    for i in issues:
        out[i["severity"]] = out.get(i["severity"], 0) + 1
    return out


def grade(score: int) -> str:
    if score >= 90:
        return "A"
    if score >= 80:
        return "B"
    if score >= 65:
        return "C"
    if score >= 50:
        return "D"
    return "F"
