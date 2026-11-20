# 案例复盘：Mimo 全接口 401（Cookie 名错误）

> 分支 A 的典型根因。保留完整排查链条，因为「接口全对、只有一个名字错」这类结论只能靠逐项比对得出，不能靠猜。

## 症状

AgentX 里 Mimo 所有模型请求返回 `Mimo failed to save conversation: HTTP 401`；且「验证凭证」页面显示**通过**（旧校验只判断字段非空，不校验有效性）。

## 排查

用录制器录制 Mimo 登录 + 发一条消息，对比网页版 vs 适配器实际发送：

| | 网页版（正常） | 适配器（401） |
|---|---|---|
| Cookie | `xiaomichatbot_serviceToken="..."` | `serviceToken=...` ❌ |
| URL | `?xiaomichatbot_ph=...` | 相同 ✓ |
| body | `{conversationId,title,type}` | 相同 ✓ |
| 方法 / 端点 | `POST /.../conversation/save` | 相同 ✓ |

## 结论

接口、方法、URL、query、body 全对，唯一差异是 **Cookie 名**：`serviceToken` → `xiaomichatbot_serviceToken`。

## 验证

用录制拿到的可用 Cookie，分别以正确名与旧名探测 `conversation/save`：

- 正确名 → `code:0` 成功
- 旧名 → 401

## 修复

适配器 `buildMimoAuthCookie()` 统一用 `xiaomichatbot_serviceToken`，并对 token 值按网页版**加引号**（值里的引号也是协议的一部分，不是格式美化）。

## 复盘要点

1. 「验证凭证通过」可能只是本地非空检查，**不代表 token 有效**；必须用真实接口校验。
2. 401 的 `loginUrl` 若指向 `sts?sign=`，说明走 STS 令牌交换，**纯 Cookie 直传不够**。
3. 接口是否可达、认证是否通过、业务是否成功是**三件事**，分开排查。
4. Cookie 的**名称**和**值**同等重要；改值不改名等于没改。
