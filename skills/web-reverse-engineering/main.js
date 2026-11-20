/**
 * agent-capture — 主进程
 *
 * 独立 Electron 小应用：打开「抓包浏览器窗口」让用户执行操作，用 Recorder
 * 忠实录制网络交互（请求/头/Cookie/响应/跳转），导出 NDJSON 供 AI 分析。
 *
 * 用法： npm start
 */

const { app, BrowserWindow, ipcMain, session, shell, dialog } = require('electron')
const { join } = require('node:path')
const { homedir } = require('node:os')
const { mkdirSync } = require('node:fs')
const { Recorder } = require('./recorder')

const OUT_ROOT = join(homedir(), '.agent-capture', 'out')
const PARTITION = `capture-${Date.now()}` // 每次抓包独立会话（登录态不跨次）
const VERSION = '0.2'

console.log(`[agent-capture] v${VERSION} 启动（recorder 使用 onBeforeRedirect + 防御式 hook）`)

let controlWin = null
let captureWin = null
let recorder = null
let outDir = null

function outRoot() {
  mkdirSync(OUT_ROOT, { recursive: true })
  return OUT_ROOT
}

function createControlWindow() {
  controlWin = new BrowserWindow({
    width: 620,
    height: 640,
    title: 'Agent Capture — 网页操作录制器',
    webPreferences: {
      preload: join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
    },
  })
  controlWin.loadFile(join(__dirname, 'renderer', 'index.html'))
  controlWin.on('closed', () => (controlWin = null))
}

async function startCapture(targetUrl) {
  if (captureWin) return { ok: false, message: '已在抓包中' }
  if (!/^https?:\/\//i.test(targetUrl)) {
    return { ok: false, message: '目标 URL 需以 http(s):// 开头' }
  }

  outDir = join(outRoot(), `session-${Date.now()}`)
  const sess = session.fromPartition(`persist:${PARTITION}`)
  recorder = new Recorder({ outDir })
  try {
    recorder.attach(sess, PARTITION)
  } catch (err) {
    recorder = null
    return { ok: false, message: `Recorder.attach 失败: ${err?.message || err}` }
  }
  recorder.onStats = (s) => {
    if (controlWin && !controlWin.isDestroyed()) {
      controlWin.webContents.send('capture:stats', s)
    }
  }

  captureWin = new BrowserWindow({
    width: 1200,
    height: 850,
    show: false,
    autoHideMenuBar: true,
    title: `抓包浏览器 — ${targetUrl}`,
    webPreferences: { partition: `persist:${PARTITION}`, contextIsolation: true, nodeIntegration: false },
  })
  captureWin.once('ready-to-show', () => captureWin.show())
  captureWin.on('closed', async () => {
    captureWin = null
    if (recorder) recorder.detach()
    recorder = null
    if (controlWin && !controlWin.isDestroyed()) {
      controlWin.webContents.send('capture:ended', { outDir })
    }
  })
  await captureWin.loadURL(targetUrl)

  return { ok: true, outDir, file: recorder.filePath() }
}

function stopCapture() {
  if (captureWin) captureWin.close()
  return { ok: true, outDir }
}

app.whenReady().then(() => {
  createControlWindow()
  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createControlWindow()
  })
})

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit()
})

// ---- IPC ----
ipcMain.handle('capture:start', (_e, url) => startCapture(url))
ipcMain.handle('capture:stop', () => stopCapture())
ipcMain.handle('capture:stats', () => (recorder ? recorder.stats() : { request: 0, header: 0, response: 0, redirect: 0 }))
ipcMain.handle('capture:openOut', () => {
  shell.openPath(outDir || outRoot())
})
ipcMain.handle('capture:pickUrl', async () => {
  const r = await dialog.showOpenDialog(controlWin, {
    properties: ['openFile'],
    filters: [{ name: 'Text', extensions: ['txt'] }],
  })
  return r.canceled ? null : r.filePaths[0]
})
