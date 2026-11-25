---
name: web-reverse-engineering
description: 通过录制网页真实网络交互，逆向登录认证与业务操作流程——自带零依赖 Electron 录制器可直接启动浏览器抓包（请求头/body、响应 set-cookie/状态、重定向链），也可直接消费 ABot 已录好的 NDJSON 三件套；产出认证画像（放行 cookie/token 名、名称映射、STS/SSO 链）、API 端点表、有序操作链，再落到两条分支：① AgentX 供应商画像 + 适配器与网页版逐项比对；② ABot 平台脚本 login/refresh/publish + schema.json 字段映射。当需要排查供应商接口 401 / 提取某站登录态 / 为自动化复刻某类操作 / 为发布平台新增适配时自动启用。
---

# 网页录制逆向（认证与操作流程）

> **打开浏览器 → 用户操作 → 忠实录制网络 → AI 分析 → 落地产物**。
> 一条流水线：两种录制来源 × 两条产出分支。别按「项目」选技能——按**你要的产出**走到 §4 或 §5。

## 触发场景

| 触发 | 说明 |
|------|------|
| 某供应商接口 401 / 调不通 | 抓真实请求，定位认证 Cookie 名/头差异 |
| 如何提取某网站的登录信息 | 录制登录流程，找出放行接口的 token/cookie |
| 复现某类操作以便自动化 | 录制操作，还原有序请求序列 |
| 为发布平台新增适配 | 录制登录+发布 → 生成平台脚本与字段 schema |
| 校验/修复已有适配器或平台脚本 | 凭证失效、发布报错时重分析录制数据 |

| 不适用 | 原因 |
|--------|------|
| 纯爬虫无登录 | 无认证逆向需求 |
| 无浏览器交互的 API 对接 | 直接用 API 文档 |
| 只在应用内改一行代码 | 不需要录制，直接改 |

## 总览

```
          ┌─ A 自带录制器（从零抓）  ─┐
录制来源 ─┤                            ├─► 定位认证 ─► 定位操作链 ─┬─► 分支 A：AgentX 供应商画像
          └─ B ABot 已有产物（复用）  ─┘        (§2)        (§3)        └─► 分支 B：ABot 平台脚本
```

## 0. 工具链

| 工具 | 用途 | 缺了会怎样 |
|------|------|-----------|
| `jq` | B 来源的 shell 全景分析（§1-B） | 命令 not found |
| `node` | `scripts/analyze.mjs`、`node --check` | 无法结构化视图与语法校验 |
| `pnpm` | 分支 B 的 ScriptRunner 验证（§5.3） | 无法真实验证发布 |
| `curl` | 补抓响应体（A 来源的缺口，见 §1） | 只能靠 `response-bodies.ndjson` |

缺失时先装，否则对应步骤直接失败。

## 1. 选录制来源

| | A 自带录制器 | B ABot 已有产物 |
|---|---|---|
| 产出文件 | `~/.agent-capture/out/session-<ts>/capture-<ts>.ndjson` **单文件** | `logs/<platform>/<ts>/` **三件套** |
| 请求头 / body | ✅ | ✅ `capture-*.ndjson` |
| 响应 set-cookie / 状态码 / 重定向 | ✅ | ✅ `capture-*.ndjson` |
| **响应体** | ❌ 不含（webRequest 取不到 body） | ✅ `response-bodies.ndjson` |
| 凭据密文 | ❌ | ✅ `login-info.enc`（login 模式） |
| 适用产出 | 分支 A（诊断 401 / 供应商画像） | 分支 B（生成发布脚本，需看响应体判成功条件） |

> **两者格式不通用**：A 的单文件喂不进 B 的三件套流程（缺响应体与 `login-info.enc`）。走 B 但手上没有 ABot 产物时，用 A 录完再**补抓响应体**——录制里已有可用 Cookie，直接对登录/校验接口重放：
> ```bash
> curl -sS '<登录接口>' -H "Cookie: <从录制抄的 cookie>" | head -c 2000
> ```
> 得到响应体后与单文件放在同目录，按 §3 的判据手工比对。

### A. 启动自带录制器（在**本技能目录**执行）

```bash
cd <本技能目录>     # 即含 package.json / main.js 的那一层，不在 tools/ 子目录
npm install        # 首次或依赖变更后（electron 约 100MB+，较慢）
npm start
```

- 填目标 base URL（如 `https://aistudio.xiaomimimo.com`）→ 开始。
- 在抓包窗口：**完整登录**（含验证码）→ 执行要分析的操作 → 停止。
- 得到 `~/.agent-capture/out/session-<ts>/capture-<ts>.ndjson`（录制器内部仍叫 `agent-capture`，目录名与 package name 未改，别按技能名找）。
- 结构与参数见 `refs/design.md`、`refs/usage.md`。

