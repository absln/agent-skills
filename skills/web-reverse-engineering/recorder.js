/**
 * agent-capture — 网络录制器
 *
 * 挂到 Electron 的 BrowserWindow session 上，忠实记录一次网页操作中产生的
 * HTTP 交互。**只负责录制必要信息，不做分析** —— 分析由 AI Agent 读取
 * 导出的 NDJSON 完成（认证画像 / 端点表 / 操作流程）。
 *
 * 每个请求按 `requestId` 关联，记录：
 *  - request : method、url、request body（非 GET）
 *  - headers : 完整 request headers（含 Cookie / Authorization / 自定义头）
 *  - response: 状态码、Set-Cookie 响应头、content-type
 *  - redirect: 跳转链（用于还原 SSO / STS 登录流程）
 *
 * 输出为追加式 NDJSON，便于流式读取与大文件分析。
 */

const { mkdirSync, appendFileSync } = require('node:fs')
const { join } = require('node:path')
const { homedir } = require('node:os')

const MAX_BODY_CHARS = 50000 // 记录单个请求体上限，防止过大

class Recorder {
  constructor({ outDir, onlyHosts = [] }) {
    this.outDir = outDir
    this.onlyHosts = onlyHosts // 为空则记录全部；否则仅记录这些 host
    this.session = null
    this.pending = new Map() // requestId -> 进行中的记录
    this.file = null
    this.count = { request: 0, header: 0, response: 0, redirect: 0 }
    this.onStats = null
  }

  /** 挂到指定 session 开始录制 */
  attach(session, partition) {
    this.session = session
    mkdirSync(this.outDir, { recursive: true })
    this.file = join(this.outDir, `capture-${partition}.ndjson`)
    this.pending.clear()

    const shouldRecord = (url) => {
      if (this.onlyHosts.length === 0) return true
      try {
        return this.onlyHosts.some((h) => new URL(url).host === h)
      } catch {
        return false
      }
    }

    const write = (obj) => {
      if (this.file) appendFileSync(this.file, `${JSON.stringify(obj)}\n`)
    }
    const emitStats = () => {
      if (this.onStats) this.onStats({ ...this.count })
    }
    // 防御式：webRequest 某方法不可用时跳过，绝不 crash
    const wr = session && session.webRequest
    const hook = (method, fn) => {
      if (wr && typeof wr[method] === 'function') wr[method](fn)
      else console.warn(`[recorder] webRequest.${method} 不可用，已跳过`)
    }

    // 请求（method/url/body）
    hook('onBeforeRequest', (details, cb) => {
      try {
        if (shouldRecord(details.url)) {
          let body
          if (details.uploadData && details.uploadData.length > 0) {
            body = Buffer.concat(
              details.uploadData.map((u) => u.bytes ?? Buffer.alloc(0)),
            ).toString('utf8')
            if (body.length > MAX_BODY_CHARS) body = body.slice(0, MAX_BODY_CHARS)
          }
          this.pending.set(details.id, {
            t: 'request',
            id: details.id,
            ts: Date.now(),
            method: details.method,
            url: details.url,
            body,
            headers: undefined,
            response: undefined,
          })
          this.count.request++
          emitStats()
        }
      } catch (e) {
        console.error('[recorder] onBeforeRequest', e)
      }
      cb({})
    })

    // 完整请求头（Cookie / Authorization / 自定义头）
    hook('onBeforeSendHeaders', (details, cb) => {
      try {
        if (shouldRecord(details.url)) {
          const rec = this.pending.get(details.id)
          if (rec) rec.headers = details.requestHeaders
          else {
            this.pending.set(details.id, {
              t: 'request', id: details.id, ts: Date.now(), method: details.method,
              url: details.url, body: undefined, headers: details.requestHeaders, response: undefined,
            })
          }
          this.count.header++
          emitStats()
        }
      } catch (e) {
        console.error('[recorder] onBeforeSendHeaders', e)
      }
      cb({ requestHeaders: details.requestHeaders })
    })

    // 响应（状态码 / Set-Cookie / content-type）
    hook('onHeadersReceived', (details, cb) => {
      try {
        if (shouldRecord(details.url)) {
          const rec = this.pending.get(details.id)
          const setCookie =
            details.responseHeaders?.['set-cookie'] ||
            details.responseHeaders?.['Set-Cookie'] ||
            []
          const resp = {
            status: details.statusCode,
            setCookie: Array.isArray(setCookie) ? setCookie : undefined,
            contentType:
              details.responseHeaders?.['content-type'] ||
              details.responseHeaders?.['Content-Type'],
          }
          if (rec) {
            rec.response = resp
          } else {
            this.pending.set(details.id, {
              t: 'request', id: details.id, ts: Date.now(), method: details.method,
              url: details.url, body: undefined, headers: undefined, response: resp,
            })
          }
          this.count.response++
          emitStats()
        }
      } catch (e) {
        console.error('[recorder] onHeadersReceived', e)
      }
      cb({})
    })

    // 完成：把完整记录落盘（含跳转目标）
    hook('onCompleted', (details) => {
      try {
        if (shouldRecord(details.url)) {
          const rec = this.pending.get(details.id)
          if (rec) {
            rec.ts = Date.now()
            if (details.redirectURL) rec.redirect = details.redirectURL
            write(rec)
            this.pending.delete(details.id)
          } else {
            write({
              t: 'request', id: details.id, ts: Date.now(), method: details.method,
              url: details.url, body: undefined, headers: undefined,
              response: { status: details.statusCode }, redirect: details.redirectURL,
            })
          }
        }
      } catch (e) {
        console.error('[recorder] onCompleted', e)
      }
    })

    // 明确记录跳转（SSO / STS 流程关键）
    hook('onBeforeRedirect', (details) => {
      try {
        if (shouldRecord(details.url)) {
          write({ t: 'redirect', ts: Date.now(), from: details.url, to: details.redirectURL })
          this.count.redirect++
          emitStats()
        }
      } catch (e) {
        console.error('[recorder] onBeforeRedirect', e)
      }
    })
  }

  filePath() {
    return this.file
  }

  stats() {
    return { ...this.count }
  }

  detach() {
    this.session = null
  }
}

module.exports = { Recorder }

if (require.main === module) {
  console.log('[agent-capture] recorder loaded (defensive hook, no onRedirect) v0.2')
}
