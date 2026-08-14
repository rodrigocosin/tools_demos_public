"""Validação de descrições (comments) em tabelas, views e campos."""

from __future__ import annotations

import re

from app.parser.notebook_parser import ParsedNotebook
from app.validators.models import Severity, ValidationResult

# Padrão para capturar COMMENT em SQL
_COMMENT_PATTERN = re.compile(
    r"""COMMENT\s+['"](.+?)['"]""",
    re.IGNORECASE | re.DOTALL,
)

# COMMENT ON TABLE/COLUMN
_COMMENT_ON_PATTERN = re.compile(
    r"""COMMENT\s+ON\s+(?:TABLE|COLUMN)\s+\S+\s+IS\s+['"](.+?)['"]""",
    re.IGNORECASE | re.DOTALL,
)

# Inline COMMENT em definição de coluna
_INLINE_COMMENT_PATTERN = re.compile(
    r"""\bCOMMENT\s+['"](.+?)['"]""",
    re.IGNORECASE,
)


def validate_descriptions(notebook: ParsedNotebook) -> list[ValidationResult]:
    results: list[ValidationResult] = []
    full_text = notebook.full_code

    all_comments: list[str] = []

    for match in _COMMENT_PATTERN.finditer(full_text):
        all_comments.append(match.group(1).strip())
    for match in _COMMENT_ON_PATTERN.finditer(full_text):
        all_comments.append(match.group(1).strip())

    if not all_comments:
        results.append(ValidationResult(
            category="Descrições",
            severity=Severity.WARNING,
            message="Nenhuma descrição (COMMENT) detectada no notebook.",
            details="Tabelas, views e campos devem conter descrição (COMMENT) com início em letra maiúscula e ponto final.",
        ))
        return results

    invalid_comments = []
    for comment in all_comments:
        issues = []
        if comment and not comment[0].isupper():
            issues.append("não inicia com letra maiúscula")
        if comment and not comment.endswith("."):
            issues.append("não termina com ponto final")
        if issues:
            # Trunca para exibição segura
            display = comment[:80] + "..." if len(comment) > 80 else comment
            invalid_comments.append((display, issues))

    if invalid_comments:
        details_lines = []
        for comment, issues in invalid_comments[:10]:
            details_lines.append(f"  - \"{comment}\" ({', '.join(issues)})")
        if len(invalid_comments) > 10:
            details_lines.append(f"  ... e mais {len(invalid_comments) - 10} descrições com problemas.")

        results.append(ValidationResult(
            category="Descrições",
            severity=Severity.ERROR,
            message=f"{len(invalid_comments)} descrição(ões) não seguem o padrão (letra maiúscula + ponto final).",
            details="\n".join(details_lines),
        ))
    else:
        results.append(ValidationResult(
            category="Descrições",
            severity=Severity.OK,
            message=f"Todas as {len(all_comments)} descrições seguem o padrão (letra maiúscula + ponto final).",
        ))

    return results