### B. 直接消费 ABot 产物

```bash
# 1. 抽出全部 URL，按域名聚合，先看请求全景（`..` 遍历任意层级，字段名按实际录制调整）
cat logs/<platform>/<时间戳>/capture-*.ndjson | jq -r '.. | .url? // empty' 2>/dev/null \
  | awk -F/ '{print $3}' | sort | uniq -c | sort -rn

# 2. 剔除静态资源，只留业务 API
cat logs/<platform>/<时间戳>/capture-*.ndjson | jq -r '.. | .url? // empty' 2>/dev/null \
  | grep -Ev '\.(css|js|png|jpe?g|gif|svg|woff2?|ico|map)(\?|$)' | sort | uniq -c | sort -rn
```

- 统计请求数、区分静态资源与业务 API（`api.*` 域名），识别本次录制阶段：是否完成登录？是否含目标操作？
- 自带录制器的单文件用 `node scripts/analyze.mjs` 出结构化视图：
  ```bash
  node scripts/analyze.mjs                                  # 最新抓包
  node scripts/analyze.mjs <capture-xxx.ndjson> --json       # 完整 JSON
  ```

## 2. 定位认证（两种来源通用）

1. 看 `Set-Cookie`：登录成功后签发了哪些 cookie（多为 token）。
2. 看 API 请求（`/open-apis/*`、`/api/*`、`/chat/*` 等）的 `Cookie` / `Authorization` 头：**哪个字段缺失或命名错误会导致 401**。
3. 看 `redirects` 与 `account.*` 类请求：是否走 STS / SSO 令牌交换（`loginUrl` 指向 `sts?sign=` 时纯 Cookie 直传不够）。
4. 找 `get_qrcode` / `login` / `oauth` / `check_qrconnect` 等登录接口确认流程；从业务接口（`user/get` 等）确认**登录态判定条件**。
5. 识别动态签名头（如 `x-secsdk-csrf-token`，随请求变化）→ **不可静态存储**，须声明为 dynamic header。
6. 有适配器代码时，对比应用侧发送的 Cookie 名与网页版差异。

产出：**认证画像**——放行 API 的 cookie/token 名、cookie 名映射（如 `serviceToken→xiaomichatbot_serviceToken`）、STS/SSO 跳转链、动态头清单。
分支 B 落成 `login.js` 的 credentials 定义（cookie 名、dynamic header、userIdentity）。

## 3. 定位业务操作流程

- 从录制中找目标操作对应的 POST 接口链（发布类典型：`draft/create → draft/update → publish`）。
- 每步记录：method / url / 请求体字段 / **依赖上一步的输出**（如 `draft_id`）。
- 记录固定参数（默认分类、`edit_type` 等）。
- 判据优先级：`response-bodies.ndjson` 里的业务错误码（如 `err_no === 0`）＞ HTTP 状态码——**接口可达 ≠ 认证通过 ≠ 业务成功**，三者分开排查。

产出：**API 端点表**（method/path/body + 鉴权头）+ **有序操作链**。

## 4. 分支 A：AgentX 供应商画像

### 4.1 机械提取起步 JSON

```bash
node scripts/generate-provider-profile.mjs <capture.ndjson> --providerId mimo --name Mimo -o profile.json
```
画像含机械提取的证据（hosts / 端点 / 认证 Cookie 候选 / SSO 主机 / 公共头）+ 待 AI 补全的语义字段。

### 4.2 AI 补齐 → 落库

按 `refs/provider-profile-schema.md` 补齐：认证 Cookie 映射、`cookieTemplate`、`tokenCheck`、`chatPath`。
用真实凭证实测返回 `code:0` 后标为已验证，再落地到 AgentX `src/main/providers/builtin/<id>.ts` 与适配器。

### 4.3 适配器 vs 网页版逐项比对

排查「调不通 / 适配器调用不对」时按 `refs/comparison-template.md` 比对：

```
[A] 目标操作            （登录 / 建会话 / 发消息 / 查询）
[B] 网页版请求          方法 / URL(含query) / 请求头(Cookie,Authorization,X-*) / body
[C] 适配器请求          同上
[D] 差异清单            ① Cookie 名/值 ② 请求头缺失或多余 ③ query 参数
                       ④ body 结构   ⑤ 方法不符        ⑥ 端点路径
[E] 结论 → 修复点
```

- 逐行 diff 请求头，优先 `Cookie` 名与值、`Authorization`、自定义 `X-*`。
- **只改有据的差异，不猜测**；每处差异给出「网页版证据 URL」。
- 修复后用录制凭证对接口实测，确认不再 401。

**已证实的一类根因**（完整复盘见 `refs/mimo-case.md`）：接口/方法/URL/body 全对，唯一差异是 **Cookie 名**——网页版 `xiaomichatbot_serviceToken`，适配器写 `serviceToken` ⇒ 全接口 401。附带教训：「验证凭证通过」可能只是本地非空检查，必须用真实接口校验。

