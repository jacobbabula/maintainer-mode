from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import IntEnum
from typing import Any


class Decision(IntEnum):
    READY = 0
    ASK = 1
    STOP = 2

    @property
    def label(self) -> str:
        return self.name


@dataclass(frozen=True)
class Finding:
    decision: Decision
    code: str
    message: str
    evidence: str | None = None

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["decision"] = self.decision.label
        return data


@dataclass
class GateResult:
    findings: list[Finding] = field(default_factory=list)

    @property
    def decision(self) -> Decision:
        return max((finding.decision for finding in self.findings), default=Decision.READY)

    def add(
        self,
        decision: Decision,
        code: str,
        message: str,
        evidence: str | None = None,
    ) -> None:
        self.findings.append(Finding(decision, code, message, evidence))

    def to_dict(self) -> dict[str, Any]:
        return {
            "decision": self.decision.label,
            "findings": [finding.to_dict() for finding in self.findings],
        }
