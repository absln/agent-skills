# Agent Capture 使用说明

## 安装与启动

```bash
cd <本技能目录>     # 即含 package.json / main.js 的那一层
npm install     # 首次需要，下载 electron
npm start
```

> 依赖 electron（约 100MB+），首次安装较慢。

## 抓取一次操作

1. 在目标 URL 输入框填供应商地址，例如：
   - Mimo：`https://aistudio.xiaomimimo.com`
   - DeepSeek：`https://chat.deepseek.com`
   - GLM：`https://chatglm.cn`
2. 点「开始抓包并打开浏览器」。
3. 在抓包窗口：
   - **登录**（走完整登录/验证码流程）
   - 执行你要分析的操作（如：新建对话 → 发一条消息）
4. 点「停止并保存」。
5. 点「打开输出目录」，得到 `session-<ts>/capture-<ts>.ndjson`。

## 分析

把 NDJSON 交给 AI Agent，AI 运行：

```bash
# 打印结构化视图（端点 / 关键头 / Set-Cookie / 跳转链）
node scripts/analyze.mjs

# 指定文件，输出完整 JSON
node scripts/analyze.mjs path/to/capture-xxx.ndjson --json
```

AI 依据录制内容得出：
- **认证画像**：决定 API 放行的 cookie/token 名、与当前适配器所用字段的差异、STS/SSO 登录链。
- **API 端点表**：method/path/body 结构。
- **操作流程**：有序请求序列，供自动化。

## 常见问题

- **登录态不跨次**：每次抓包用独立会话分区，需每次重新登录。若要复用登录，改 `main.js` 中的 `PARTITION` 为固定值。
- **请求体超长**：超过 50KB 会被截断（`recorder.js` 的 `MAX_BODY_CHARS`）。
- **只记录必要信息**：应用不含分析逻辑；具体分析产出视后续应用而定。
