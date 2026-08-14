"""
Handlers dinâmicos para regras de validação parametrizadas.
Cada handler recebe o notebook e um dict de regra (da tabela Delta)
e retorna uma lista de ValidationResult.

SEGURANÇA: Nenhum handler usa eval/exec. Regex são compilados com flags restritas.
"""

from __future__ import annotations

import logging
import re
from typing import Callable

from app.parser.notebook_parser import ParsedNotebook
from app.validators.extractors import (
    extract_column_names,
    extract_comments,
    extract_mask_functions,
    extract_masking_tags,
    extract_table_refs,
    extract_tag_pairs,
    extract_tag_pairs_raw,
    extract_view_names,
)
from app.validators.models import Severity, ValidationResult

logger = logging.getLogger(__name__)

# Flags permitidas (segurança: não permite VERBOSE ou outros)
_ALLOWED_FLAGS = {
    "IGNORECASE": re.IGNORECASE,
    "MULTILINE": re.MULTILINE,
    "DOTALL": re.DOTALL,
}


def _compile_pattern(pattern: str, flags_str: str = "IGNORECASE") -> re.Pattern:
    """Compila regex com flags restritas."""
    flags = 0
    for flag_name in flags_str.split("|"):
        flag_name = flag_name.strip().upper()
        if flag_name in _ALLOWED_FLAGS:
            flags |= _ALLOWED_FLAGS[flag_name]
    return re.compile(pattern, flags)


def _get_search_text(notebook: ParsedNotebook, scope: str) -> str:
    """Retorna o texto a ser pesquisado conforme o scope."""
    if scope == "filename":
        return notebook.filename
    return notebook.full_code


def _severity_from_str(s: str) -> Severity:
    mapping = {"erro": Severity.ERROR, "aviso": Severity.WARNING, "ok": Severity.OK}
    return mapping.get(s, Severity.ERROR)


# ---------------------------------------------------------------------------
# HANDLERS
# ---------------------------------------------------------------------------

def handle_regex_must_exist(notebook: ParsedNotebook, rule: dict) -> list[ValidationResult]:
    """Padrão regex deve existir no código."""
    params = rule["params"]
    pattern = _compile_pattern(params["pattern"], params.get("flags", "IGNORECASE"))
    scope = params.get("search_scope", "full_code")
    text = _get_search_text(notebook, scope)

    if pattern.search(text):
        if rule.get("message_ok"):
            return [ValidationResult(
                category=rule["category"],
                severity=Severity.OK,
                message=rule["message_ok"],
            )]
        return []
    else:
        return [ValidationResult(
            category=rule["category"],
            severity=_severity_from_str(rule["severity"]),
            message=rule["message_fail"],
            details=rule.get("details_fail", ""),
        )]


def handle_regex_must_not_exist(notebook: ParsedNotebook, rule: dict) -> list[ValidationResult]:
    """Padrão regex NÃO deve existir no código."""
    params = rule["params"]
    pattern = _compile_pattern(params["pattern"], params.get("flags", "IGNORECASE"))
    scope = params.get("search_scope", "full_code")
    text = _get_search_text(notebook, scope)

    if pattern.search(text):
        return [ValidationResult(
            category=rule["category"],
            severity=_severity_from_str(rule["severity"]),
            message=rule["message_fail"],
            details=rule.get("details_fail", ""),
        )]
    else:
        if rule.get("message_ok"):
            return [ValidationResult(
                category=rule["category"],
                severity=Severity.OK,
                message=rule["message_ok"],
            )]
        return []


def handle_conditional_warning(notebook: ParsedNotebook, rule: dict) -> list[ValidationResult]:
    """Se condição encontrada no código, emite aviso."""
    params = rule["params"]
    pattern = _compile_pattern(params["condition_pattern"], params.get("flags", "IGNORECASE"))

    if pattern.search(notebook.full_code):
        return [ValidationResult(
            category=rule["category"],
            severity=_severity_from_str(rule["severity"]),
            message=rule["message_fail"],
            details=rule.get("details_fail", ""),
        )]
    return []


