"""Modelos compartilhados para resultados de validação."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class Severity(str, Enum):
    ERROR = "erro"
    WARNING = "aviso"
    OK = "ok"


@dataclass
class ValidationResult:
    category: str
    severity: Severity
    message: str
    details: str = ""


@dataclass
class ValidationReport:
    filename: str
    results: list[ValidationResult] = field(default_factory=list)

    @property
    def errors(self) -> list[ValidationResult]:
        return [r for r in self.results if r.severity == Severity.ERROR]

    @property
    def warnings(self) -> list[ValidationResult]:
        return [r for r in self.results if r.severity == Severity.WARNING]

    @property
    def ok_items(self) -> list[ValidationResult]:
        return [r for r in self.results if r.severity == Severity.OK]

    def to_dict(self) -> dict:
        return {
            "filename": self.filename,
            "summary": {
                "total": len(self.results),
                "errors": len(self.errors),
                "warnings": len(self.warnings),
                "ok": len(self.ok_items),
            },
            "results": [
                {
                    "category": r.category,
                    "severity": r.severity.value,
                    "message": r.message,
                    "details": r.details,
                }
                for r in self.results
            ],
        }
