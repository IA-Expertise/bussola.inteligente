#!/usr/bin/env python3
"""Entrypoint Railway — Streamlit (app) ou Gunicorn (webhook)."""
from __future__ import annotations

import os
import subprocess
import sys


def main() -> int:
    service = (os.getenv("BUSSOLA_SERVICE") or "app").strip().lower()
    port = (os.getenv("PORT") or "8080").strip()

    if service == "webhook":
        cmd = [
            "gunicorn",
            "webhook_asaas:app",
            "--bind",
            f"0.0.0.0:{port}",
            "--workers",
            "1",
            "--threads",
            "2",
            "--timeout",
            "120",
            "--access-logfile",
            "-",
            "--error-logfile",
            "-",
        ]
        print(f"railway_start: webhook gunicorn on {port}", flush=True)
    else:
        cmd = [
            "streamlit",
            "run",
            "app.py",
            "--server.port",
            port,
            "--server.address",
            "0.0.0.0",
            "--browser.gatherUsageStats",
            "false",
        ]
        print(f"railway_start: streamlit on {port}", flush=True)

    os.execvp(cmd[0], cmd)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
