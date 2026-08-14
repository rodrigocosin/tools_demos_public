"""
Assistente LLM para geração de regras de validação.
Usa Foundation Model API do Databricks (Claude Sonnet) para converter
descrições em linguagem natural para params JSON técnicos.
"""

from __future__ import annotations

import json
import logging
import os
import re

logger = logging.getLogger(__name__)

# Endpoint do Foundation Model API
_MODEL_ENDPOINT = "databricks-claude-sonnet-4-6"

# rule_types válidos (segurança: output do LLM é validado contra esta lista)
VALID_RULE_TYPES = {
    "regex_must_exist",
    "regex_must_not_exist",
    "conditional_warning",
    "conditional_compound",
    "notebook_name_pattern",
    "table_prefix_check",
    "view_prefix_check",
    "field_prefix_check",
    "required_column_check",
    "comment_format_check",
    "tag_value_check",
    "tag_uppercase_check",
    "masking_check",
}

# Mapeamento amigável → técnico
FRIENDLY_TYPES = {
    "deve_conter": "regex_must_exist",
    "nao_deve_conter": "regex_must_not_exist",
    "aviso_condicional": "conditional_warning",
    "aviso_composto": "conditional_compound",
    "nome_notebook": "notebook_name_pattern",
    "prefixo_tabela": "table_prefix_check",
    "prefixo_view": "view_prefix_check",
    "prefixo_campo": "field_prefix_check",
    "coluna_obrigatoria": "required_column_check",
    "formato_comment": "comment_format_check",
    "valor_tag": "tag_value_check",
    "tag_maiuscula": "tag_uppercase_check",
    "mascaramento": "masking_check",
}

_SYSTEM_PROMPT = """Você é um assistente que gera regras de validação para notebooks Databricks.

Dado uma descrição em linguagem natural, você deve gerar um JSON com os campos:
- "rule_type": um dos tipos válidos listados abaixo
- "params": objeto JSON com os parâmetros específicos do tipo
- "rule_id": identificador único (snake_case, sem acentos)

## Tipos de regra e seus params:

### regex_must_exist
O padrão regex DEVE existir no código. Erro se não encontrado.
params: {"pattern": "regex aqui", "flags": "IGNORECASE", "search_scope": "full_code"}

### regex_must_not_exist
O padrão regex NÃO DEVE existir no código. Erro se encontrado.
params: {"pattern": "regex aqui", "flags": "IGNORECASE", "search_scope": "full_code"}

### conditional_warning
Se o padrão for encontrado, emite um aviso (warning).
params: {"condition_pattern": "regex aqui", "flags": "IGNORECASE"}

### conditional_compound
Múltiplas condições que devem ser todas verdadeiras (AND) para emitir erro.
params: {"conditions": [{"pattern": "regex1", "flags": "IGNORECASE"}, {"pattern": "regex2", "flags": "IGNORECASE"}], "operator": "AND"}

### notebook_name_pattern
Se uma condição for encontrada no código, o nome do arquivo deve ter um prefixo.
params: {"condition_pattern": "texto_gatilho", "name_prefix": "nb_prefixo_", "flags": "IGNORECASE"}

### table_prefix_check
Tabelas em schemas específicos de catálogos lakehouse devem ter prefixos.
params: {"catalog_pattern": "regex_catalogo", "schema_prefix_map": {"schema": ["prefixo1_", "prefixo2_"]}}

### view_prefix_check
Views devem iniciar com um prefixo.
params: {"required_prefix": "vie_"}

### field_prefix_check
Campos devem usar prefixos aprovados.
params: {"valid_prefixes": ["ano_", "cod_", ...], "skip_if_only_catalog": "catalogo_exceção"}

### required_column_check
Se um tipo de tabela for detectado, certas colunas são obrigatórias.
params: {"table_pattern": "\\\\bprefixo_\\\\w+", "required_columns": ["coluna1", "coluna2"], "flags": "IGNORECASE"}

### comment_format_check
Validações de formato dos COMMENTs SQL.
params: {"require_uppercase_start": true, "require_period_end": true}

### tag_value_check
Valida valores esperados para tags específicas.
params: {"expected_table_values": {"TAG": "VALOR"}, "na_masking_value": "N/A_MASKING", "field_tag_pattern": "^[A-Z]+_[A-Z_]+$"}

### tag_uppercase_check
Tags e valores devem estar em maiúsculas.
params: {}

### masking_check
Validações de funções de mascaramento oc_mask_*.
params: {"function_pattern": "\\\\boc_mask_(\\\\w+)", "min_parts": 2, "default_schema": "catalogo.schema"}

## Regras importantes:
1. Use \\\\b para word boundaries em regex
2. flags deve ser "IGNORECASE" na maioria dos casos
3. search_scope: "full_code" (padrão) pesquisa em todo o notebook
4. Escape duplo de backslashes no JSON (\\\\b, \\\\s, \\\\w)
5. rule_id deve ser snake_case, descritivo, sem acentos
6. Retorne APENAS o JSON, sem explicações

## Exemplos:

Descrição: "O notebook não pode referenciar o catálogo 3_prd_homolog"
Resposta:
{"rule_type": "regex_must_not_exist", "rule_id": "no_catalog_homolog", "params": {"pattern": "\\\\b3_prd_homolog\\\\b", "flags": "IGNORECASE", "search_scope": "full_code"}}

Descrição: "Tabelas no schema 5_srv devem iniciar com srv_"
Resposta:
{"rule_type": "table_prefix_check", "rule_id": "table_prefix_5srv", "params": {"catalog_pattern": "3_prd_lakehouse(_rwd)?", "schema_prefix_map": {"5_srv": ["srv_"]}}}

Descrição: "Se o notebook referenciar o catálogo 3_prd_external, avisar que precisa aprovação do DPO"
Resposta:
{"rule_type": "conditional_warning", "rule_id": "external_dpo_warning", "params": {"condition_pattern": "\\\\b3_prd_external\\\\b", "flags": "IGNORECASE"}}
"""


