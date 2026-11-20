---
name: deepseek-web-search
description: 用 DeepSeek 自研搜索引擎做联网搜索与网页抓取（Search / Fetch API，按次计费）；当需要联网检索最新信息、抓取网页正文转 Markdown、或作为 deep-research 多源调研的兜底搜索源时自动启用。
---

# deepseek-web-search

> 调用 DeepSeek Search / Fetch API（自研搜索引擎）完成联网搜索与网页抓取。搜索返回结构化结果（标题/链接/短摘要/长摘要/正文/权威性/排序分），抓取返回页面标题 + Markdown 正文。**按成功请求次数计费**（5 元 / 1000 次），非按 token。

---

## 适用场景

| 触发条件 | 说明 |
|---------|------|
| 需要联网检索最新/实时信息 | 模型知识截止之后的事件、新闻、版本发布 |
| 需要抓取某网页正文并转 Markdown | 阅读/引用某篇具体文章内容 |
| 作为 deep-research 的兜底搜索源 | 其它公开源（HN/GitHub/arXiv 等）无结果或需补充中文/综合结果 |
| 需要带权威性/排序分的结构化搜索结果 | 事实核查、证据分级时参考 authority / rerank_score |

| 不适用 | 原因 |
|--------|------|
| 已有专用免费源可满足（GitHub/HN/arXiv 等） | 优先用 deep-research 的直连源，本技能作为补充/兜底 |
| 无 API key 或不想产生计费 | 本技能依赖 DeepSeek API key，且按次计费 |
| 需登录/需 JS 渲染的页面抓取 | Fetch 只返回服务端可得的正文，动态页可能为空 |

---

## 前置条件

1. API key：环境变量 `DEEPSEEK_API_KEY`，或写入 `~/.deepseek_key`（首行）。
2. 脚本：`scripts/ds_search.py`（标准库实现，无第三方依赖，Python 3 即可）。

---

## 执行步骤

### 1. 搜索（search）

```bash
python3 scripts/ds_search.py search "关键词" \
    --count 10 \
    --ori-question "用户原始问题" \
    --need-content          # 可选：返回网页正文
```

参数说明（对齐官方文档）：

| 参数 | 必填 | 约束 | 说明 |
|------|------|------|------|
| `query` | 是 | 1~128 Unicode 字符，非全空白 | 支持 `site:`、`-site:`、引号等搜索语法 |
| `count` | 否 | 1~50，默认 10 | 返回条数 |
| `ori_question` | 否 | 1~128 字符，null 视为未提供 | 触发搜索的用户原始问题，帮助理解意图 |
| `localization` | 否 | 默认空串 | 优先返回本地化结果的 IP 地址 |
| `need_content` | 否 | 默认 false | 是否返回网页正文；false 时 content 恒为空串 |

返回 `results[]` 字段：`rerank_score`（0~3，≥1.5 优质）、`title`、`url`、`snippet`（100~200 字符）、`summary`（600~800 字符，给模型读）、`content`（正文，need_content=false 时为空）、`site_name`、`site_icon`、`date`（RFC3339 UTC）、`authority`（-1~4，≥3 极权威）。

### 2. 抓取（fetch）

```bash
python3 scripts/ds_search.py fetch "https://example.com/article"
```

| 参数 | 必填 | 约束 | 说明 |
|------|------|------|------|
| `url` | 是 | ≤8192 字符，含 host 的 HTTP/HTTPS，不含用户名密码 | 要抓取的网页地址 |

返回：`title`（页面标题，缺失为空串）、`content`（Markdown 正文）。

### 3. 原始 JSON 输出

```bash
python3 scripts/ds_search.py search "关键词" --json
python3 scripts/ds_search.py fetch "URL" --json
```

用于程序化处理或需要完整字段时。

---

## 计费与错误处理

| 事项 | 说明 |
|------|------|
| 计费单位 | 按「成功请求次数」计费，5 元 / 1000 次，不按 token 或结果条数 |
| 计费条件 | 仅 HTTP 200 且产生结果才计费（Search 的 results 非空；Fetch 返回正文） |
| 失败退出码 | HTTP 非 200 或结果为空 → 退出码 1，错误信息走 stderr |
| 无 key | 脚本提示「未找到 DEEPSEEK_API_KEY」并退出 |

---

## 常见错误

| 问题 | 现象 | 处理 |
|------|------|------|
| 401 未鉴权 | `HTTP 401` | 检查 DEEPSEEK_API_KEY / ~/.deepseek_key 是否正确 |
| query 超长 | 接口报 400/422 | query 与 ori_question 均限制 ≤128 字符 |
| 无结果 | `results` 为空，脚本退出码 1 | 优化搜索词，或加 `site:` 限定、精确短语 |
| 正文为空 | need_content 未开，或该页正文缺失 | 加 `--need-content`；仍空则换 fetch 抓取 |
| 动态页抓取为空 | fetch 返回空 content | 该页依赖 JS 渲染，本工具无法获取，换源 |

---

## 输出

```
（无文件产出；结果打印到 stdout，供 Agent 直接阅读或继续加工）
```
