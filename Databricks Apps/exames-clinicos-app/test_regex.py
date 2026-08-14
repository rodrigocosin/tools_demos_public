import re

def _extract_header_regex(text: str) -> dict:
    # Normalize tabs/multi-spaces → single space, keep newlines
    normalized = re.sub(r'[ \t]+', ' ', text)
    result: dict = {}

    # ── Doctor: "DR. NAME CRM NUM" ─────────────────────────────────────────
    m = re.search(
        r'(?:DR\.?\s+|DRA\.?\s+)([A-ZÁÉÍÓÚÀÂÊÔÃÕÜÇ][A-ZÁÉÍÓÚÀÂÊÔÃÕÜÇ\s]{3,60}?)\s+CRM\s*[\d/\w]+',
        normalized, re.IGNORECASE
    )
    if m:
        result['medico_solicitante'] = m.group(1).strip()

    # ── Fallback doctor: label "Médico/Medico:" + optional title ──────────
    if 'medico_solicitante' not in result:
        m = re.search(
            r'M[eé]dic[oa]\s*:\s*(?:DR\.?\s+|DRA\.?\s+)?([A-ZÁÉÍÓÚÀÂÊÔÃÕÜÇ][^\n]{3,60})',
            normalized, re.IGNORECASE
        )
        if m:
            candidate = m.group(1).strip()
            if not re.search(r'\bCRM\b', candidate, re.IGNORECASE):
                result['medico_solicitante'] = candidate

    # ── Patient + DOB: ALLCAPS name on its own line immediately before a date ──
    # Used for Fleury footer column disorder (PyPDF2 puts patient name after Médico: label).
    # Key: do NOT use re.IGNORECASE and do NOT use \s in char class (avoids crossing lines)
    m = re.search(
        r'\n([A-ZÁÉÍÓÚÀÂÊÔÃÕÜÇ][A-ZÁÉÍÓÚÀÂÊÔÃÕÜÇ ]{5,59})\n(\d{2}/\d{2}/\d{4})',
        normalized  # no IGNORECASE — ALLCAPS only
    )
    if m:
        candidate = m.group(1).strip()
        if not re.search(r'\bCRM\b', candidate, re.IGNORECASE):
            result['nome'] = candidate
            result['data_nascimento'] = m.group(2)

    # ── Fallback patient: label on same line as value ──────────────────────
    # Uses [^\n]+ to stay strictly on the same line as the label
    if 'nome' not in result:
        for label in ['Cliente', 'Paciente', 'Nome do Paciente', 'Solicitado para', r'Benefici[aá]rio']:
            m = re.search(rf'{label}\s*:\s*([^\n]{{3,80}})', normalized, re.IGNORECASE)
            if m:
                candidate = m.group(1).strip()
                if (len(candidate) >= 3
                        and not re.search(r'\bCRM\b', candidate, re.IGNORECASE)
                        and not re.match(r'^(Data|M[eé]dic|Ficha|Idade|Sexo|CPF)\b', candidate, re.IGNORECASE)):
                    result['nome'] = candidate
                    break

    # ── Fallback DOB: label + date on same line ────────────────────────────
    if 'data_nascimento' not in result:
        m = re.search(
            r'(?:Data de Nascimento|Nascimento|D\.?\s*N\.?)\s*[:\s]\s*(\d{2}/\d{2}/\d{4})',
            normalized, re.IGNORECASE
        )
        if m:
            result['data_nascimento'] = m.group(1)

    # ── CPF ───────────────────────────────────────────────────────────────
    # Try labeled first, then standalone XXX.XXX.XXX-XX pattern (Fleury puts it alone)
    m = re.search(r'CPF\s*[:\s]\s*(\d{3}[\s.]?\d{3}[\s.]?\d{3}[\s-]?\d{2})', normalized, re.IGNORECASE)
    if not m:
        m = re.search(r'(\d{3}\.\d{3}\.\d{3}-\d{2})', normalized)
    if m:
        result['cpf'] = m.group(1).strip()

    # ── Exam date ─────────────────────────────────────────────────────────
    for label in ['Data da Ficha', 'Data do Exame', r'Data de Realiza[çc][aã]o', 'Data de Coleta']:
        m = re.search(rf'{label}\s*[:\s]\s*(\d{{2}}/\d{{2}}/\d{{4}})', normalized, re.IGNORECASE)
        if m:
            result['data_exame'] = m.group(1)
            break
    if 'data_exame' not in result:
        dob = result.get('data_nascimento')
        for d in re.findall(r'\d{2}/\d{2}/\d{4}', normalized):
            if d != dob:
                result['data_exame'] = d
                break

    # ── Age ───────────────────────────────────────────────────────────────
    m = re.search(r'Idade\s*[:\s]\s*(\d+)', normalized, re.IGNORECASE)
    if m:
        try:
            result['idade'] = int(m.group(1))
        except ValueError:
            pass

    # ── Sex ───────────────────────────────────────────────────────────────
    m = re.search(r'Sexo\s*[:\s]\s*([MF])', normalized, re.IGNORECASE)
    if m:
        result['sexo'] = m.group(1).upper()

    return result


