"""Motor de validação que orquestra validadores dinâmicos (tabela) com fallback estático."""

from __future__ import annotations

import logging

from app.parser.notebook_parser import ParsedNotebook
from app.validators.descriptions import validate_descriptions
from app.validators.dynamic_handlers import run_dynamic_rules
from app.validators.header import validate_header
from app.validators.location import validate_location
from app.validators.masking import validate_masking
from app.validators.models import Severity, ValidationReport, ValidationResult
from app.validators.naming import (
    validate_field_naming,
    validate_notebook_naming,
    validate_table_naming,
    validate_view_naming,
)
from app.validators.required_fields import validate_required_fields
from app.validators.rule_loader import get_rules
from app.validators.tags import validate_tags

logger = logging.getLogger(__name__)

_STATIC_VALIDATORS = [
    validate_header,
    validate_location,
    validate_notebook_naming,
    validate_table_naming,
    validate_view_naming,
    validate_field_naming,
    validate_required_fields,
    validate_descriptions,
    validate_tags,
    validate_masking,
]


def run_all_validations(notebook: ParsedNotebook) -> ValidationReport:
    """Executa todas as validações. Tenta dinâmico primeiro, fallback para estático."""
    report = ValidationReport(filename=notebook.filename)

    # Tenta carregar regras dinâmicas da tabela
    rules = get_rules()

    if rules is not None:
        logger.info("Usando %d regras dinâmicas", len(rules))
        results = run_dynamic_rules(notebook, rules)
        report.results.extend(results)
    else:
        # Fallback para validadores estáticos
        logger.info("Usando validadores estáticos (fallback)")
        for validator in _STATIC_VALIDATORS:
            try:
                results = validator(notebook)
                report.results.extend(results)
            except Exception:
                report.results.append(ValidationResult(
                    category="Erro Interno",
                    severity=Severity.WARNING,
                    message=f"Erro ao executar validação '{validator.__name__}'.",
                    details="Verifique o notebook manualmente para esta categoria.",
                ))

    return report
