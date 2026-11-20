# Agent Capture 设计

- 版本：v0.1
- 日期：2026-08-14
- 定位：独立于 AgentX 的「网页操作录制器」，只做忠实录制，分析交给 AI。

## 背景

在排查 Mimo（Xiaomi MiMo）登录/接口 401 问题时，通过在应用内 Electron 窗口抓包，发现：网页版认证 Cookie 名为 `xiaomichatbot_serviceToken`，而 AgentX 适配器用的是 `serviceToken`，导致所有接口 401。修正后即时生效。

这个「打开浏览器 → 用户操作 → 记录网络 → 分析认证与流程」的方法是可复用的。因此抽成独立小应用，并保持 AgentX 主项目干净。

## 目标

1. 独立应用启动浏览器，用户执行操作，忠实记录网络交互。
2. 记录内容足够让 AI 分析出：
   - 登录态/认证信息（放行的 Cookie/token 名、cookie 名称映射、STS/SSO 跳转链）
   - 某类操作的完整请求流程（方法/URL/参数/顺序）
3. 输出为通用 NDJSON，不预设具体分析格式（视后续应用而定）。

## 非目标

- 应用内不做自动化分析（分析由 AI Agent 读 NDJSON 完成）。
- 不做登录态复用（每次独立会话分区）。
- 不做系统休眠唤醒等高级能力。

## 架构

```
控制窗(renderer) ──IPC──▶ 主进程(main.js) ──▶ 抓包窗(session)
                                     │
                                     └─▶ Recorder(recorder.js)
                                           │
                                           ▼
                                    out/session-<ts>/capture-<ts>.ndjson
                                           │
                                           ▼ (AI 读取)
                                    scripts/analyze.mjs → 结构化视图
```

### 录制模型

`Recorder` 挂到抓包窗的 `session`，通过 `webRequest` 系列事件按 `requestId` 关联：

- `onBeforeRequest`：method / url / body（uploadData）
- `onBeforeSendHeaders`：完整请求头（Cookie / Authorization / 自定义）
- `onHeadersReceived`：状态码 / Set-Cookie / content-type
- `onCompleted`：落盘完整记录
- `onRedirect`：跳转链

每行一个 JSON 对象，追加式写入 NDJSON。

## 关键设计决策

| 决策 | 说明 |
|------|------|
| 独立应用 | 本技能目录根（`main.js`/`package.json`/`renderer/`），自带 electron 依赖，与 AgentX 隔离 |
| 只录制 | 应用不含分析逻辑，降低耦合，分析灵活 |
| 独立会话分区 | `persist:capture-<ts>`，登录态不跨次，避免污染 |
| NDJSON | 追加式、可流式、便于大文件与增量分析 |

## 应用到其它供应商

对任意供应商：
1. 启动抓包，填入其 base URL，用户登录并执行操作。
2. AI 读 `capture.ndjson`，得到认证画像 + 端点表 + 流程。
3. 据此生成/校验 AgentX 的 provider 适配器与认证配置（如 Mimo 的 cookie 名修正）。

## 后续可扩展（视需要）

- 固定分区名以复用登录态。
- 录制 response body（当前 webRequest 不提供，需 fetch 拦截）。
- 生成可导入的 provider 画像格式。
- 与应用（AgentX）对接，自动校验适配器调用 vs 网页版差异。
