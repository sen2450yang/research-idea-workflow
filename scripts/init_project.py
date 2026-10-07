#!/usr/bin/env python3
"""Create a new research record from bundled templates, never overwrite.

Python 3.10+; standard library only. No network, installation, or analysis.
The parent directory must exist and the destination must not exist.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
from typing import Any

MODES = ("full", "landscape", "ideation", "novelty", "review", "pilot", "protocol")
MODE_STAGES = {
    "full": set(range(1, 11)),
    "landscape": {1, 2, 3, 4},
    "ideation": {1, 2, 3, 4, 5, 6, 7},
    "novelty": {1, 3, 6},
    "review": {1, 6, 7, 8},
    "pilot": {1, 9},
    "protocol": {1, 9, 10},
}
EXPECTED_TEMPLATES = (
    "research-brief.md", "evidence-ledger.md", "idea-card.md",
    "novelty-and-review.md", "pilot-plan.md", "research-protocol.md",
    "decision-log.md", "report-outline.md", "project-state.json",
)


def prepare_files(template_dir: Path, title: str, mode: str) -> dict[str, str]:
    """Validate and render all input before creating a directory."""
    if not title.strip():
        raise ValueError("研究主题不能为空。")
    if "\n" in title or "\r" in title or "\x00" in title:
        raise ValueError("研究主题必须为单行，且不能含空字符。")
    if mode not in MODES:
        raise ValueError(f"不支持的模式：{mode}")
    timestamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    rendered: dict[str, str] = {}
    for name in EXPECTED_TEMPLATES:
        source = template_dir / name
        if not source.is_file() or source.is_symlink():
            raise FileNotFoundError(f"缺少正常模板文件：{source}")
        raw = source.read_text(encoding="utf-8")
        if source.suffix == ".json":
            data: dict[str, Any] = json.loads(raw)
            data["project_title"] = title.strip()
            data["created_at"] = timestamp
            data["mode"] = mode
            data["scope_note"] = (
                "阶段范围为初始化建议；执行前结合本轮要求调整。"
                "未覆盖阶段可复用已核实成果，但不得假称新近完成。"
            )
            for stage in data["stages"]:
                stage["status"] = (
                    "not_started" if stage["id"] in MODE_STAGES[mode]
                    else "out_of_scope"
                )
            content = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
        else:
            content = raw.replace("{{PROJECT_TITLE}}", title.strip()).replace(
                "{{CREATED_AT}}", timestamp
            )
        rendered[name] = content
    return rendered


def initialize(destination: Path, title: str, mode: str = "full",
               dry_run: bool = False, template_dir: Path | None = None) -> list[Path]:
    """Create one new folder. Reject existing paths, including symlinks."""
    destination = destination.expanduser()
    if destination.exists() or destination.is_symlink():
        raise FileExistsError(f"目标已存在，拒绝覆盖：{destination}")
    parent = destination.parent
    if not parent.is_dir():
        raise FileNotFoundError(f"父目录必须已存在且已获授权：{parent}")
    # Use the actual parent only after the caller has explicitly selected it.
    # No directory is inferred from a project name or template content.
    destination = parent.resolve(strict=True) / destination.name
    if destination.exists() or destination.is_symlink():
        raise FileExistsError(f"目标已存在，拒绝覆盖：{destination}")
    template_dir = template_dir or Path(__file__).resolve().parents[1] / "assets" / "templates"
    files = prepare_files(template_dir, title, mode)
    planned = [destination / name for name in files]
    if dry_run:
        return planned
    destination.mkdir(exist_ok=False)
    created: list[Path] = []
    try:
        for name, content in files.items():
            target = destination / name
            with target.open("x", encoding="utf-8", newline="\n") as stream:
                stream.write(content)
            created.append(target)
    except OSError as exc:
        # Preserve any created files. Never delete potentially user-modified files.
        raise OSError(
            f"写入中断，已创建的 {len(created)} 个文件保留在 {destination}；"
            "未覆盖已有文件。请检查后选用新的目标目录。"
        ) from exc
    return created


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--destination", required=True, type=Path,
                        help="已授权的现有父目录下，一个尚不存在的新目录")
    parser.add_argument("--title", required=True, help="单行研究主题")
    parser.add_argument("--mode", choices=MODES, default="full")
    parser.add_argument("--dry-run", action="store_true", help="只显示计划，不创建目录")
    args = parser.parse_args(argv)
    try:
        paths = initialize(args.destination, args.title, args.mode, args.dry_run)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f"初始化失败：{exc}", file=sys.stderr)
        return 2
    print("计划创建（未写入）：" if args.dry_run else "已创建空白研究记录：")
    for path in paths:
        print(path)
    print("这些文件不是检索、数据分析或实验结果。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
