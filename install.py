#!/usr/bin/env python3
"""One install for the Munich demo: four agents, the routing skill, the Dash Server rule and the persona-metrics
dashboard pipeline (vendored, no chat panel).

    python3 install.py              install everything, then show what is still missing
    python3 install.py --uninstall  remove what this installed
    python3 install.py --no-hook    skip the hook that blocks chat artifacts
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SKILLS = ["munich-mobility-agents", "persona-metrics"]
START, END = "<!-- munich-mobility-agents:start -->", "<!-- munich-mobility-agents:end -->"
HOOK_MARK = "block_artifacts.py"


def claude_home() -> Path:
    return Path(os.environ.get("CLAUDE_CONFIG_DIR") or Path.home() / ".claude")


def copy_tree(src: Path, dst: Path) -> None:
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst, ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".DS_Store"))


def install_skills(step) -> None:
    for name in SKILLS:
        src = HERE / "skill" / name
        for root in (claude_home() / "skills", Path.home() / ".agents" / "skills"):
            dst = root / name
            step(f"skill {name} -> {dst}")
            dst.parent.mkdir(parents=True, exist_ok=True)
            copy_tree(src, dst)
            if name == "munich-mobility-agents":
                (dst / "assets").mkdir(exist_ok=True)
                shutil.copy2(HERE / "scripts" / "prepare_dataset.py", dst / "assets" / "prepare_dataset.py")
                shutil.copy2(HERE / "AGENTS.md", dst / "AGENTS.md")


def install_agents(step) -> int:
    dst = claude_home() / "agents"
    dst.mkdir(parents=True, exist_ok=True)
    n = 0
    for f in sorted((HERE / "agents").glob("*.md")):
        step(f"agent -> {dst / f.name}")
        shutil.copy2(f, dst / f.name)
        n += 1
    return n


# Where each AI client reads its always-on instructions. The rule is appended between markers
# (idempotent) to the shared files, or written as its own rule file where the client has a rules folder.
# A client gets the rule only when its config folder exists, i.e. it is installed on this machine.
def client_rule_targets() -> list[tuple[str, Path, str]]:
    home = Path.home()
    return [
        ("Claude Code", claude_home() / "CLAUDE.md", "append"),
        ("Codex", home / ".codex" / "AGENTS.md", "append"),
        ("Gemini CLI", home / ".gemini" / "GEMINI.md", "append"),
        ("OpenCode", home / ".config" / "opencode" / "AGENTS.md", "append"),
        ("Cursor", home / ".cursor" / "rules" / "munich-mobility-agents.mdc", "cursor"),
        ("Continue", home / ".continue" / "rules" / "munich-mobility-agents.md", "continue"),
    ]


def _client_present(name: str, path: Path) -> bool:
    if name == "Claude Code":
        return True
    root = path.parent.parent if path.parent.name == "rules" else path.parent
    return root.is_dir()


def install_commands(step) -> int:
    """Slash commands /mobility-operations, /urban-planning, /sustainability, /city-leadership."""
    dst = claude_home() / "commands"
    dst.mkdir(parents=True, exist_ok=True)
    n = 0
    for f in sorted((HERE / "commands").glob("*.md")):
        step(f"command -> {dst / f.name}")
        shutil.copy2(f, dst / f.name)
        n += 1
    return n


def install_rules(step) -> list[str]:
    block = (HERE / "claude-rules.md").read_text(encoding="utf-8").strip()
    pattern = re.compile(re.escape(START) + r".*?" + re.escape(END), re.S)
    done = []
    for name, path, kind in client_rule_targets():
        if not _client_present(name, path):
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        if kind == "append":
            existing = path.read_text(encoding="utf-8") if path.exists() else ""
            new = pattern.sub(lambda _m: block, existing) if pattern.search(existing) else \
                (existing.rstrip() + "\n\n" if existing.strip() else "") + block + "\n"
        elif kind == "cursor":
            new = "---\ndescription: Dashboards on Exasol data are built on Dash Server (Munich demo)\nalwaysApply: true\n---\n" + block + "\n"
        else:  # continue
            new = "---\nname: munich-mobility-agents\nalwaysApply: true\n---\n" + block + "\n"
        step(f"rule for {name} -> {path}")
        path.write_text(new, encoding="utf-8")
        done.append(name)
    return done


def remove_rules() -> None:
    for name, path, kind in client_rule_targets():
        if not path.exists():
            continue
        if kind == "append":
            text = path.read_text(encoding="utf-8")
            new = re.sub(r"\n?" + re.escape(START) + r".*?" + re.escape(END) + r"\n?", "\n", text, flags=re.S).strip()
            path.write_text(new + ("\n" if new else ""), encoding="utf-8")
        else:
            path.unlink()


def install_hook(step, enable: bool) -> None:
    settings = claude_home() / "settings.json"
    data = {}
    if settings.exists():
        try:
            data = json.loads(settings.read_text(encoding="utf-8") or "{}")
        except json.JSONDecodeError:
            raise SystemExit(f"{settings} is not valid JSON; fix or remove it, then re-run.")
    hooks = data.setdefault("hooks", {})
    pre = hooks.setdefault("PreToolUse", [])
    pre[:] = [h for h in pre if HOOK_MARK not in json.dumps(h)]
    if enable:
        script = claude_home() / "skills" / "munich-mobility-agents" / "assets" / HOOK_MARK
        pre.append({"matcher": "Artifact|.*show_widget",
                    "hooks": [{"type": "command", "command": f'"{sys.executable}" "{script}"'}]})
        step(f"PreToolUse hook -> {settings}")
    if not pre:
        hooks.pop("PreToolUse", None)
    if not hooks:
        data.pop("hooks", None)
    settings.parent.mkdir(parents=True, exist_ok=True)
    settings.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def uninstall() -> int:
    for name in SKILLS:
        for root in (claude_home() / "skills", Path.home() / ".agents" / "skills"):
            shutil.rmtree(root / name, ignore_errors=True)
    for f in (HERE / "agents").glob("*.md"):
        (claude_home() / "agents" / f.name).unlink(missing_ok=True)
    for f in (HERE / "commands").glob("*.md"):
        (claude_home() / "commands" / f.name).unlink(missing_ok=True)
    remove_rules()
    install_hook(lambda m: None, enable=False)
    print("Removed: both skills, four agents, four slash commands, the Dash Server rule from every AI client, PreToolUse hook.")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--uninstall", action="store_true")
    ap.add_argument("--no-hook", action="store_true")
    ap.add_argument("--verbose", action="store_true")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()
    if args.uninstall:
        return uninstall()
    say = (lambda *a: None) if args.quiet else print
    step = (lambda m: print(f"==> {m}")) if args.verbose else (lambda m: None)

    install_skills(step)
    n = install_agents(step)
    ncmd = install_commands(step)
    clients = install_rules(step)
    install_hook(step, enable=not args.no_hook)

    say(f"Installed: {n} agents, {ncmd} slash commands, munich-mobility-agents, persona-metrics, "
        f"Dash Server rule for {', '.join(clients)}{', hook' if not args.no_hook else ''}")
    say("")
    sys.stdout.flush()
    return subprocess.run([sys.executable, str(HERE / "preflight.py")]).returncode


if __name__ == "__main__":
    sys.exit(main())
