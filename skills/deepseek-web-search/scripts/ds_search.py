#!/usr/bin/env python3
"""DeepSeek 联网搜索 / 网页抓取工具。

基于 DeepSeek Search / Fetch API（自研搜索引擎）：
  - POST https://api.deepseek.com/v1/tools/search  网页搜索
  - POST https://api.deepseek.com/v1/tools/fetch   网页抓取（转 Markdown）

鉴权：环境变量 DEEPSEEK_API_KEY（Bearer Token），未设置时读取 ~/.deepseek_key 首行。
计费：Search / Fetch 均按「成功请求次数」计费（5 元 / 1000 次），
      只有返回 HTTP 200 且产生结果（Search 的 results 非空 / Fetch 返回正文）才计费。

用法：
  python3 ds_search.py search "关键词" [--count 10] [--ori-question "原始问题"] \
      [--localization "1.2.3.4"] [--need-content] [--json]
  python3 ds_search.py fetch "https://example.com/article" [--json]

退出码：0 成功；1 请求失败/无结果。
"""

import argparse
import json
import os
import sys
import urllib.request
import urllib.error

BASE = "https://api.deepseek.com"


def _load_key() -> str:
    key = os.environ.get("DEEPSEEK_API_KEY", "").strip()
    if key:
        return key
    p = os.path.expanduser("~/.deepseek_key")
    if os.path.exists(p):
        with open(p, encoding="utf-8") as f:
            key = f.read().strip().splitlines()[0].strip()
    return key


def _post(path: str, payload: dict, key: str) -> dict:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        BASE + path,
        data=data,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"Bearer {key}",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace")
        print(f"[ds_search] HTTP {e.code}: {body}", file=sys.stderr)
        sys.exit(1)


def cmd_search(args) -> None:
    payload = {
        "query": args.query,
        "count": args.count,
        "ori_question": args.ori_question,
        "localization": args.localization,
        "need_content": args.need_content,
    }
    resp = _post("/v1/tools/search", payload, _load_key())
    results = resp.get("results", [])
    if args.json:
        print(json.dumps(resp, ensure_ascii=False, indent=2))
        return
    if not results:
        print("[ds_search] 无匹配结果", file=sys.stderr)
        sys.exit(1)
    for i, r in enumerate(results, 1):
        print(f"[{i}] {r.get('title', '')}")
        print(f"    URL     : {r.get('url', '')}")
        print(f"    站点    : {r.get('site_name') or '-'}  "
              f"权威性 {r.get('authority')}  排序分 {r.get('rerank_score')}")
        if r.get("date"):
            print(f"    发布时间: {r['date']}")
        print(f"    摘要    : {r.get('snippet', '')}")
        summary = r.get("summary", "")
        if summary:
            print(f"    长摘要  : {summary}")
        content = r.get("content", "")
        if content:
            print(f"    正文    : {content}")
        print()


def cmd_fetch(args) -> None:
    payload = {"url": args.url}
    resp = _post("/v1/tools/fetch", payload, _load_key())
    if args.json:
        print(json.dumps(resp, ensure_ascii=False, indent=2))
        return
    title = resp.get("title", "")
    content = resp.get("content", "")
    if not content:
        print("[ds_search] 未抓取到正文", file=sys.stderr)
        sys.exit(1)
    if title:
        print(f"# {title}\n")
    print(content)


def main() -> None:
    p = argparse.ArgumentParser(description="DeepSeek 联网搜索/网页抓取工具")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("search", help="网页搜索")
    s.add_argument("query", help="搜索词（1~128 Unicode 字符，支持 site:/-site:/引号）")
    s.add_argument("--count", type=int, default=10, help="返回条数 1~50，默认 10")
    s.add_argument("--ori-question", default=None, help="触发搜索的用户原始问题（1~128 字符）")
    s.add_argument("--localization", default="", help="优先返回本地化结果的 IP 地址")
    s.add_argument("--need-content", action="store_true", help="返回网页正文（默认 false）")
    s.add_argument("--json", action="store_true", help="输出原始 JSON")
    s.set_defaults(func=cmd_search)

    f = sub.add_parser("fetch", help="网页抓取（转 Markdown）")
    f.add_argument("url", help="要抓取的 URL（HTTP/HTTPS，含 host，不含用户名密码）")
    f.add_argument("--json", action="store_true", help="输出原始 JSON")
    f.set_defaults(func=cmd_fetch)

    args = p.parse_args()
    if not _load_key():
        print("[ds_search] 未找到 DEEPSEEK_API_KEY（请设置环境变量或 ~/.deepseek_key）",
              file=sys.stderr)
        sys.exit(1)
    args.func(args)


if __name__ == "__main__":
    main()
