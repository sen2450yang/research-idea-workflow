#!/usr/bin/env python3
"""Validate this bundle's structure, references and optional SHA-256 manifest.

Standard library only, Python 3.10+. This checks the YAML subset used by this
bundle; it is not a general YAML parser or an official Agent Skills validator.
No LLM evaluations or scientific fact checking are performed.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
from pathlib import Path
import re
import sys
from urllib.parse import unquote, urlparse

EXPECTED_TEMPLATES = {
    "research-brief.md", "evidence-ledger.md", "idea-card.md",
    "novelty-and-review.md", "pilot-plan.md", "research-protocol.md",
    "decision-log.md", "report-outline.md", "project-state.json",
}
REQUIRED_FILES = {
    "SKILL.md", "README.md", "agents/openai.yaml",
    "references/workflow-complete.md", "references/stages-01-04.md",
    "references/stages-05-08.md", "references/stages-09-10.md",
    "references/evidence-rules.md", "references/review-rubric.md",
    "references/coverage-map.md", "examples/usage.md", "evals/scenarios.json",
    "scripts/init_project.py", "scripts/validate_skill.py", "scripts/test_tooling.py",
} | {f"assets/templates/{name}" for name in EXPECTED_TEMPLATES}


def validate(root: Path, check_manifest: bool = False) -> dict:
    errors: list[str] = []
    checks: list[str] = []
    root = root.resolve()
    if not root.is_dir():
        return {"ok": False, "errors": [f"Skill目录不存在：{root}"], "checks": []}
    for item in sorted(REQUIRED_FILES):
        p = root / item
        if not p.is_file() or p.is_symlink():
            errors.append(f"缺少正常文件：{item}")
    checks.append("必需文件和模板存在")
    texts: dict[str, str] = {}
    for p in sorted(root.rglob("*")):
        if p.is_symlink():
            errors.append(f"不允许打包符号链接：{p.relative_to(root)}")
        if p.is_file() and p.suffix in {".md", ".yaml", ".json", ".py"}:
            try:
                text = p.read_text(encoding="utf-8")
                if not text.strip() or "\x00" in text or "\ufffd" in text:
                    errors.append(f"空白或异常文本：{p.relative_to(root)}")
                texts[p.relative_to(root).as_posix()] = text
                if p.suffix == ".json":
                    json.loads(text)
                if p.suffix == ".py":
                    ast.parse(text, filename=str(p))
            except (UnicodeError, ValueError, SyntaxError) as exc:
                errors.append(f"文本或语法错误：{p.relative_to(root)}: {exc}")
    checks.append("UTF-8、JSON及Python语法")
    skill = texts.get("SKILL.md", "")
    m = re.match(r"\A---\n(.*?)\n---\n", skill, flags=re.S)
    if not m:
        errors.append("SKILL.md缺少YAML前置元数据")
    else:
        block = m.group(1)
        fields: dict[str, str] = {}
        for line in block.splitlines():
            if not line or line.startswith(" ") or line.startswith("#"):
                continue
            if ":" not in line:
                errors.append("不支持的前置元数据行")
                continue
            key, value = line.split(":", 1)
            value = value.strip()
            if value.startswith('"'):
                try:
                    value = json.loads(value)
                except json.JSONDecodeError:
                    errors.append(f"引号字段格式不正确：{key}")
            fields[key] = value
        name = fields.get("name", "")
        if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", name) or not 1 <= len(name) <= 64:
            errors.append("Skill名称不符合本包命名规则")
        if name != root.name:
            errors.append("Skill名称与目录名不一致")
        desc = fields.get("description", "")
        if not 1 <= len(desc) <= 1024:
            errors.append("description长度需为1—1024字符")
    if len(skill.splitlines()) > 500:
        errors.append("SKILL.md超过本包500行上限")
    checks.append("入口元数据、目录名及长度")
    # Only file links are checked, not external resources or anchor semantics.
    local_links = 0
    for name, text in texts.items():
        if not name.endswith(".md"):
            continue
        for match in re.finditer(r"(?<!!)\[[^\]\n]+\]\(([^)\s]+)\)", text):
            href = match.group(1)
            if href.startswith("#") or urlparse(href).scheme:
                continue
            relative = unquote(href.split("#", 1)[0])
            target = (root / name).parent / relative
            resolved = target.resolve()
            if not resolved.is_relative_to(root):
                errors.append(f"越界链接：{name} -> {href}")
            elif not target.is_file():
                errors.append(f"失效文件链接：{name} -> {href}")
            local_links += 1
    checks.append(f"本地Markdown文件链接（{local_links}处）")
    complete = texts.get("references/workflow-complete.md", "")
    for numeral in ("一", "二", "三", "四", "五", "六", "七", "八", "九", "十"):
        if f"## 第{numeral}步：" not in complete:
            errors.append(f"完整流程缺少第{numeral}步")
    if complete.count("**阶段产出：") != 10:
        errors.append("完整流程应保留十个阶段产出")
    if "## 全流程的运行方式" not in complete:
        errors.append("缺少全流程迭代说明")
    checks.append("十阶段章节、阶段产出及迭代说明")
    state_text = texts.get("assets/templates/project-state.json", "{}")
    try:
        state = json.loads(state_text)
        stages = state.get("stages", [])
        if [s.get("id") for s in stages] != list(range(1, 11)):
            errors.append("状态模板阶段ID不是1—10")
        if any(s.get("status") != "not_started" for s in stages):
            errors.append("空白状态不得预先标记完成")
        if state.get("current_stage") is not None:
            errors.append("空白状态不应预设当前执行阶段")
    except (ValueError, TypeError, AttributeError):
        errors.append("状态模板无法解析")
    checks.append("任务状态与未执行标记")
    try:
        scenarios = json.loads(texts.get("evals/scenarios.json", "{}"))
        cases = scenarios.get("cases", [])
        ids = [c["id"] for c in cases]
        if len(cases) < 12 or len(ids) != len(set(ids)):
            errors.append("行为测试场景数量不足或ID重复")
        if scenarios.get("execution_status") != "not_run_on_target_model":
            errors.append("测试状态应如实标为未在目标模型运行")
        for c in cases:
            if not c.get("prompt") or not c.get("expected_behaviors") or not c.get("failure_signals"):
                errors.append(f"行为场景缺少判据：{c.get('id')}")
    except (ValueError, KeyError, TypeError):
        errors.append("行为测试场景无法解析")
    checks.append("行为场景完整性（不代表已经执行）")
    yaml_text = texts.get("agents/openai.yaml", "")
    if "$research-idea-workflow" not in yaml_text:
        errors.append("默认提示词未显式提及Skill")
    sm = re.search(r'^  short_description: (".*")$', yaml_text, re.M)
    if sm:
        try:
            if not 25 <= len(json.loads(sm.group(1))) <= 64:
                errors.append("UI短描述长度不符合25—64字符约定")
        except ValueError:
            errors.append("UI短描述引号格式不正确")
    else:
        errors.append("缺少UI短描述")
    checks.append("显示元数据和默认调用提示")
    if check_manifest:
        try:
            manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
            actual = {
                p.relative_to(root).as_posix() for p in root.rglob("*")
                if p.is_file() and p.name != "manifest.json" and "__pycache__" not in p.parts
            }
            entries = manifest["files"]
            listed = {e["path"] for e in entries}
            if len(listed) != len(entries) or listed != actual:
                errors.append("Manifest文件清单不匹配")
            for e in entries:
                rel = Path(e["path"])
                path = root / rel
                if rel.is_absolute() or ".." in rel.parts or not path.is_file():
                    errors.append(f"Manifest含无效路径：{e['path']}")
                    continue
                raw = path.read_bytes()
                if hashlib.sha256(raw).hexdigest() != e["sha256"] or len(raw) != e["bytes"]:
                    errors.append(f"文件校验失败：{e['path']}")
            checks.append("Manifest文件清单、字节数与SHA-256")
        except (OSError, ValueError, KeyError, TypeError) as exc:
            errors.append(f"Manifest不可用：{exc}")
    return {"ok": not errors, "errors": errors, "checks": checks,
            "scope": "Static bundle checks only; no live model or scientific validation."}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("skill_dir", nargs="?", type=Path,
                        default=Path(__file__).resolve().parents[1])
    parser.add_argument("--check-manifest", action="store_true")
    args = parser.parse_args(argv)
    result = validate(args.skill_dir, args.check_manifest)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
