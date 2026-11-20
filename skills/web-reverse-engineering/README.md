# web-reverse-engineering — 网页录制逆向

> 面向人的应用说明。**AI 执行侧流程以 `SKILL.md` 为准**（触发场景、录制来源选择、定位认证/操作链、两条产出分支的契约都在那里），本文件出现冲突时以 `SKILL.md` 为准。

## 这个技能是什么

一个 Electron 小应用 + 一套分析方法：**打开浏览器窗口 → 你执行操作 → 忠实记录网络交互 → 导出 NDJSON 供 AI 分析**。

技能本体是**录制器**；分析由 AI 读 NDJSON 完成（应用内不做分析）。

## 快速开始

```bash
cd <本技能目录>     # 即含 package.json / main.js 的那一层，不在 tools/ 子目录
npm install        # 首次需要，下载 electron（约 100MB+）
npm start
```

1. 在控制窗填目标 URL → 点「开始抓包并打开浏览器」
2. 在抓包窗口**完整登录**（含验证码）→ 执行要分析的操作（如新建对话 → 发一条消息）
3. 点「停止并保存」→ `~/.agent-capture/out/session-<ts>/capture-<ts>.ndjson`

> 录制器应用本身仍叫 `agent-capture`（`package.json` name、`~/.agent-capture/` 输出根）；技能名是 `web-reverse-engineering`，两者不是一回事。

## 典型用途

- 逆向供应商的**登录认证信息**（哪些 Cookie / token 决定 API 是否放行）——如 Mimo 案例：网页用 `xiaomichatbot_serviceToken`，适配器却用 `serviceToken` 导致全接口 401。
- 还原某类操作的**请求流程**（有序的 method/URL/参数），为自动化做准备。
- 生成供应商的 **API 端点表 + 认证画像** → 分支 A：AgentX 供应商画像
- 生成发布平台的**脚本与字段映射** → 分支 B：ABot 平台脚本

## 能力边界

录制内容：请求头与 body、响应 `set-cookie` / `content-type` / 状态码、重定向链。
**不含响应体**（Electron `webRequest` 取不到 body）。需要响应体判业务成功条件时，用录制里拿到的 Cookie 重放一次：

```bash
curl -sS '<登录或校验接口>' -H "Cookie: <从录制抄的>" | head -c 2000
```

## 目录结构

```
<本技能目录>/
├── main.js                     # Electron 主进程（控制窗 + 抓包窗）
├── preload.js                  # contextBridge IPC
├── recorder.js                 # 网络录制器（webRequest）
├── renderer/                   # 控制 UI
├── scripts/analyze.mjs         # 单文件抓包 → 结构化视图
├── scripts/generate-provider-profile.mjs   # → AgentX 供应商画像起步 JSON
├── refs/                       # 设计/用法/比对模板/画像 schema/两个实录
├── SKILL.md                    # AgentSkill（AI 侧的完整流程）
└── package.json
```

## 说明

- 每次抓包使用**独立会话分区**，登录态不跨次。
- 输出为追加式 NDJSON，便于流式读取与大文件分析。
- 录制文件含敏感 Cookie/Authorization，**勿提交版本库**。
