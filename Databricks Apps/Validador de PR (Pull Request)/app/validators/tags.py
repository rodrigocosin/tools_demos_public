"""Validações de tagueamento (PII, PHI, ESTRATEGICA, DESCONTINUADO)."""

from __future__ import annotations

import re

from app.parser.notebook_parser import ParsedNotebook
from app.validators.models import Severity, ValidationResult

# Detecta SET TAGS em tabelas
_SET_TAGS_TABLE = re.compile(
    r"(?:ALTER\s+TABLE|SET\s+TAGS)\s*.*?\(\s*(.+?)\s*\)",
    re.IGNORECASE | re.DOTALL,
)

# Detecta SET TAGS em colunas
_SET_TAGS_COLUMN = re.compile(
    r"ALTER\s+(?:TABLE|COLUMN)\s+.*?(?:ALTER\s+COLUMN|SET\s+TAGS)\s*.*?\(\s*(.+?)\s*\)",
    re.IGNORECASE | re.DOTALL,
)

# Tags conhecidas
_KNOWN_TAGS = {"PII", "PHI", "ESTRATEGICA", "DESCONTINUADO"}

# Extrai pares tag = valor
_TAG_PAIR = re.compile(
    r"""['"](\w+)['"]\s*=\s*['"](\w+)['"]""",
    re.IGNORECASE,
)
# Tags sem valor (apenas chave)
_TAG_KEY_ONLY = re.compile(
    r"""['"](\w+)['"]""",
    re.IGNORECASE,
)

_EXPECTED_TABLE_VALUES = {
    "PII": "CONTEM_PII",
    "PHI": "CONTEM_PHI",
    "ESTRATEGICA": "CONTEM_ESTRATEGICA",
}

_NA_MASKING = "N/A_MASKING"
_FIELD_TAG_VALUE_PATTERN = re.compile(r"^[A-Z]+_[A-Z_]+$")


def _extract_tag_assignments(text: str) -> list[tuple[str, str | None]]:
    """Extrai pares (tag, valor) ou (tag, None) do texto."""
    pairs = []
    for match in _TAG_PAIR.finditer(text):
        pairs.append((match.group(1).upper(), match.group(2).upper()))
    return pairs


def validate_tags(notebook: ParsedNotebook) -> list[ValidationResult]:
    results: list[ValidationResult] = []
    full_text = notebook.full_code

    # Procura qualquer referência a SET TAGS
    has_tags = bool(re.search(r"\bSET\s+TAGS\b", full_text, re.IGNORECASE))

    if not has_tags:
        results.append(ValidationResult(
            category="Tagueamento",
            severity=Severity.WARNING,
            message="Nenhum comando SET TAGS detectado no notebook.",
            details="Se o notebook envolve aplicação de tags, verifique manualmente.",
        ))
        return results

    tag_pairs = _extract_tag_assignments(full_text)

    if not tag_pairs:
        results.append(ValidationResult(
            category="Tagueamento",
            severity=Severity.WARNING,
            message="Comando SET TAGS encontrado mas não foi possível extrair pares tag=valor.",
        ))
        return results

    for tag, value in tag_pairs:
        # Validar que tags e valores estão em maiúsculas (já convertemos para upper)
        # Verificar no texto original se estavam em maiúsculas
        original_check = re.search(
            rf"""['"]{tag}['"]\s*=\s*['"]{value}['"]""",
            full_text,
        )
        if not original_check:
            # Tenta encontrar a versão case-insensitive
            ci_check = re.search(
                rf"""['"](?i:{re.escape(tag)})['""" + r"""]\s*=\s*['"](?i:""" + re.escape(value) + r""")['"]""",
                full_text,
            )
            if ci_check:
                original_text = ci_check.group(0)
                if tag not in original_text or value not in original_text:
                    results.append(ValidationResult(
                        category="Tagueamento",
                        severity=Severity.ERROR,
                        message=f"Tag '{tag}' ou valor '{value}' não está em letras maiúsculas.",
                        details="Todas as tags e valores devem estar em letras maiúsculas.",
                    ))

        # Validar valores esperados para tags de tabela
        if tag in _EXPECTED_TABLE_VALUES:
            expected = _EXPECTED_TABLE_VALUES[tag]
            if value == expected:
                results.append(ValidationResult(
                    category="Tagueamento",
                    severity=Severity.OK,
                    message=f"Tag de tabela '{tag}' com valor correto '{value}'.",
                ))
            elif value == _NA_MASKING or _FIELD_TAG_VALUE_PATTERN.match(value):
                # Parece ser tag de campo, não de tabela
                results.append(ValidationResult(
                    category="Tagueamento",
                    severity=Severity.OK,
                    message=f"Tag de campo '{tag}' com valor '{value}'.",
                ))
            else:
                results.append(ValidationResult(
                    category="Tagueamento",
                    severity=Severity.ERROR,
                    message=f"Tag '{tag}' com valor incorreto '{value}'.",
                    details=f"Para tag de tabela '{tag}', o valor esperado é '{expected}'. "
                            f"Para tag de campo, use 'N/A_MASKING' ou padrão [GRUPO]_[INFORMAÇÃO].",
                ))

    return results