def handle_conditional_compound(notebook: ParsedNotebook, rule: dict) -> list[ValidationResult]:
    """Múltiplas condições AND - todas devem ser verdadeiras para emitir erro."""
    params = rule["params"]
    conditions = params.get("conditions", [])
    operator = params.get("operator", "AND")
    full_text = notebook.full_code

    matches = []
    for cond in conditions:
        pattern = _compile_pattern(cond["pattern"], cond.get("flags", "IGNORECASE"))
        matches.append(bool(pattern.search(full_text)))

    all_match = all(matches) if operator == "AND" else any(matches)

    if all_match:
        return [ValidationResult(
            category=rule["category"],
            severity=_severity_from_str(rule["severity"]),
            message=rule["message_fail"],
            details=rule.get("details_fail", ""),
        )]
    elif rule.get("message_ok") and len(matches) >= 2 and matches[0] and matches[1]:
        # OK message quando lakehouse + ref_rel presentes mas ingestao ausente
        return [ValidationResult(
            category=rule["category"],
            severity=Severity.OK,
            message=rule["message_ok"],
        )]
    return []


def handle_notebook_name_pattern(notebook: ParsedNotebook, rule: dict) -> list[ValidationResult]:
    """Valida nome do notebook se condição encontrada no código."""
    params = rule["params"]
    condition = params.get("condition_pattern", "")
    name_prefix = params.get("name_prefix", "")
    name_exclude = params.get("name_exclude_prefix", "")

    if condition.lower() not in notebook.full_code.lower():
        return []

    fname = notebook.filename.lower()
    dot_pos = fname.rfind(".")
    if dot_pos >= 0:
        fname = fname[:dot_pos]

    passes = fname.startswith(name_prefix.lower())
    if name_exclude and fname.startswith(name_exclude.lower()):
        passes = False
    # Para lakehouse, aceitar nb_ que não seja nb_ingestao_
    if name_exclude and not fname.startswith(name_exclude.lower()) and fname.startswith(name_prefix.lower()):
        passes = True

    if passes:
        if rule.get("message_ok"):
            return [ValidationResult(
                category=rule["category"],
                severity=Severity.OK,
                message=rule["message_ok"],
            )]
        return []
    else:
        return [ValidationResult(
            category=rule["category"],
            severity=_severity_from_str(rule["severity"]),
            message=rule["message_fail"],
            details=rule.get("details_fail", ""),
        )]


def handle_table_prefix_check(notebook: ParsedNotebook, rule: dict) -> list[ValidationResult]:
    """Valida prefixos de tabelas baseado no schema."""
    params = rule["params"]
    catalog_pattern = _compile_pattern(params["catalog_pattern"], "IGNORECASE")
    schema_prefix_map = params.get("schema_prefix_map", {})
    results = []

    refs = extract_table_refs(notebook)
    for catalog, schema, table in refs:
        if not catalog_pattern.search(catalog):
            continue
        for schema_key, valid_prefixes in schema_prefix_map.items():
            if schema.startswith(schema_key) or schema == schema_key:
                has_valid = any(table.startswith(p) for p in valid_prefixes)
                if has_valid:
                    results.append(ValidationResult(
                        category=rule["category"],
                        severity=Severity.OK,
                        message=f"Tabela '{table}' segue o prefixo correto para schema '{schema}'.",
                    ))
                else:
                    prefixes_str = "' ou '".join(valid_prefixes)
                    results.append(ValidationResult(
                        category=rule["category"],
                        severity=_severity_from_str(rule["severity"]),
                        message=f"Tabela '{table}' no schema '{schema}' deve iniciar com '{prefixes_str}'.",
                        details=f"Encontrado: '{table}'.",
                    ))

    if not refs:
        results.append(ValidationResult(
            category=rule["category"],
            severity=Severity.WARNING,
            message="Nenhuma referência a tabelas (catalog.schema.table) foi detectada no notebook.",
        ))

    return results


