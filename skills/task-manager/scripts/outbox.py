#!/usr/bin/env python3
"""离线暂存区（outbox）读写工具：MCP 调用失败时把操作追加到 .agents/tasks/，恢复后回补。

文件格式（与旧文件式任务管理一致，人可读、可手工改）：
  .agents/tasks/TASKS.md   任务操作（create_task / update_task）
  .agents/tasks/ISSUES.md  问题操作（create_issue / update_issue）

一条操作 = 一个二级标题块：

  ## [PENDING] a1b2c3d4 完成A项目方案评审
  - id: a1b2c3d4
  - op: create_task
  - created_at: 2026-10-20 15:30
  - reason: HTTP 401 无效的 API Key
  - payload:
    ```json
    {"title": "完成A项目方案评审", "task_type": "design", "project_id": 101}
    ```

- `id` 8 位十六进制，回补时用于查重（幂等），不会重复建单。
- `[PENDING]` 待回补；`[SYNCED]` 已回补（保留一行留痕，可随时删除）。
- 回补后该条从文件删除；文件里没有 PENDING 块时，文件本身保留一个空表头。

用法：
  python outbox.py add --file tasks --title "标题" --payload '{"title":"...","project_id":101}'
  python outbox.py add --file issues --title "登录页报错" --payload '{...}' --reason "连接被拒绝"
  python outbox.py list
  python outbox.py remove --id a1b2c3d4
  python outbox.py mark --id a1b2c3d4 --status SYNCED
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import uuid
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
TASKS_DIR = ROOT / ".agents" / "tasks"

FILES = {"tasks": "TASKS.md", "issues": "ISSUES.md"}

HEADERS = {
    "tasks": """# TASKS（离线暂存区 / outbox）

> **本文件不是任务台账，权威数据在 MCP 系统（`tasks` 表）。**
> 只有 `create_task` / `update_task` 调用**失败**时才往这里追加一条 `[PENDING]`；MCP 恢复后立即回补并删除该条。
> 格式：一条操作一个 `## [PENDING] <id> <标题>` 块，字段见 `.agents/skills/task-manager/SKILL.md` §14.2。
> 回补：Agent 用 MCP 工具逐条重放，成功后 `outbox.py remove --id <id>`（见 SKILL.md §14.3）

""",
    "issues": """# ISSUES（离线暂存区 / outbox）

> **本文件不是问题台账，权威数据在 MCP 系统（`issues` 表）。**
> 只有 `create_issue` / `update_issue` 调用**失败**时才往这里追加一条 `[PENDING]`；MCP 恢复后立即回补并删除该条。
> 格式：一条操作一个 `## [PENDING] <id> <标题>` 块，字段见 `.agents/skills/task-manager/SKILL.md` §14.2。
> 回补：Agent 用 MCP 工具逐条重放，成功后 `outbox.py remove --id <id>`（见 SKILL.md §14.3）

