#!/usr/bin/env node
/**
 * agent-capture — 录制结果分析（AI Agent 用）
 *
 * 读取一次抓包导出的 NDJSON，输出结构化视图，辅助 AI 分析：
 *  - 请求端点表（method/path + body）
 *  - 关键请求头（Cookie / Authorization / 自定义 X-*）
 *  - Set-Cookie（登录 token 签发）
 *  - 跳转链（SSO / STS 登录流程）
 *
 * 用法：
 *   node scripts/analyze.mjs <capture-*.ndjson> [--json]
 * 若省略路径，取 ~/.agent-capture/out 下最新的 capture-*.ndjson。
 */
const { readFileSync, readdirSync, statSync } = await import('node:fs')
const { join } = await import('node:path')
const { homedir } = await import('node:os')

const defaultDir = join(homedir(), '.agent-capture', 'out')
const isJson = process.argv.includes('--json')

function resolveDefaultDir() {
  const cands = [defaultDir, '/mnt/c/Users/adam/.agent-capture/out']
  for (const c of cands) {
    try { if (statSync(c).isDirectory()) return c } catch { /* ignore */ }
  }
  return defaultDir
}

function pickFile(arg) {
  if (arg) return arg
  const dir = resolveDefaultDir()
  const files = readdirSync(dir)
    .filter((f) => /capture-.*\.ndjson$/.test(f))
    .map((f) => ({ f, m: statSync(join(dir, f)).mtimeMs }))
    .sort((a, b) => b.m - a.m)
  if (files.length === 0) {
    console.error(`无抓包文件，目录: ${dir}`)
    process.exit(1)
  }
  return join(dir, files[0].f)
}

const file = pickFile(process.argv[2])
const lines = readFileSync(file, 'utf8').split('\n').filter(Boolean).map((l) => JSON.parse(l))
const requests = lines.filter((l) => l.t === 'request')
const redirects = lines.filter((l) => l.t === 'redirect')

// 端点表
const endpoints = new Map()
for (const r of requests) {
  const u = new URL(r.url)
  const key = `${r.method} ${u.host}${u.pathname}`
  if (!endpoints.has(key)) endpoints.set(key, { method: r.method, host: u.host, path: u.pathname, sample: r })
}

// 关键头去重
const seenHdr = new Set()
const keyHeaders = []
for (const r of requests) {
  if (!r.headers) continue
  const keys = Object.keys(r.headers).filter((k) => /cookie|authorization|^x-|token|sig|device/i.test(k))
  if (!keys.length) continue
  const sig = `${r.url}|${keys.map((k) => `${k}=${String(r.headers[k]).slice(0, 40)}`).join(';')}`
  if (seenHdr.has(sig)) continue
  seenHdr.add(sig)
  keyHeaders.push({ url: r.url, headers: keys.map((k) => ({ k, v: String(r.headers[k]) })) })
}

const setCookies = []
const seenCk = new Set()
for (const r of requests) {
  const sc = r.response?.setCookie
  if (!sc) continue
  for (const c of sc) {
    const name = c.split(';')[0].split('=')[0]
    if (seenCk.has(name)) continue
    seenCk.add(name)
    setCookies.push(c)
  }
}

const result = {
  file,
  counts: { requests: requests.length, redirects: redirects.length },
  endpoints: [...endpoints.values()].map(({ method, host, path, sample }) => ({
    method, host, path,
    body: sample.body ? sample.body.slice(0, 300) : undefined,
    status: sample.response?.status,
  })),
  keyHeaders,
  setCookies,
  redirects: redirects.map((r) => ({ from: r.from, to: r.to })),
  requests: requests.map((r) => ({
    method: r.method, url: r.url,
    status: r.response?.status,
    body: r.body ? r.body.slice(0, 200) : undefined,
    cookie: r.headers?.Cookie || r.headers?.cookie,
  })),
}

if (isJson) {
  process.stdout.write(JSON.stringify(result, null, 2) + '\n')
} else {
  console.log(`=== ${file} ===`)
  console.log(`requests=${result.counts.requests} redirects=${result.counts.redirects}\n`)
  console.log('--- 端点 ---')
  for (const e of result.endpoints) {
    console.log(`  ${e.method} ${e.host}${e.path}  [${e.status ?? '-'}]`)
    if (e.body) console.log(`      body: ${e.body}`)
  }
  console.log('\n--- 关键请求头 ---')
  for (const h of result.keyHeaders) {
    console.log(`  ${h.url}`)
    for (const { k, v } of h.headers) console.log(`      ${k}: ${v.slice(0, 100)}`)
  }
  console.log('\n--- Set-Cookie（token 签发） ---')
  for (const c of result.setCookies) console.log(`  ${c.slice(0, 100)}`)
  console.log('\n--- 跳转链（SSO/STS） ---')
  for (const r of result.redirects) console.log(`  ${r.from}  ->  ${r.to}`)
  console.log('\n（加 --json 输出完整结构化 JSON）')
}