def handle_view_prefix_check(notebook: ParsedNotebook, rule: dict) -> list[ValidationResult]:
    """Valida prefixo de views."""
    params = rule["params"]
    required_prefix = params.get("required_prefix", "vie_")
    results = []

    views = extract_view_names(notebook)
    for view in views:
        if view != view.lower():
            results.append(ValidationResult(
                category=rule["category"],
                severity=Severity.ERROR,
                message=f"View '{view}' contém letras maiúsculas.",
                details="Nomes de views devem ser em letras minúsculas.",
            ))
        if not view.startswith(required_prefix):
            results.append(ValidationResult(
                category=rule["category"],
                severity=_severity_from_str(rule["severity"]),
                message=f"View '{view}' não inicia com o prefixo '{required_prefix}'.",
                details=f"Views devem iniciar com o prefixo '{required_prefix}'.",
            ))
        else:
            results.append(ValidationResult(
                category=rule["category"],
                severity=Severity.OK,
                message=f"View '{view}' segue a nomenclatura correta.",
            ))

    return results


def handle_field_prefix_check(notebook: ParsedNotebook, rule: dict) -> list[ValidationResult]:
    """Valida prefixos de campos."""
    params = rule["params"]
    valid_prefixes = params.get("valid_prefixes", [])
    skip_catalog = params.get("skip_if_only_catalog", "")
    full_lower = notebook.full_code.lower()

    # Exceção: se apenas catálogo de ingestão
    if skip_catalog and skip_catalog in full_lower and "3_prd_lakehouse" not in full_lower:
        return [ValidationResult(
            category=rule["category"],
            severity=Severity.OK,
            message=f"Catálogo {skip_catalog}: regra de prefixo de campos não se aplica.",
        )]

    columns = extract_column_names(notebook)
    invalid_cols = [c for c in columns if not any(c.startswith(p) for p in valid_prefixes)]

    if invalid_cols:
        prefixes_str = ", ".join(valid_prefixes)
        return [ValidationResult(
            category=rule["category"],
            severity=_severity_from_str(rule["severity"]),
            message=f"{len(invalid_cols)} campo(s) não seguem os prefixos obrigatórios.",
            details=f"Campos inválidos: {', '.join(invalid_cols[:20])}{'...' if len(invalid_cols) > 20 else ''}. "
                    f"Prefixos válidos: {prefixes_str}.",
        )]
    elif columns:
        return [ValidationResult(
            category=rule["category"],
            severity=Severity.OK,
            message=f"Todos os {len(columns)} campos detectados seguem os prefixos obrigatórios.",
        )]
    else:
        return [ValidationResult(
            category=rule["category"],
            severity=Severity.WARNING,
            message="Nenhuma definição de campo detectada para validação de prefixos.",
        )]


def handle_required_column_check(notebook: ParsedNotebook, rule: dict) -> list[ValidationResult]:
    """Valida colunas obrigatórias por tipo de tabela."""
    params = rule["params"]
    table_pattern = _compile_pattern(params["table_pattern"], params.get("flags", "IGNORECASE"))
    required_cols = params.get("required_columns", [])
    full_text = notebook.full_code

    if not table_pattern.search(full_text):
        return []

    missing = [col for col in required_cols if not re.search(rf"\b{re.escape(col)}\b", full_text, re.IGNORECASE)]

    if missing:
        return [ValidationResult(
            category=rule["category"],
            severity=_severity_from_str(rule["severity"]),
            message=f"{rule['message_fail']} {', '.join(missing)}.",
            details=rule.get("details_fail", ""),
        )]
    else:
        if rule.get("message_ok"):
            return [ValidationResult(
                category=rule["category"],
                severity=Severity.OK,
                message=rule["message_ok"],
            )]
        return []


