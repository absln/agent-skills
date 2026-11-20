# 平台脚本样例参考 — 掘金（juejin.cn）

本目录为 `web-reverse-engineering` 分支 B 的参考样例，展示从 ABot 录制产物生成的平台脚本结构。

## 目录结构

```
scripts/juejin.cn/
├── schema.json       # 平台字段对应关系（必填/来源/默认值）
├── login.js          # 登录逻辑（分析产物）
├── refresh.js        # 凭证刷新/校验（分析产物）
└── publish.js        # 发布执行版（读 schema）
```

## 关键分析结论（掘金）

### 认证凭证
- cookie: `passport_csrf_token`、`csrf_session_id`、`sessionid`、`sid_guard`、`sid_tt`
- 动态签名头: `x-secsdk-csrf-token`（随请求变化，不可静态存储）
- 用户标识: `user_id`（部分接口需要）

### 发布 API 链
1. `POST content_api/v1/article_draft/create` → 返回 `data.id` (draft_id)
2. `POST content_api/v1/article_draft/update` → 补全分类/标签/正文
3. `POST content_api/v1/article/publish` → 发布，返回 `data.article_id`

### 必填字段
`title`、`mark_content`（Markdown 正文）、`edit_type:10`（固定）
可选：`category_id`、`tag_ids`（缺省有默认值）、`brief_content`（派生取正文前100字）

## 使用方式

```bash
# 发布
pnpm start -- --mode=run --platform=juejin \
  --script=scripts/juejin.cn/publish.js \
  --task-id=T1 --callback-url=http://127.0.0.1:9001 \
  --credential-file=logs/juejin/<时间戳>/login-info.enc \
  --data-file=post.json
```

## 复用此样例

新增平台时，参照本结构：
1. 录制该平台登录 + 发布操作
2. 分析出认证 cookie / 发布接口链 / 必填字段
3. 复制本目录结构，替换 schema.json 与脚本中的接口/字段
