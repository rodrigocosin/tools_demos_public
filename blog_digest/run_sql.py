#!/usr/bin/env python3
"""Executa SQL no Databricks via Statement Execution API.
Uso: python run_sql.py <arquivo.sql | -e "SELECT ...">
Divide em statements por ';' (ignorando ';' dentro de strings simples) e roda um a um.
"""
import json
import os
import subprocess
import sys

PROFILE = os.environ.get("PROFILE", "fe-vm-cosin-aws-serverless")
WAREHOUSE_ID = os.environ.get("WAREHOUSE_ID", "0c2def7684630e5e")


def run_statement(sql: str):
    sql = sql.strip()
    if not sql:
        return
    payload = {
        "warehouse_id": WAREHOUSE_ID,
        "statement": sql,
        "wait_timeout": "50s",
        "on_wait_timeout": "CANCEL",
    }
    p = subprocess.run(
        ["databricks", "api", "post", "/api/2.0/sql/statements/",
         "--profile", PROFILE, "--json", json.dumps(payload)],
        capture_output=True, text=True,
    )
    if p.returncode != 0:
        print("CLI ERROR:", p.stderr[:2000])
        sys.exit(1)
    resp = json.loads(p.stdout)
    state = resp.get("status", {}).get("state")
    label = sql[:70].replace("\n", " ")
    if state == "SUCCEEDED":
        result = resp.get("result", {})
        data = result.get("data_array")
        print(f"OK   | {label}")
        if data is not None:
            cols = [c["name"] for c in resp.get("manifest", {}).get("schema", {}).get("columns", [])]
            print("     cols:", cols)
            for row in data[:50]:
                print("     ", row)
    else:
        print(f"FAIL | {label}")
        print(json.dumps(resp.get("status", {}), indent=2)[:2000])
        sys.exit(1)


def split_statements(text: str):
    # remove linhas de comentario puro (--)
    lines = [l for l in text.splitlines() if not l.strip().startswith("--")]
    cleaned = "\n".join(lines)
    # split por ';' respeitando strings entre aspas simples
    stmts, buf, in_quote = [], [], False
    i = 0
    while i < len(cleaned):
        c = cleaned[i]
        if c == "'":
            # trata '' (aspa escapada) dentro de string
            if in_quote and i + 1 < len(cleaned) and cleaned[i + 1] == "'":
                buf.append("''")
                i += 2
                continue
            in_quote = not in_quote
            buf.append(c)
        elif c == ";" and not in_quote:
            stmts.append("".join(buf))
            buf = []
        else:
            buf.append(c)
        i += 1
    if buf:
        stmts.append("".join(buf))
    return [s for s in stmts if s.strip()]


if __name__ == "__main__":
    if len(sys.argv) >= 3 and sys.argv[1] == "-e":
        stmts = split_statements(sys.argv[2])
    else:
        with open(sys.argv[1]) as f:
            stmts = split_statements(f.read())
    for s in stmts:
        run_statement(s)