def generate_rule_params(
    description: str,
    friendly_type: str | None = None,
    category: str = "",
) -> dict | None:
    """
    Usa o LLM para gerar rule_type e params a partir de uma descrição natural.
    Retorna dict com rule_type, rule_id, params ou None em caso de erro.
    """
    # Se o tipo amigável foi fornecido, inclui como dica
    hint = ""
    if friendly_type and friendly_type in FRIENDLY_TYPES:
        technical_type = FRIENDLY_TYPES[friendly_type]
        hint = f"\n\nDica: o tipo de regra mais provável é '{technical_type}'."

    if category:
        hint += f"\nCategoria da regra: '{category}'."

    user_message = f"Gere a regra para: {description}{hint}"

    try:
        from databricks.sdk import WorkspaceClient
        import requests as req

        w = WorkspaceClient()
        # Obtém host e token autenticado do SDK
        host = w.config.host.rstrip("/")
        headers = w.config.authenticate()

        url = f"{host}/serving-endpoints/{_MODEL_ENDPOINT}/invocations"
        payload = {
            "messages": [
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
            "max_tokens": 1000,
            "temperature": 0.1,
        }

        resp = req.post(url, json=payload, headers=headers, timeout=60)
        resp.raise_for_status()
        data = resp.json()

        content = data.get("choices", [{}])[0].get("message", {}).get("content", "")

        if not content:
            logger.error("LLM retornou conteúdo vazio")
            return None

        # Extrai JSON da resposta (pode estar envolta em markdown)
        json_match = re.search(r"\{[\s\S]*\}", content)
        if not json_match:
            logger.error("Não foi possível extrair JSON da resposta do LLM")
            return None

        result = json.loads(json_match.group(0))

        # Validação de segurança: rule_type deve ser válido
        rule_type = result.get("rule_type", "")
        if rule_type not in VALID_RULE_TYPES:
            logger.error("LLM gerou rule_type inválido: %s", rule_type)
            return None

        # Garante que params é um dict
        if not isinstance(result.get("params"), dict):
            logger.error("LLM não gerou params como dict")
            return None

        return {
            "rule_type": result["rule_type"],
            "rule_id": result.get("rule_id", "custom_rule"),
            "params": result["params"],
        }

    except Exception as e:
        logger.exception("Erro ao chamar Foundation Model API: %s", e)
        return None
