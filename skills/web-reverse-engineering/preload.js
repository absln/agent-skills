/**
 * agent-capture — preload：向控制页暴露最小 IPC 桥接
 */
const { contextBridge, ipcRenderer } = require('electron')

contextBridge.exposeInMainWorld('capture', {
  start: (url) => ipcRenderer.invoke('capture:start', url),
  stop: () => ipcRenderer.invoke('capture:stop'),
  stats: () => ipcRenderer.invoke('capture:stats'),
  openOut: () => ipcRenderer.invoke('capture:openOut'),
  onStats: (cb) => ipcRenderer.on('capture:stats', (_e, s) => cb(s)),
  onEnded: (cb) => ipcRenderer.on('capture:ended', (_e, info) => cb(info)),
})
