#!/usr/bin/env python3
"""Install the Munich demo prerequisites: four agents, the routing skill, the Dash Server rule, and persona-metrics.

    python3 install.py                 install everything, then preflight
    python3 install.py --uninstall     remove exactly what this installed
    python3 install.py --no-hook       skip the PreToolUse hook that blocks artifacts
    python3 install.py --skip-deps     do not install/refresh persona-metrics (dashserverskills)
    --clipboard / --key-file PATH      forwarded to persona-metrics' key setup (keeps the key out of the transcript)

Runs identically on macOS, Linux, WSL and Windows (get.sh / get.ps1 only clone and call this).
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
SKILL_NAME = "munich-mobility-agents"
DEPS_REPO = os.environ.get("DASHSERVER_REPO", "https://github.com/yuvi-ex/dashserverskills")
DEPS_DIR = Path(os.environ.get("DASHSERVER_DIR", Path.home() / "dashserverskills"))
START, END = "<!-- munich-mobility-agents:start -->", "<!-- munich-mobility-agents:end -->"
HOOK_MARK = "block_artifacts.py"


def claude_home() -> Path:
    return Path(os.environ.get("CLAUDE_CONFIG_DIR") or Path.home() / ".claude")


def copy_tree(src: Path, dst: Path) -> None:
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst, ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".DS_Store"))


def install_skill(step) -> list[Path]:
    placed = []
    src = HERE / "skill" / SKILL_NAME
    for root in (claude_home() / "skills", Path.home() / ".agents" / "skills"):
        dst = root / SKILL_NAME
        step(f"skill -> {dst}")
        dst.parent.mkdir(parents=True, exist_ok=True)
        copy_tree(src, dst)
        (dst / "assets").mkdir(exist_ok=True)
        shutil.copy2(HERE / "scripts" / "prepare_dataset.py", dst / "assets" / "prepare_dataset.py")
        shutil.copy2(HERE / "AGENTS.md", dst / "AGENTS.md")
        placed.append(dst)
    return placed


def install_agents(step) -> list[Path]:
    dst = claude_home() / "agents"
    dst.mkdir(parents=True, exist_ok=True)
    placed = []
    for f in sorted((HERE / "agents").glob("*.md")):
        step(f"agent -> {dst / f.name}")
        shutil.copy2(f, dst / f.name)
        placed.append(dst / f.name)
    return placed


def install_rules(step) -> Path:
    path = claude_home() / "CLAUDE.md"
    block = (HERE / "claude-rules.md").read_text(encoding="utf-8").strip()
    existing = path.read_text(encoding="utf-8") if path.exists() else ""
    pattern = re.compile(re.escape(START) + r".*?" + re.escape(END), re.S)
    if pattern.search(existing):
        new = pattern.sub(lambda _m: block, existing)
    else:
        new = (existing.rstrip() + "\n\n" if existing.strip() else "") + block + "\n"
    step(f"rule block -> {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(new, encoding="utf-8")
    return path


def remove_rules() -> None:
    path = claude_home() / "CLAUDE.md"
    if not path.exists():
        return
    text = path.read_text(encoding="utf-8")
    new = re.sub(r"\n?" + re.escape(START) + r".*?" + re.escape(END) + r"\n?", "\n", text, flags=re.S).strip()
    path.write_text(new + ("\n" if new else ""), encoding="utf-8")


def install_hook(step, enable: bool) -> Path | None:
    settings = claude_home() / "settings.json"
    data = {}
    if settings.exists():
        try:
            data = json.loads(settings.read_text(encoding="utf-8") or "{}")
        except json.JSONDecodeError:
            raise SystemExit(f"{settings} is not valid JSON; fix it or remove it, then re-run.")
    hooks = data.setdefault("hooks", {})
    pre = hooks.setdefault("PreToolUse", [])
    pre[:] = [h for h in pre if HOOK_MARK not in json.dumps(h)]
    if enable:
        script = claude_home() / "skills" / SKILL_NAME / "assets" / HOOK_MARK
        cmd = f'"{sys.executable}" "{script}"'
        pre.append({"matcher": "Artifact|.*show_widget", "hooks": [{"type": "command", "command": cmd}]})
        step(f"PreToolUse hook -> {settings}")
    if not pre:
        hooks.pop("PreToolUse", None)
    if not hooks:
        data.pop("hooks", None)
    settings.parent.mkdir(parents=True, exist_ok=True)
    settings.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return settings if enable else None


def install_deps(step, args) -> str:
    """persona-metrics (yuvi-ex/dashserverskills): the dashboard pipeline every agent uses."""
    if args.skip_deps:
        return "skipped"
    if not shutil.which("git"):
        return "git missing - install persona-metrics by hand"
    if (DEPS_DIR / ".git").is_dir():
        step(f"updating {DEPS_DIR}")
        subprocess.run(["git", "-C", str(DEPS_DIR), "pull", "--quiet", "--ff-only"], check=False)
    else:
        step(f"cloning {DEPS_REPO} -> {DEPS_DIR}")
        r = subprocess.run(["git", "clone", "--quiet", DEPS_REPO, str(DEPS_DIR)], check=False)
        if r.returncode != 0:
            return "clone failed"
    forwarded = ["--quiet"]
    if args.clipboard:
        forwarded.append("--clipboard")
    if args.key_file:
        forwarded += ["--key-file", args.key_file]
    step("persona-metrics install.py (asks for an optional Anthropic key, hidden input, Enter to skip)")
    r = subprocess.run([sys.executable, str(DEPS_DIR / "install.py")] + forwarded, check=False)
    return "installed" if r.returncode == 0 else f"exit {r.returncode}"


def uninstall() -> int:
    for root in (claude_home() / "skills", Path.home() / ".agents" / "skills"):
        shutil.rmtree(root / SKILL_NAME, ignore_errors=True)
    for f in (HERE / "agents").glob("*.md"):
        try:
            (claude_home() / "agents" / f.name).unlink()
        except FileNotFoundError:
            pass
    remove_rules()
    install_hook(lambda m: None, enable=False)
    print(f"Removed {SKILL_NAME}: skill, four agents, CLAUDE.md rule block, PreToolUse hook. persona-metrics was left in place.")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--uninstall", action="store_true")
    ap.add_argument("--no-hook", action="store_true")
    ap.add_argument("--skip-deps", action="store_true")
    ap.add_argument("--clipboard", action="store_true")
    ap.add_argument("--key-file", metavar="PATH")
    ap.add_argument("--verbose", action="store_true")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()
    if args.uninstall:
        return uninstall()

    say = (lambda *a: None) if args.quiet else print
    step = (lambda m: print(f"==> {m}")) if args.verbose else (lambda m: None)

    deps = install_deps(step, args)
    install_skill(step)
    agents = install_agents(step)
    install_rules(step)
    install_hook(step, enable=not args.no_hook)

    say(f"Installed {SKILL_NAME}: {len(agents)} agents, skill, Dash Server rule, "
        f"{'hook' if not args.no_hook else 'no hook'}; persona-metrics {deps}")
    say("")
    sys.stdout.flush()
    return subprocess.run([sys.executable, str(HERE / "preflight.py")]).returncode


if __name__ == "__main__":
    sys.exit(main())
