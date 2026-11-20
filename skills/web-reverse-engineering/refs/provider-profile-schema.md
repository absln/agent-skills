# 供应商画像（Provider Profile）Schema

由抓包分析产出，用于生成 / 校验 AgentX 的 provider 配置与适配器。目标是让 AI 从录制数据填充画像，再据此生成 `src/main/providers/builtin/*.ts` 的 `BuiltinProviderConfig` 与适配器调用。

## 结构

```jsonc
{
  "meta": {
    "providerId": "mimo",
    "generatedFrom": "capture-xxx.ndjson",
    "date": "2026-08-14",
    "evidence": {                 // 证据引用，便于复核
      "apiHost": "aistudio.xiaomimimo.com",
      "authFailureBeforeFix": "HTTP 401 on all endpoints",
      "verifiedCode": "code:0 成功 after cookie-name fix"
    }
  },

  "provider": {                    // 映射 AgentX Provider + BuiltinProviderConfig
    "id": "mimo",
    "name": "Mimo",
    "type": "builtin",
    "authType": "cookie",          // cookie | oauth | token
    "apiEndpoint": "https://aistudio.xiaomimimo.com",
    "chatPath": "/open-apis/bot/chat",
    "headers": { "X-Timezone": "Asia/Shanghai" },
    "tokenCheckMethod": "POST",
    "tokenCheckEndpoint": "/open-apis/chat/conversation/list"
  },

  "auth": {                        // 认证层（最易踩坑）
    "credentialFields": [          // 映射 Provider.credentialFields
      {
        "key": "service_token",    // AgentX 存储字段名
        "cookieName": "xiaomichatbot_serviceToken",  // 网页版 Cookie 名 ← 关键
        "label": "Service Token",
        "type": "password",
        "quoted": true             // Cookie 值是否加引号
      }
    ],
    "cookieTemplate": "xiaomichatbot_serviceToken=\"${service_token}\"; userId=${user_id}; xiaomichatbot_ph=\"${ph_token}\"",
    "queryAuth": [ { "name": "xiaomichatbot_ph", "from": "ph_token" } ],
    "tokenCheck": { "method": "POST", "path": "/open-apis/chat/conversation/list",
                    "body": { "pageInfo": { "pageNum": 1, "pageSize": 1 } } },
    "sso": { "detected": true, "sts": true, "hosts": ["account.xiaomi.com"] }
  },

  "endpoints": {                   // 适配器层：方法/路径/body 结构
    "chat":              { "method": "POST", "path": "/open-apis/bot/chat", "body": { "msgId": "...", "conversationId": "...", "query": "...", "modelConfig": { "model": "...", "enableThinking": false } } },
    "conversationSave":  { "method": "POST", "path": "/open-apis/chat/conversation/save", "body": { "conversationId": "...", "title": "...", "type": "chat" } },
    "conversationList":  { "method": "POST", "path": "/open-apis/chat/conversation/list", "body": { "pageInfo": { "pageNum": 1, "pageSize": 20 } } },
    "conversationGenTitle": { "method": "POST", "path": "/open-apis/chat/conversation/genTitle", "body": { "conversationId": "...", "content": "..." } }
  },

  "models": [ { "display": "MiMo-V2.5-Pro", "actual": "mimo-v2.5-pro" } ]
}
```

## 生成步骤（AI 侧）

1. `node scripts/generate-provider-profile.mjs <capture.ndjson> --providerId mimo` → 得到**起步画像**（机械提取：hosts/端点/Cookie 名/SSO 主机/公共头）。
2. AI 依据 `SKILL.md` 的分析模板补齐语义字段：
   - `auth.credentialFields[].cookieName`：哪个 Cookie 决定 API 放行（对照 Set-Cookie 与请求 Cookie）。
   - `auth.cookieTemplate`：按网页版实际拼装。
   - `auth.sso`：从跳转链判断 STS/SSO。
   - `endpoints.*`：method/body 从录制请求确认。
3. 用 `auth.tokenCheck` 对真实凭证实测，确认 `code:0`。

## 映射到 AgentX

画像 → `src/main/providers/builtin/<id>.ts`（`BuiltinProviderConfig`）+ 适配器：

| 画像字段 | AgentX 位置 |
|---------|------------|
| `provider.*` | `BuiltinProviderConfig`（id/name/authType/apiEndpoint/chatPath/headers/tokenCheck*） |
| `auth.credentialFields` | `BuiltinProviderConfig.credentialFields` |
| `provider.supportedModels` / `models` | `supportedModels` / `modelMappings` |
| `auth.cookieTemplate` / `queryAuth` | 适配器 `buildHeaders` / `buildUrl` |
| `auth.tokenCheck` | 凭证校验（如 `checker.ts` 的 checkMimoToken） |
| `endpoints.*` | 适配器各方法（chatCompletion/saveConversation/list...） |

## 规则
- 画像所有字段须有录制证据；无法确定标 `"unverified": true`。
- `cookieName` 是最高风险项，必须实测（用抓包凭证改对后返回 `code:0`）才可标为已验证。
- 生成后不直接覆盖 AgentX 配置；作为草稿供人工/AI 核对后落地。
