/** agent-capture — 控制页逻辑 */
const $ = (id) => document.getElementById(id)
const urlInput = $('url')
const btnStart = $('start')
const btnStop = $('stop')
const status = $('status')

function setRunning(running) {
  btnStart.disabled = running
  btnStop.disabled = !running
  urlInput.disabled = running
}

btnStart.addEventListener('click', async () => {
  const url = urlInput.value.trim()
  status.textContent = '正在打开抓包浏览器…'
  const r = await window.capture.start(url)
  if (r.ok) {
    status.textContent = `抓包中…\n输出目录: ${r.outDir}`
    setRunning(true)
  } else {
    status.textContent = `启动失败: ${r.message}`
  }
})

btnStop.addEventListener('click', async () => {
  const r = await window.capture.stop()
  status.textContent = `已停止。输出: ${r.outDir}\n把其中的 capture-*.ndjson 交给 AI 分析。`
  setRunning(false)
})

$('openOut').addEventListener('click', () => window.capture.openOut())

window.capture.onStats((s) => {
  $('nReq').textContent = s.request
  $('nHdr').textContent = s.header
  $('nResp').textContent = s.response
  $('nRedir').textContent = s.redirect
})

window.capture.onEnded((info) => {
  status.textContent = `抓包结束。输出: ${info.outDir}`
  setRunning(false)
})