# ── Test cases ──────────────────────────────────────────────────────────────

tests = [
    (
        "Fleury multi-column (real PyPDF2 output)",
        """ANTICOAGULANTE LUPICO, plasma
Método: Coagulométrico

DR. ANDRE JAIME CRM 87719SP
Cliente:
Data de Nascimento:
Médico:
RODRIGO QUINELATO COSIN
16/05/1983 Ficha:
Data da Ficha:
3801969601
04/09/2025
CRM: 900959 - RESPONSAVEL TECNICO: DR EDGAR GIL RIZZATTI CRM: 94199SP
""",
        {"nome": "RODRIGO QUINELATO COSIN", "medico_solicitante": "ANDRE JAIME",
         "data_nascimento": "16/05/1983", "data_exame": "04/09/2025"},
    ),
    (
        "Normal same-line format (DASA, etc.)",
        """
Paciente: JOAO DA SILVA
Data de Nascimento: 01/01/1970
Medico Solicitante: DR. CARLOS LIMA CRM 12345SP
Data do Exame: 15/03/2025
CPF: 123.456.789-00
""",
        {"nome": "JOAO DA SILVA", "medico_solicitante": "CARLOS LIMA",
         "data_nascimento": "01/01/1970", "data_exame": "15/03/2025", "cpf": "123.456.789-00"},
    ),
    (
        "Mixed case patient name on same line",
        """Cliente:            Rodrigo Quinelato Cosin
Data de Nascimento: 16/05/1983
Medico:             DR. ANDRE JAIME   CRM 87719SP
Data da Ficha:      04/09/2025
""",
        {"nome": "Rodrigo Quinelato Cosin", "medico_solicitante": "ANDRE JAIME",
         "data_nascimento": "16/05/1983", "data_exame": "04/09/2025"},
    ),
    (
        "Fleury with CPF as standalone value",
        """DR. ANDRE JAIME CRM 87719SP
Cliente:
Data de Nascimento:
CPF:
Médico:
RODRIGO QUINELATO COSIN
16/05/1983
321.654.987-00
Data da Ficha:
04/09/2025
""",
        {"nome": "RODRIGO QUINELATO COSIN", "medico_solicitante": "ANDRE JAIME",
         "data_nascimento": "16/05/1983", "cpf": "321.654.987-00", "data_exame": "04/09/2025"},
    ),
    (
        "No doctor CRM (unstructured)",
        """Centro de Imagem Diagnostica
Paciente: MARIA OLIVEIRA SANTOS
Data: 10/02/2025
Medico: Dra. ANA PAULA FERREIRA
CPF: 987.654.321-00
""",
        {"nome": "MARIA OLIVEIRA SANTOS", "medico_solicitante": "ANA PAULA FERREIRA",
         "data_exame": "10/02/2025", "cpf": "987.654.321-00"},
    ),
]

passed = failed = 0
for label, text, expected in tests:
    r = _extract_header_regex(text)
    ok = True
    lines = [f"=== {label} ==="]
    for field, exp_val in expected.items():
        got = r.get(field, 'NOT FOUND')
        match = str(got).strip().upper() == str(exp_val).strip().upper()
        status = "OK  " if match else "FAIL"
        if not match:
            ok = False
        lines.append(f"  [{status}] {field}: got={got!r}  expected={exp_val!r}")
    print('\n'.join(lines))
    print(f"  => {'PASS' if ok else 'FAIL'}\n")
    passed += ok
    failed += not ok

print(f"{'='*50}")
print(f"Results: {passed}/{passed+failed} passed")
