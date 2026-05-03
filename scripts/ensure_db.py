#!/usr/bin/env python3
"""
Aplica sql/init_leads.sql no Postgres indicado por DATABASE_URL.
Chamado pelo Procfile antes do Streamlit no Railway (deploy sem passo manual no Query).
"""
from __future__ import annotations

import os
import sys
from pathlib import Path


def _split_sql_statements(sql_text: str) -> list[str]:
    lines: list[str] = []
    for line in sql_text.splitlines():
        s = line.strip()
        if s.startswith("--"):
            continue
        lines.append(line)
    cleaned = "\n".join(lines)
    parts: list[str] = []
    for chunk in cleaned.split(";"):
        stmt = chunk.strip()
        if stmt:
            parts.append(stmt)
    return parts


def main() -> int:
    dsn = (os.getenv("DATABASE_URL") or "").strip()
    if not dsn:
        print("ensure_db: DATABASE_URL ausente — pulando criação de schema.", file=sys.stderr)
        return 0

    root = Path(__file__).resolve().parent.parent
    sql_path = root / "sql" / "init_leads.sql"
    if not sql_path.is_file():
        print(f"ensure_db: arquivo não encontrado: {sql_path}", file=sys.stderr)
        return 1

    try:
        import psycopg2
    except ImportError:
        print("ensure_db: psycopg2 não instalado.", file=sys.stderr)
        return 1

    raw = sql_path.read_text(encoding="utf-8")
    statements = _split_sql_statements(raw)
    if not statements:
        print("ensure_db: nenhum comando SQL após parse.", file=sys.stderr)
        return 1

    try:
        conn = psycopg2.connect(dsn)
    except Exception as e:
        print(f"ensure_db: falha ao conectar: {e}", file=sys.stderr)
        return 1

    conn.autocommit = True
    try:
        with conn.cursor() as cur:
            for stmt in statements:
                cur.execute(stmt)
        print("ensure_db: tabela public.leads verificada/criada com sucesso.")
        return 0
    except Exception as e:
        print(f"ensure_db: falha ao executar SQL: {e}", file=sys.stderr)
        return 1
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
