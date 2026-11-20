# 界面质量与可访问性检查清单

来源：[Vercel Web Interface Guidelines](https://github.com/vercel-labs/web-interface-guidelines)（MIT License，© Vercel）。
已按本项目技术栈（Vue 3 + TypeScript + Element Plus）适配：React 专有 API 译为目标写法，英文文案规则转中文语境，`Hydration Safety` 收窄为 Nuxt/SSR 场景。

**使用方式**：写代码时当作约束；审 UI 时逐条过，输出见文末格式。标注「EP 内置」的项由 Element Plus 自动满足，只需验证未被破坏；其余需手写。

---

## 1. 可访问性（Accessibility）

### 语义与标签

- 纯图标按钮必须有 `aria-label`（`<el-button :icon="Search" aria-label="搜索" />`）
- 表单控件必须有 `<label>` 或 `aria-label`；EP 的 `el-form-item` 的 `label` 已生成关联，**但 `label-position="top"` 之外的自定义布局需手动确认**
- 图片必须有 `alt`；纯装饰图 `alt=""`
- 装饰性图标加 `aria-hidden="true"`
- **优先语义化 HTML，而非堆 ARIA**：能用 `<button>` / `<a>` / `<label>` / `<table>` 就不要用 `<div role="button">`
- 标题层级递增 `<h1>`→`<h6>`，不得跳级；主内容区提供跳转链接（skip link）
- 标题锚点加 `scroll-margin-top`，避免被 sticky 头部遮挡
- 品牌名、代码标识符加 `translate="no"`，防浏览器自动翻译乱码

### 键盘可达

- 可交互元素必须响应键盘（Vue：`@keydown.enter` / `@keydown.space`；**若用 `<button>` 则天然支持，优先换标签**）
- 动作使用 `<button>`，导航使用 `<a>` / `<router-link>`；禁止 `<div @click>` 冒充按钮
- 自定义拖拽/滑动/捏合手势，必须同时提供点击与键盘替代路径（除非手势本身不可替代）
- 媒体控件需键盘可操作；纯装饰媒体对辅助技术隐藏

### 焦点

- 可交互元素必须有可见焦点：EP 默认有，**但自定义 `outline: none` 必须补替代方案**
- 严禁 `outline: none` / `outline-none` 而不提供替代
- 用 `:focus-visible` 替代 `:focus`，避免鼠标点击时也出焦点环
- 复合控件用 `:focus-within` 统一整组焦点样式
- **sticky 头/底部/浮层不得遮挡当前聚焦元素**

### 状态播报

- 异步结果（Toast、校验失败、加载完成）需 `aria-live="polite"`；EP 的 `el-message` 已内置，自定义提示需手写

### 媒体

- 有意义的音视频提供字幕、文字稿或描述

---

## 2. 表单（Forms）

- 输入框必须给 `autocomplete` 与有意义的 `name`（密码管理器依赖）
- 用正确 `type`（`email` / `tel` / `url` / `number`）与 `inputmode`，移动端唤起对应键盘
- **禁止阻止粘贴**（`@paste` + `preventDefault`）——密码字段也不例外
- 标签可点击：EP 的 `el-form-item label` 已关联；手写 `<label>` 需 `for` 或包裹控件
- 邮箱、验证码、用户名关闭拼写检查（`spellcheck="false"`）
- 复选框/单选框：标签与控件共用同一可点区域，不留死区
- 提交按钮在请求开始前保持可用；请求中显示 loading（`el-button :loading`）
- 错误就近显示在字段旁；提交失败时**自动聚焦第一个错误字段**（`formRef.value.validate` + `scrollToField`）
- 占位符以 `…` 结尾并给出示例格式，如「如 name@example.com…」
- 非登录类字段用 `autocomplete="off"`，避免误触发密码管理器
- 有未保存改动时，离开前必须提示（`onBeforeRouteLeave` 或 `beforeunload`）

---

## 3. 交互状态（Hover & Interactive）

- 按钮和链接必须有 `hover` 反馈
- 交互态对比度递增：`hover` / `active` / `focus` 应比常态更醒目，而非等强

---

## 4. 触摸与手势（Touch & Interaction）

- `touch-action: manipulation` 消除双击缩放延迟
- `-webkit-tap-highlight-color` 按设计意图显式设置，而非听任默认灰块
- 弹窗/抽屉/底部面板加 `overscroll-behavior: contain`，防滚动穿透到背景页
- 页面回弹抑制：仅在 `@media (pointer: fine)` 内对 `<html>` 设 `overscroll-behavior: none`；粗指针设备保留默认以支持下拉刷新。**混合输入设备需实测**（`pointer` 只描述主输入，该属性同时会禁用滚动链接与原生侧滑返回）
- 拖拽过程中禁用文本选择，被拖元素加 `inert`
- `autofocus` 谨慎使用：仅桌面端、仅单个主输入框；移动端避免

---

## 5. 动效（Animation）

- 必须尊重 `prefers-reduced-motion`，提供降级版或直接关闭
- 只动 `transform` / `opacity`（走合成层，不触发重排重绘）
- **禁止 `transition: all`**，显式列出属性
- 设置正确的 `transform-origin`
- SVG 变换放在 `<g>` 包装层，配 `transform-box: fill-box; transform-origin: center`
- 动画必须可中断，用户操作能随时打断
- 自动播放且超过 5 秒的动效，需提供暂停/停止/隐藏控件
- 静音装饰性循环动画在 `prefers-reduced-motion` 下必须停止

---

## 6. 排版与文案（Typography & Copy）

- 省略号用 `…`，不是 `...`
- 引号用中文弯引号 `“”`，不用直引号 `"`
- 数字与单位、快捷键、品牌名之间用不换行空格（`10&nbsp;MB`、`⌘&nbsp;K`），防断行拆散
- 加载态文案以 `…` 结尾：「加载中…」「保存中…」
- 数字列、易比较的数值用 `font-variant-numeric: tabular-nums` 对齐
- 标题用 `text-wrap: balance` / `text-pretty`，防孤字成行
- **文案规范（中文语境）**：
  - 用主动语态：「安装 CLI」而非「CLI 将被安装」
  - 数量直接用阿拉伯数字：「8 个部署」而非「八个部署」
  - 按钮标签具体化：「保存 API 密钥」而非「继续」
  - 错误信息给出修复办法或下一步，而不止陈述问题
  - 用第二人称「你」，避免「我们」式自称
  - 英文标题的 Title Case 规则**不适用**于中文；中英混排时按项目语言规范统一

---

## 7. 内容承载与布局（Content & Layout）

- 文本容器必须处理超长内容：`truncate`（单行省略）、`line-clamp-*`（多行）、`break-words`（强制换行）三选一
- **flex 子项需 `min-w-0`**，否则文本省略失效——高频坑
- 处理空状态：空字符串/空数组不得渲染出破损 UI
- 用户生成内容需覆盖极短、正常、极长三种输入
- 通栏布局用 `env(safe-area-inset-*)` 适配刘海屏
- 防多余滚动条：容器 `overflow-x: hidden`，并修掉内容真实溢出（而非掩盖）
- 布局优先用 flex/grid，不用 JS 测量

---

## 8. 性能与图片（Performance & Images）

- 超过 50 条的长列表要虚拟化（`virtua`、`@vueuse/core` 的 `useVirtualList`，或 Element Plus 的 `el-table-v2`）；`.map()` 直出大数组属反模式
- 渲染路径中禁止读布局（`getBoundingClientRect`、`offsetHeight`、`offsetWidth`、`scrollTop`）
- 批量合并 DOM 读写，避免交替触发强制同步布局
- 输入框每敲一次键的开销必须低；能用非受控就别逐键回写
- 为 CDN/静态资源域名加 `<link rel="preconnect">`
- 关键字体 `<link rel="preload" as="font">` 配 `font-display: swap`
- `<img>` 必须显式 `width` / `height`（防 CLS）
- 首屏关键图：`fetchpriority="high"`；首屏以下：`loading="lazy"`
- 循环动图优先用 `<video autoplay muted loop playsinline>` 替代 GIF，并提供静态替代图
- 短的非必要循环：Safari 走 H.264 MP4 的 `<picture>` source，配 `prefers-reduced-motion` 媒体条件与静态兜底

---

## 9. 导航与状态（Navigation & State）

- URL 必须反映状态：筛选、标签页、分页、展开面板都进 query 参数
- 链接用 `<a>` / `<router-link>`，保留 Cmd/Ctrl+点击、中键新开标签能力
- 所有有状态 UI 都应可深链（Vue 中用 `router.push({ query })` 同步，而非仅存组件内 `ref`）
- 破坏性操作必须二次确认或提供撤销窗口，**绝不立即执行**（EP：`el-message-box` / `ElMessageBox.confirm`）

---

## 10. 主题与国际化（Theme & i18n）

- 深色主题在 `<html>` 上设 `color-scheme: dark`（修正滚动条与原生控件配色）
- `<meta name="theme-color">` 与页面背景色一致
- 原生 `<select>` 在深色模式下必须显式设 `background-color` 与 `color`（Windows 下的老问题）
- 日期时间用 `Intl.DateTimeFormat`，数字金额用 `Intl.NumberFormat`，**禁止硬编码格式**
- 语言识别用 `Accept-Language` / `navigator.languages`，**不要按 IP 猜**

---

## 11. SSR / Nuxt 专有（Hydration Safety）

> 纯 Vite SPA 无此问题，仅 Nuxt 或 SSR 场景适用。

- 带 `value` 的输入框需 `@input` 同步，或改用非受控初值
- 日期时间渲染需防服务端/客户端不一致
- 抑制水合警告的指令只在确有必要处使用

---

## 12. 反模式速查表（命中即报）

| 反模式 | 正确做法 |
|---|---|
| `user-scalable=no` / `maximum-scale=1` 禁缩放 | 移除，允许缩放 |
| `@paste` + `preventDefault` 禁粘贴 | 允许粘贴 |
| `transition: all` | 显式列属性 |
| `outline: none` 无焦点替代 | 补 `:focus-visible` 样式 |
| 内联 `@click` 做导航 | 用 `<router-link>` |
| `<div>` / `<span>` 带点击 | 改 `<button>` |
| 图片无尺寸 | 补 `width` / `height` |
| 大数组 `.map()` 不虚拟化 | `el-table-v2` / 虚拟列表 |
| 表单输入无标签 | 补 `label` / `aria-label` |
| 图标按钮无 `aria-label` | 补 `aria-label` |
| 硬编码日期/数字格式 | `Intl.*` |
| `autofocus` 无正当理由 | 移除或限定桌面单输入 |
| 能用压缩视频却用 GIF | `<video>` + 静态兜底 |
| 仅手势操作，无点击/键盘替代 | 补替代路径 |

---

## 13. 审查输出格式

按文件分组，`file:line` 便于编辑器点击跳转。只陈述「问题 + 位置」，修复显而易见时不解释，无寒暄。

```text
## src/views/DiskList.vue

src/views/DiskList.vue:42 - 图标按钮缺少 aria-label
src/views/DiskList.vue:58 - el-dialog 缺少 overscroll-behavior: contain
src/views/DiskList.vue:71 - transition: all → 显式列属性
src/views/DiskList.vue:88 - 表格数字列缺 tabular-nums

## src/components/IconButton.vue

✓ pass
```
