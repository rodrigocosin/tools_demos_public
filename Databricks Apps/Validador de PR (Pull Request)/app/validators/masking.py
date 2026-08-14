"""Validações de mascaramento (funções de masking para PII/PHI/ESTRATEGICA)."""

from __future__ import annotations

import re

from app.parser.notebook_parser import ParsedNotebook
from app.validators.models import Severity, ValidationResult

# Detecta uso de funções de mascaramento
_MASK_FUNCTION = re.compile(r"\boc_mask_(\w+)", re.IGNORECASE)

# Detecta tags com valores que requerem mascaramento (não N/A_MASKING)
_TAG_WITH_MASKING = re.compile(
    r"""['"](?:PII|PHI|ESTRATEGICA)['"]\s*=\s*['"](?!N/A_MASKING)([A-Z_]+)['"]""",
    re.IGNORECASE,
)

# Schema default do catálogo 3_prd_lakehouse
_LAKEHOUSE_DEFAULT_SCHEMA = re.compile(
    r"\b3_prd_lakehouse\.default\b", re.IGNORECASE
)
_LAKEHOUSE_CATALOG = re.compile(r"\b3_prd_lakehouse\b", re.IGNORECASE)


def validate_masking(notebook: ParsedNotebook) -> list[ValidationResult]:
    results: list[ValidationResult] = []
    full_text = notebook.full_code

    # Verifica se há tags que requerem mascaramento
    masking_tags = _TAG_WITH_MASKING.findall(full_text)
    mask_functions = _MASK_FUNCTION.findall(full_text)

    if not masking_tags and not mask_functions:
        # Sem mascaramento no notebook
        return results

    # Valida nomenclatura das funções de mascaramento
    for func_suffix in mask_functions:
        func_name = f"oc_mask_{func_suffix}"
        # Deve seguir padrão oc_mask_[grupo]_[informação]
        parts = func_suffix.lower().split("_")
        if len(parts) < 2:
            results.append(ValidationResult(
                category="Mascaramento",
                severity=Severity.ERROR,
                message=f"Função de mascaramento '{func_name}' não segue o padrão.",
                details="Padrão esperado: oc_mask_[grupo]_[informação mascarada]. Exemplo: oc_mask_paciente_nome.",
            ))
        else:
            results.append(ValidationResult(
                category="Mascaramento",
                severity=Severity.OK,
                message=f"Função de mascaramento '{func_name}' segue o padrão de nomenclatura.",
            ))

    # Verifica se as funções pertencem ao schema default do 3_prd_lakehouse
    has_lakehouse = bool(_LAKEHOUSE_CATALOG.search(full_text))
    if mask_functions and has_lakehouse:
        if _LAKEHOUSE_DEFAULT_SCHEMA.search(full_text):
            results.append(ValidationResult(
                category="Mascaramento",
                severity=Severity.OK,
                message="Funções de mascaramento referenciadas no schema default do catálogo 3_prd_lakehouse.",
            ))
        else:
            results.append(ValidationResult(
                category="Mascaramento",
                severity=Severity.WARNING,
                message="Verificar se as funções de mascaramento pertencem ao schema default do catálogo 3_prd_lakehouse.",
                details="As funções de mascaramento utilizadas devem pertencer ao schema default do catálogo 3_prd_lakehouse.",
            ))

    # Avisos obrigatórios quando há mascaramento
    if masking_tags or mask_functions:
        results.append(ValidationResult(
            category="Mascaramento",
            severity=Severity.WARNING,
            message='Será necessário a evidência com "De Acordo" dos responsáveis.',
            details="Responsáveis: solicitante, líder imediato e Thiago Jordão.",
        ))
        results.append(ValidationResult(
            category="Mascaramento",
            severity=Severity.WARNING,
            message="Será necessário validar a criação dos grupos de acesso.",
            details=(
                "Os grupos de acesso devem seguir o padrão de nomenclatura "
                "mask_[grupo]_[informação mascarada] e a inclusão dos usuários. "
                "Exemplo: mask_paciente_nome."
            ),
        ))

    # Verifica correspondência entre tags e funções
    for tag_value in masking_tags:
        tag_lower = tag_value.lower()
        expected_func = f"oc_mask_{tag_lower}"
        func_found = any(
            f"oc_mask_{f}".lower() == expected_func
            for f in mask_functions
        )
        if not func_found:
            results.append(ValidationResult(
                category="Mascaramento",
                severity=Severity.WARNING,
                message=f"Tag de mascaramento '{tag_value}' sem função correspondente 'oc_mask_{tag_lower}'.",
                details="Verifique se a função de mascaramento correspondente está definida.",
            ))

    return results
