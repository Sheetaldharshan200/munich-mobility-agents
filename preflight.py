#!/usr/bin/env python3
"""What is ready on this machine for the Munich demo, and what is not. Changes nothing."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

CLAUDE = Path(os.environ.get("CLAUDE_CONFIG_DIR") or Path.home() / ".claude")
SKILL = "munich-mobility-agents"
AGENTS = ["mobility-operations", "urban-planning", "sustainability", "city-leadership"]
rows: list[tuple[str, str, str]] = []


def add(ok: bool | None, what: str, fix: str = "") -> None:
    rows.append(("OK  " if ok else ("WARN" if ok is None else "FAIL"), what, fix))


def run(cmd: list[str], timeout=60) -> tuple[int, str]:
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return p.returncode, (p.stdout or "") + (p.stderr or "")
    except Exception as e:  # noqa: BLE001
        return 127, str(e)


def main() -> int:
    # 1. the kit
    exakit = shutil.which("exakit") or shutil.which("exakit.ps1")
    add(bool(exakit), "exakit on PATH (Exasol Personal Local Starter Kit)",
        "curl https://www.exasol.com/install/starter-kit.sh | sh   (Windows: irm https://www.exasol.com/install/starter-kit.ps1 | iex)")
    status = {}
    if exakit:
        rc, out = run([exakit, "status", "--json"])
        try:
            status = json.loads(out[out.index("{"):]) if "{" in out else {}
        except Exception:  # noqa: BLE001
            status = {}
        services = status.get("services") or {}
        db = str(services.get("database") or status.get("database") or status.get("status") or "").lower()
        add("run" in db or "healthy" in db or "up" in db, f"database running ({db or 'unknown'})", "exakit start")
        ds = str(services.get("dash-server") or "not installed").lower()
        add("run" in ds, f"dash-server add-on ({ds})",
            "exakit marketplace dash-server   then   exakit start" if "not" in ds else "exakit start")
        url = (status.get("urls") or {}).get("dash-server")
        if url:
            add(True, f"dashboard URL {url}")
        # 2. data
        rc, out = run([exakit, "sql", "--json",
                       "SELECT COUNT(*) AS N FROM EXA_ALL_TABLES WHERE TABLE_SCHEMA='MUNICH_DATASET'"])
        n = None
        try:
            doc = json.loads(out[out.index("{"):]) if "{" in out else json.loads(out)
            txt = json.dumps(doc)
            import re
            m = re.search(r'"N":\s*"?(\d+)', txt)
            n = int(m.group(1)) if m else None
        except Exception:  # noqa: BLE001
            n = None
        add(bool(n), f"schema MUNICH_DATASET loaded ({n if n is not None else 'unknown'} tables)",
            "unzip munich-dataset.zip, then: exakit data-load   (folder path, schema MUNICH_DATASET)")
    # 3. MCP wiring for Claude Code
    cfg = Path.home() / ".claude.json"
    servers = {}
    if cfg.exists():
        try:
            servers = json.loads(cfg.read_text(encoding="utf-8")).get("mcpServers") or {}
        except Exception:  # noqa: BLE001
            servers = {}
    add("exasol" in servers, "exasol MCP server registered in Claude Code", "exakit mcp-setup, then restart Claude Code")
    add("dash-server" in servers, "dash-server MCP server registered in Claude Code", "exakit mcp-setup, then restart Claude Code")
    # 4. this package
    add((CLAUDE / "skills" / SKILL / "SKILL.md").exists(), f"skill {SKILL} installed", "python3 install.py")
    add((CLAUDE / "skills" / "persona-metrics" / "SKILL.md").exists(), "skill persona-metrics installed (dashboard pipeline)",
        "python3 install.py")
    missing = [a for a in AGENTS if not (CLAUDE / "agents" / f"{a}.md").exists()]
    add(not missing, "four persona agents in ~/.claude/agents" + (f" (missing: {', '.join(missing)})" if missing else ""), "python3 install.py")
    missing_cmd = [a for a in AGENTS if not (CLAUDE / "commands" / f"{a}.md").exists()]
    add(not missing_cmd, "four slash commands in ~/.claude/commands (/mobility-operations, /urban-planning, /sustainability, /city-leadership)", "python3 install.py")
    md = CLAUDE / "CLAUDE.md"
    add(md.exists() and "munich-mobility-agents:start" in md.read_text(encoding="utf-8"), "Dash Server rule block in ~/.claude/CLAUDE.md", "python3 install.py")
    home = Path.home()
    others = {"Codex": home / ".codex" / "AGENTS.md", "Gemini CLI": home / ".gemini" / "GEMINI.md",
              "OpenCode": home / ".config" / "opencode" / "AGENTS.md",
              "Cursor": home / ".cursor" / "rules" / "munich-mobility-agents.mdc",
              "Continue": home / ".continue" / "rules" / "munich-mobility-agents.md"}
    have = [n for n, f in others.items() if f.exists() and "munich-mobility-agents:start" in f.read_text(encoding="utf-8")]
    add(True, "Dash Server rule in other AI clients: " + (", ".join(have) if have else "none installed on this machine"))
    st = CLAUDE / "settings.json"
    hook = st.exists() and "block_artifacts.py" in st.read_text(encoding="utf-8")
    add(True if hook else None, "PreToolUse hook blocking artifacts" + ("" if hook else " (not installed)"), "python3 install.py  (or keep it off with --no-hook)")

    width = max(len(r[1]) for r in rows)
    fails = 0
    for state, what, fix in rows:
        print(f"  {state}  {what.ljust(width)}" + (f"   -> {fix}" if fix and state != "OK  " else ""))
        fails += state == "FAIL"
    print()
    print("Ready. Open a NEW Claude Code session and run the prompts in RUNBOOK.md." if fails == 0
          else f"{fails} to fix (lines marked FAIL). WARN lines are optional.")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
