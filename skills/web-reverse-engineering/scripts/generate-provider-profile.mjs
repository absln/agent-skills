#!/usr/bin/env node
/**
 * agent-capture — 生成供应商画像（起步版）
 *
 * 从抓包 NDJSON 机械提取证据，生成「供应商画像」起步 JSON，供 AI 补齐语义字段
 * （认证 Cookie 映射、SSO、端点结构）。画像 schema 见 docs/provider-profile-schema.md。
 *
 * 用法：
 *   node scripts/generate-provider-profile.mjs <capture-*.ndjson> --providerId mimo [--name Mimo] [--json]
 *   （--providerId 必填；输出到 stdout，或 -o out.json）
 */
import { readFileSync } from 'node:fs'

const file = process.argv[2]
const pidIdx = process.argv.indexOf('--providerId')
const providerId = pidIdx > -1 ? process.argv[pidIdx + 1] : null
const nameIdx = process.argv.indexOf('--name')
const name = nameIdx > -1 ? process.argv[nameIdx + 1] : providerId
const outIdx = process.argv.indexOf('-o')
const outFile = outIdx > -1 ? process.argv[outIdx + 1] : null

if (!file || !providerId) {
  console.error('用法: node scripts/generate-provider-profile.mjs <capture-*.ndjson> --providerId <id> [--name N] [-o out.json]')
  process.exit(1)
}

const lines = readFileSync(file, 'utf8').split('\n').filter(Boolean).map((l) => JSON.parse(l))
const requests = lines.filter((l) => l.t === 'request')
const redirects = lines.filter((l) => l.t === 'redirect')

// 兼容旧格式（分离的 t:'headers' 记录）与新格式（合并到 request 的 headers）
const headerRecords = lines.filter((l) => l.t === 'headers')
const headersFor = (r) =>
  r.headers ||
  (headerRecords.find((h) => h.url === r.url)?.headers) ||
  undefined

// 主 API host：请求最多的非静态资源 host（排除 .js/.css/静态）
const hostCount = new Map()
for (const r of requests) {
  try {
    const u = new URL(r.url)
    const isStatic = /\.(js|css|png|jpg|svg|ico|woff2?|json)$/i.test(u.pathname) && !/open-apis|\/api\//.test(u.pathname)
    if (isStatic) continue
    hostCount.set(u.host, (hostCount.get(u.host) || 0) + 1)
  } catch { /* ignore */ }
}
const apiHost = [...hostCount.entries()].sort((a, b) => b[1] - a[1])[0]?.[0] || ''
const base = apiHost ? `https://${apiHost}` : ''

// 端点
const endpoints = new Map()
for (const r of requests) {
  try {
    const u = new URL(r.url)
    if (u.host !== apiHost) continue
    if (/\.(js|css|png|svg|ico|woff2?)$/i.test(u.pathname)) continue
    const key = `${r.method} ${u.pathname}`
    if (!endpoints.has(key)) {
      endpoints.set(key, { method: r.method, path: u.pathname, body: r.body ? safeParse(r.body) : undefined, status: r.response?.status })
    }
  } catch { /* ignore */ }
}

// Cookie 名（请求 Cookie + Set-Cookie）+ 出现频次
const cookieFreq = new Map()
for (const r of requests) {
  const ck = headersFor(r)?.Cookie || headersFor(r)?.cookie
  if (ck) for (const part of ck.split(';')) {
    const n = part.split('=')[0].trim()
    if (n) cookieFreq.set(n, (cookieFreq.get(n) || 0) + 1)
  }
  const sc = r.response?.setCookie
  if (sc) for (const c of sc) {
    const n = c.split(';')[0].split('=')[0].trim()
    if (n) cookieFreq.set(n, (cookieFreq.get(n) || 0) + 1)
  }
}
const cookies = [...cookieFreq.entries()].sort((a, b) => b[1] - a[1]).map(([name, count]) => ({ name, count }))

// query 参数频次（认证参数线索，如 xiaomichatbot_ph）
const queryFreq = new Map()
for (const r of requests) {
  try { for (const [k] of new URL(r.url).searchParams) queryFreq.set(k, (queryFreq.get(k) || 0) + 1) } catch { /* ignore */ }
}
const queryAuth = [...queryFreq.entries()].sort((a, b) => b[1] - a[1]).map(([name, count]) => ({ name, count }))

// 公共请求头（除 Cookie）
const hdrFreq = new Map()
for (const r of requests) {
  for (const k of Object.keys(headersFor(r) || {})) {
    if (/cookie/i.test(k)) continue
    hdrFreq.set(k, (hdrFreq.get(k) || 0) + 1)
  }
}
const commonHeaders = Object.fromEntries(
  [...hdrFreq.entries()].filter(([, c]) => c >= Math.max(2, requests.length / 2)).map(([k]) => [k, '']),
)

// SSO / 认证 host
const ssoHosts = [...new Set(
  redirects.map((r) => safeHost(r.from)).concat(redirects.map((r) => safeHost(r.to))),
)].filter((h) => h && h !== apiHost && /account|pass|sso|login|auth/i.test(h))

// 认证候选 Cookie：带 token/session/service 等字样，或出现在 Set-Cookie 的
const credCandidates = cookies.filter((c) => /token|session|service|auth|user|ph|uid|sid/i.test(c.name))

function safeHost(url) { try { return new URL(url).host } catch { return null } }
function safeParse(s) { try { return JSON.parse(s) } catch { return s } }

const profile = {
  meta: { providerId, name, generatedFrom: file, date: new Date().toISOString().slice(0, 10) },
  provider: {
    id: providerId, name, type: 'builtin',
    authType: 'unverified', apiEndpoint: base, chatPath: 'unverified',
    headers: commonHeaders, tokenCheckMethod: 'POST', tokenCheckEndpoint: 'unverified',
  },
  auth: {
    credentialFields: credCandidates.map((c) => ({
      key: c.name, cookieName: c.name, label: c.name, type: 'password', quoted: false, unverified: true,
    })),
    cookieTemplate: 'unverified',
    queryAuth: queryAuth.filter((q) => /token|ph|auth|sig|sid/i.test(q.name)).map((q) => ({ name: q.name, from: 'unverified' })),
    tokenCheck: { method: 'POST', path: 'unverified', body: {} },
    sso: { detected: ssoHosts.length > 0, sts: ssoHosts.some((h) => /sts|pass/i.test(h)), hosts: ssoHosts },
  },
  endpoints: Object.fromEntries(
    [...endpoints.entries()].map(([k, v]) => [k.replace(/[^a-zA-Z0-9]/g, '_'), v]),
  ),
  models: [],
  notes: [
    `主 API host: ${apiHost || '未识别'}`,
    `共 ${requests.length} 请求、${redirects.length} 跳转`,
    '以下字段为机械提取的“证据/候选”，认证 Cookie 映射、cookieTemplate、tokenCheck、chatPath 需 AI 依 SKILL.md 分析模板确认后填，并实测验证。',
  ],
}

const out = JSON.stringify(profile, null, 2) + '\n'
if (outFile) {
  const { writeFileSync } = await import('node:fs')
  writeFileSync(outFile, out, 'utf8')
  console.log(`画像已写入: ${outFile}`)
} else {
  process.stdout.write(out)
}