## 5. 分支 B：ABot 平台脚本

### 5.1 schema.json（平台字段对应关系，必填项必须标注）

```json
{
  "platform": "juejin",
  "name": "稀土掘金",
  "auth": { "cookie": ["..."], "dynamicHeader": "..." },
  "publishContent": {
    "title": { "required": true, "source": "task", "sourceKey": "title" },
    "mark_content": { "required": true, "source": "task", "sourceKey": "content" },
    "edit_type": { "required": true, "source": "fixed", "value": 10 },
    "category_id": { "required": false, "source": "task", "sourceKey": "categoryId", "default": "..." },
    "tag_ids": { "required": false, "source": "task", "sourceKey": "tagIds", "default": [] },
    "brief_content": { "required": false, "source": "derived", "derive": "content.slice(0,100)" }
  },
  "apiFlow": [
    { "step": 1, "api": "POST .../create", "output": "data.id" },
    { "step": 2, "api": "POST .../update", "input": "draft_id" },
    { "step": 3, "api": "POST .../publish", "input": "draft_id" }
  ],
  "validate": { "api": "GET ...", "successCondition": "err_no === 0" }
}
```

| source | 说明 |
|--------|------|
| `task` | 从任务数据 `data[sourceKey]` 取，缺省用 default |
| `fixed` | 固定值（如 `edit_type=10`） |
| `derived` | 派生值（如摘要取正文前 N 字） |

### 5.2 三个脚本

```
scripts/<platform-domain>/
├── login.js       # 登录逻辑（分析产物）：返回凭证定义、登录流程、存储位置
├── refresh.js     # 刷新逻辑（分析产物）：返回校验方式、刷新策略
└── publish.js     # 执行版：读 schema.json → 必填校验 → 字段映射 → 调 apiFlow 真实发布
```

- `login.js` / `refresh.js` → **分析产物**，返回结构化定义（凭证是什么/存哪、如何校验）。
- `publish.js` → **执行版**，真实调用接口，返回 `{success, url, error}`。

### 5.3 验证

```bash
node --check scripts/<platform>/*.js          # 语法
# 真实发布：run 模式 + credential-file + data-file
pnpm start -- --mode=run --platform=<platform> \
  --script=scripts/<platform>/publish.js \
  --task-id=T1 --callback-url=http://127.0.0.1:9001 \
  --credential-file=logs/<platform>/<时间戳>/login-info.enc \
  --data-file=post.json
```

校验规则：字段映射正确、必填校验生效、`apiFlow` 顺序正确、能真实发布成功。
掘金全链实录见 `refs/juejin-example.md`。

## 常见错误

| 问题 | 现象 | 处理 |
|------|------|------|
| 录制未完成登录 | `check_qrconnect` 始终 `status:new` | 重新录制完整登录+操作 |
| 只改 cookie 值不改名 | 仍 401 | 核对**名称**映射，不只是值 |
| 动态签名头被静态存 | 首次成功后续全失败 | 标记为 dynamic header，每次现取 |
| `http.post` 未发 body | `create` 成功但 `update` 报"参数错误" | 确认 ScriptRunner 的 `post` 兼容 body 对象（已修复） |
| 必填项未识别 | 平台有必填字段但 schema 未标 `required` | 用不同字段组合实测确定必填项 |
| 把 `login.js` 当执行版 | 期望它发请求却只返回定义 | 真正发包的是 `publish.js` |

## 输出

| 分支 | 产物 |
|------|------|
| A AgentX | 认证画像 + API 端点表 + 供应商画像 JSON → `providers/builtin/<id>.ts` + 适配器 |
| B ABot | `scripts/<platform-domain>/{schema.json, login.js, refresh.js, publish.js}` |

## 规则

- 不向用户索要明文凭据；凭据只出现在录制文件中，分析后按需清理。
- 录制文件含敏感 Cookie/Authorization，**勿提交版本库**；`out/` 视为临时产物。
- 分析结论须基于录制数据，禁止凭空假设；每处差异给出证据 URL。

## 参考文件

| 文件 | 内容 |
|------|------|
| `refs/design.md` | 录制器设计：目标/非目标、记录字段、为什么不内置分析 |
| `refs/usage.md` | 录制器安装与逐屏操作说明 |
| `refs/comparison-template.md` | 适配器 vs 网页版逐项比对模板（分支 A） |
| `refs/provider-profile-schema.md` | 供应商画像 JSON 结构与证据字段（分支 A） |
| `refs/mimo-case.md` | Mimo 401 完整复盘：排查→验证→修复→复盘要点 |
| `refs/juejin-example.md` | 掘金 create→update→publish 全链录制实录（分支 B） |