def handle_comment_format_check(notebook: ParsedNotebook, rule: dict) -> list[ValidationResult]:
    """Valida formato de COMMENTs (maiúscula + ponto final)."""
    params = rule["params"]
    require_upper = params.get("require_uppercase_start", True)
    require_period = params.get("require_period_end", True)

    comments = extract_comments(notebook)

    if not comments:
        return [ValidationResult(
            category=rule["category"],
            severity=Severity.WARNING,
            message="Nenhuma descrição (COMMENT) detectada no notebook.",
            details=rule.get("details_fail", ""),
        )]

    invalid = []
    for comment in comments:
        issues = []
        if require_upper and comment and not comment[0].isupper():
            issues.append("não inicia com letra maiúscula")
        if require_period and comment and not comment.endswith("."):
            issues.append("não termina com ponto final")
        if issues:
            display = comment[:80] + "..." if len(comment) > 80 else comment
            invalid.append((display, issues))

    if invalid:
        details_lines = []
        for comment, issues in invalid[:10]:
            details_lines.append(f'  - "{comment}" ({", ".join(issues)})')
        if len(invalid) > 10:
            details_lines.append(f"  ... e mais {len(invalid) - 10} com problemas.")
        return [ValidationResult(
            category=rule["category"],
            severity=_severity_from_str(rule["severity"]),
            message=f"{len(invalid)} descrição(ões) não seguem o padrão (letra maiúscula + ponto final).",
            details="\n".join(details_lines),
        )]
    else:
        return [ValidationResult(
            category=rule["category"],
            severity=Severity.OK,
            message=f"Todas as {len(comments)} descrições seguem o padrão.",
        )]


def handle_tag_value_check(notebook: ParsedNotebook, rule: dict) -> list[ValidationResult]:
    """Valida valores de tags (PII, PHI, ESTRATEGICA)."""
    params = rule["params"]
    expected_table = params.get("expected_table_values", {})
    na_masking = params.get("na_masking_value", "N/A_MASKING")
    field_pattern = params.get("field_tag_pattern", r"^[A-Z]+_[A-Z_]+$")
    field_re = re.compile(field_pattern)

    tag_pairs = extract_tag_pairs(notebook)
    if not tag_pairs:
        return []

    has_set_tags = bool(re.search(r"\bSET\s+TAGS\b", notebook.full_code, re.IGNORECASE))
    if not has_set_tags:
        return [ValidationResult(
            category=rule["category"],
            severity=Severity.WARNING,
            message="Nenhum comando SET TAGS detectado no notebook.",
        )]

    results = []
    for tag, value in tag_pairs:
        if tag in expected_table:
            expected_val = expected_table[tag]
            if value == expected_val:
                results.append(ValidationResult(
                    category=rule["category"],
                    severity=Severity.OK,
                    message=f"Tag de tabela '{tag}' com valor correto '{value}'.",
                ))
            elif value == na_masking or field_re.match(value):
                results.append(ValidationResult(
                    category=rule["category"],
                    severity=Severity.OK,
                    message=f"Tag de campo '{tag}' com valor '{value}'.",
                ))
            else:
                results.append(ValidationResult(
                    category=rule["category"],
                    severity=_severity_from_str(rule["severity"]),
                    message=f"Tag '{tag}' com valor incorreto '{value}'.",
                    details=f"Para tag de tabela '{tag}', valor esperado: '{expected_val}'. "
                            f"Para campo: 'N/A_MASKING' ou padrão [GRUPO]_[INFORMAÇÃO].",
                ))

    return results


def handle_tag_uppercase_check(notebook: ParsedNotebook, rule: dict) -> list[ValidationResult]:
    """Valida que tags e valores estão em maiúsculas."""
    raw_pairs = extract_tag_pairs_raw(notebook)
    results = []

    for tag_orig, val_orig, _ in raw_pairs:
        if tag_orig != tag_orig.upper() or val_orig != val_orig.upper():
            results.append(ValidationResult(
                category=rule["category"],
                severity=_severity_from_str(rule["severity"]),
                message=f"Tag '{tag_orig}' ou valor '{val_orig}' não está em letras maiúsculas.",
                details=rule.get("details_fail", ""),
            ))

    return results