""",
}

BLOCK_RE = re.compile(r"^## \[(PENDING|SYNCED)\] ([0-9a-f]{8}) (.*)$", re.M)


def path_of(kind: str) -> Path:
    if kind not in FILES:
        raise SystemExit(f"未知文件类型 {kind}，只能是 tasks / issues")
    return TASKS_DIR / FILES[kind]


def ensure_file(kind: str) -> Path:
    p = path_of(kind)
    p.parent.mkdir(parents=True, exist_ok=True)
    if not p.exists():
        p.write_text(HEADERS[kind], encoding="utf-8")
    return p


def new_id() -> str:
    return uuid.uuid4().hex[:8]


def _split_blocks(text: str) -> tuple[str, list[str]]:
    """返回 (文件头, [块文本, ...])。块以 '## [' 开头。"""
    idx = [m.start() for m in re.finditer(r"^## \[", text, re.M)]
    if not idx:
        return text.rstrip("\n") + "\n", []
    head = text[: idx[0]]
    blocks = []
    for i, start in enumerate(idx):
        end = idx[i + 1] if i + 1 < len(idx) else len(text)
        blocks.append(text[start:end].rstrip("\n"))
    return head, blocks


def add(kind: str, title: str, payload: dict, reason: str = "", op: str | None = None) -> str:
    p = ensure_file(kind)
    head, blocks = _split_blocks(p.read_text(encoding="utf-8"))
    op = op or ("create_task" if kind == "tasks" else "create_issue")
    oid = new_id()
    body = json.dumps(payload, ensure_ascii=False)
    block = (
        f"## [PENDING] {oid} {title}\n"
        f"- id: {oid}\n"
        f"- op: {op}\n"
        f"- created_at: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
        f"- reason: {reason or 'MCP 调用失败'}\n"
        f"- payload:\n"
        f"  ```json\n"
        f"  {body}\n"
        f"  ```"
    )
    blocks.append(block)
    p.write_text(head + "\n" + "\n\n".join(blocks) + "\n", encoding="utf-8")
    return oid


def parse(kind: str) -> list[dict]:
    """解析出全部操作块（含 SYNCED）。"""
    p = path_of(kind)
    if not p.exists():
        return []
    _, blocks = _split_blocks(p.read_text(encoding="utf-8"))
    out: list[dict] = []
    for raw in blocks:
        m = BLOCK_RE.match(raw.splitlines()[0])
        if not m:
            out.append({"kind": kind, "status": "BROKEN", "raw": raw})
            continue
        status, oid, title = m.groups()
        item = {"kind": kind, "status": status, "id": oid, "title": title, "raw": raw}
        for line in raw.splitlines()[1:]:
            s = line.strip()
            if s.startswith("- op:"):
                item["op"] = s.split(":", 1)[1].strip()
            elif s.startswith("- created_at:"):
                item["created_at"] = s.split(":", 1)[1].strip()
            elif s.startswith("- reason:"):
                item["reason"] = s.split(":", 1)[1].strip()
        jm = re.search(r"```json\s*(.+?)\s*```", raw, re.S)
        if jm:
            try:
                item["payload"] = json.loads(jm.group(1))
            except json.JSONDecodeError as e:
                item["status"] = "BROKEN"
                item["error"] = f"payload JSON 解析失败：{e}"
        else:
            item["status"] = "BROKEN"
            item["error"] = "缺少 payload 代码块"
        out.append(item)
    return out


def _rewrite(kind: str, blocks: list[str]) -> None:
    p = ensure_file(kind)
    head, _ = _split_blocks(p.read_text(encoding="utf-8"))
    p.write_text(head + ("\n" + "\n\n".join(blocks) + "\n" if blocks else ""), encoding="utf-8")


def remove(kind: str, oid: str) -> bool:
    p = ensure_file(kind)
    head, blocks = _split_blocks(p.read_text(encoding="utf-8"))
    keep = [b for b in blocks if not BLOCK_RE.match(b.splitlines()[0]) or BLOCK_RE.match(b.splitlines()[0]).group(2) != oid]
    if len(keep) == len(blocks):
        return False
    _rewrite(kind, keep)
    return True


def mark(kind: str, oid: str, status: str = "SYNCED") -> bool:
    p = ensure_file(kind)
    head, blocks = _split_blocks(p.read_text(encoding="utf-8"))
    hit = False
    for i, b in enumerate(blocks):
        m = BLOCK_RE.match(b.splitlines()[0])
        if m and m.group(2) == oid:
            blocks[i] = b.replace("## [PENDING]", f"## [{status}]", 1)
            hit = True
    if hit:
        _rewrite(kind, blocks)
    return hit


def pending(kind: str | None = None) -> list[dict]:
    kinds = [kind] if kind else list(FILES)
    items: list[dict] = []
    for k in kinds:
        items.extend([i for i in parse(k) if i["status"] in ("PENDING", "BROKEN")])
    return items


def main() -> None:
    ap = argparse.ArgumentParser(description="离线暂存区（outbox）读写")
    sub = ap.add_subparsers(dest="cmd", required=True)

    a = sub.add_parser("add", help="追加一条待回补操作")
    a.add_argument("--file", required=True, choices=list(FILES))
    a.add_argument("--title", required=True)
    a.add_argument("--payload", required=True, help="JSON 字符串（create_task/create_issue 的入参）")
    a.add_argument("--op", help="操作名，默认 create_task / create_issue")
    a.add_argument("--reason", default="")

    sub.add_parser("list", help="列出待回补操作")

    r = sub.add_parser("remove", help="删除一条操作")
    r.add_argument("--id", required=True)
    r.add_argument("--file", choices=list(FILES))

    m = sub.add_parser("mark", help="标记状态（PENDING → SYNCED）")
    m.add_argument("--id", required=True)
    m.add_argument("--file", choices=list(FILES))
    m.add_argument("--status", default="SYNCED", choices=["SYNCED", "PENDING"])

    args = ap.parse_args()
    if args.cmd == "add":
        try:
            payload = json.loads(args.payload)
        except json.JSONDecodeError as e:
            sys.exit(f"payload 不是合法 JSON：{e}")
        oid = add(args.file, args.title, payload, args.reason, args.op)
        print(oid)
    elif args.cmd == "list":
        items = pending()
        if not items:
            print("outbox 为空")
            return
        for it in items:
            print(f"[{it['status']}] {it['kind']}/{it['id']} {it.get('op','?')} {it['title']}")
            if it.get("error"):
                print(f"    ! {it['error']}")
    elif args.cmd == "remove":
        kinds = [args.file] if args.file else list(FILES)
        ok = any(remove(k, args.id) for k in kinds)
        print("已删除" if ok else "未找到")
    elif args.cmd == "mark":
        kinds = [args.file] if args.file else list(FILES)
        ok = any(mark(k, args.id, args.status) for k in kinds)
        print("已标记" if ok else "未找到")


if __name__ == "__main__":
    main()
