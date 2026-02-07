from __future__ import annotations

import argparse
import subprocess
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_NOTES = ROOT / "SESSION_NOTES.md"


def _run_git(args: list[str]) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return ""
    return result.stdout.strip()


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _ensure_header(path: Path) -> None:
    if path.exists() and path.read_text(encoding="utf-8").strip():
        return
    path.write_text(
        "# SESSION_NOTES\n\n"
        "半自动会话记录：`start` 自动记录会话开始，`end` 自动记录最近一次提交并附人工 next。\n",
        encoding="utf-8",
    )


def cmd_start(path: Path, session: str) -> None:
    _ensure_header(path)
    branch = _run_git(["rev-parse", "--abbrev-ref", "HEAD"]) or "UNKNOWN"
    commit = _run_git(["rev-parse", "--short", "HEAD"]) or "UNKNOWN"
    worktree = str(ROOT)
    block = (
        f"\n## [{_now()}] START {session}\n"
        f"- branch: `{branch}`\n"
        f"- head: `{commit}`\n"
        f"- worktree: `{worktree}`\n"
        f"- status: in_progress\n"
    )
    with path.open("a", encoding="utf-8") as f:
        f.write(block)
    print(f"[session-notes] start recorded in {path}")


def cmd_end(path: Path, session: str, next_step: str, risk: str) -> None:
    _ensure_header(path)
    branch = _run_git(["rev-parse", "--abbrev-ref", "HEAD"]) or "UNKNOWN"
    commit = _run_git(["rev-parse", "--short", "HEAD"]) or "UNKNOWN"
    subject = _run_git(["log", "-1", "--pretty=%s"]) or "NO_COMMIT_MESSAGE"
    files = _run_git(["show", "--name-only", "--pretty=format:", "HEAD"])
    file_lines = [line.strip() for line in files.splitlines() if line.strip()]
    changed = ", ".join(f"`{p}`" for p in file_lines[:12]) if file_lines else "`(no files)`"
    if len(file_lines) > 12:
        changed += f", ... (+{len(file_lines)-12} files)"

    block = (
        f"\n## [{_now()}] END {session}\n"
        f"- branch: `{branch}`\n"
        f"- commit: `{commit}`\n"
        f"- summary: {subject}\n"
        f"- changed_files: {changed}\n"
        f"- next: {next_step}\n"
        f"- risk_or_note: {risk}\n"
        f"- status: done\n"
    )
    with path.open("a", encoding="utf-8") as f:
        f.write(block)
    print(f"[session-notes] end recorded in {path}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Semi-automated SESSION_NOTES.md writer for multi-session worktree workflow."
    )
    parser.add_argument(
        "--notes-path",
        type=Path,
        default=DEFAULT_NOTES,
        help="Path of SESSION_NOTES.md (default: repo root/SESSION_NOTES.md)",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_start = sub.add_parser("start", help="Record session start.")
    p_start.add_argument("--session", required=True, help="Session name, e.g. backend-api")

    p_end = sub.add_parser("end", help="Record session end.")
    p_end.add_argument("--session", required=True, help="Session name, e.g. backend-api")
    p_end.add_argument(
        "--next",
        dest="next_step",
        default="TBD",
        help="Next action for the next session.",
    )
    p_end.add_argument(
        "--risk",
        default="none",
        help="Known risk/blocker/note.",
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    notes_path = args.notes_path

    if args.command == "start":
        cmd_start(notes_path, args.session)
        return
    if args.command == "end":
        cmd_end(notes_path, args.session, args.next_step, args.risk)
        return

    parser.error(f"unknown command: {args.command}")


if __name__ == "__main__":
    main()