def handle_masking_check(notebook: ParsedNotebook, rule: dict) -> list[ValidationResult]:
    """Valida funções de mascaramento e correspondência tag-função."""
    params = rule["params"]
    results = []

    mask_functions = extract_mask_functions(notebook)
    masking_tags = extract_masking_tags(notebook)

    if not mask_functions and not masking_tags:
        return []

    # Verifica nomenclatura das funções
    if params.get("function_pattern"):
        min_parts = params.get("min_parts", 2)
        for func_suffix in mask_functions:
            func_name = f"oc_mask_{func_suffix}"
            parts = func_suffix.lower().split("_")
            if len(parts) < min_parts:
                results.append(ValidationResult(
                    category=rule["category"],
                    severity=_severity_from_str(rule["severity"]),
                    message=f"Função de mascaramento '{func_name}' não segue o padrão.",
                    details=rule.get("details_fail", ""),
                ))
            else:
                results.append(ValidationResult(
                    category=rule["category"],
                    severity=Severity.OK,
                    message=f"Função de mascaramento '{func_name}' segue o padrão de nomenclatura.",
                ))

        # Verifica schema default
        default_schema = params.get("default_schema", "")
        if default_schema and mask_functions:
            if default_schema in notebook.full_code.lower():
                results.append(ValidationResult(
                    category=rule["category"],
                    severity=Severity.OK,
                    message=f"Funções de mascaramento referenciadas no schema {default_schema}.",
                ))
            else:
                results.append(ValidationResult(
                    category=rule["category"],
                    severity=Severity.WARNING,
                    message=f"Verificar se as funções de mascaramento pertencem ao schema {default_schema}.",
                ))

    # Verifica correspondência tag-função
    if params.get("check_correspondence"):
        for tag_value in masking_tags:
            tag_lower = tag_value.lower()
            expected_func = f"oc_mask_{tag_lower}"
            found = any(f"oc_mask_{f}".lower() == expected_func for f in mask_functions)
            if not found:
                results.append(ValidationResult(
                    category=rule["category"],
                    severity=_severity_from_str(rule["severity"]),
                    message=f"Tag de mascaramento '{tag_value}' sem função correspondente '{expected_func}'.",
                    details=rule.get("details_fail", ""),
                ))

    return results


# ---------------------------------------------------------------------------
# REGISTRY
# ---------------------------------------------------------------------------

HANDLER_REGISTRY: dict[str, Callable] = {
    "regex_must_exist": handle_regex_must_exist,
    "regex_must_not_exist": handle_regex_must_not_exist,
    "conditional_warning": handle_conditional_warning,
    "conditional_compound": handle_conditional_compound,
    "notebook_name_pattern": handle_notebook_name_pattern,
    "table_prefix_check": handle_table_prefix_check,
    "view_prefix_check": handle_view_prefix_check,
    "field_prefix_check": handle_field_prefix_check,
    "required_column_check": handle_required_column_check,
    "comment_format_check": handle_comment_format_check,
    "tag_value_check": handle_tag_value_check,
    "tag_uppercase_check": handle_tag_uppercase_check,
    "masking_check": handle_masking_check,
}


def run_dynamic_rules(notebook: ParsedNotebook, rules: list[dict]) -> list[ValidationResult]:
    """Executa todas as regras dinâmicas e retorna resultados."""
    results = []
    for rule in rules:
        rule_type = rule.get("rule_type", "")
        handler = HANDLER_REGISTRY.get(rule_type)
        if handler is None:
            logger.warning("Tipo de regra desconhecido: %s (rule_id=%s)", rule_type, rule.get("rule_id"))
            continue
        try:
            rule_results = handler(notebook, rule)
            results.extend(rule_results)
        except Exception:
            logger.exception("Erro ao executar regra %s", rule.get("rule_id"))
            results.append(ValidationResult(
                category=rule.get("category", "Erro Interno"),
                severity=Severity.WARNING,
                message=f"Erro ao executar validação '{rule.get('rule_id')}'.",
                details="Verifique o notebook manualmente para esta categoria.",
            ))
    return results
