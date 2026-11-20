# 设计令牌提取指南与成套色板

## 1. 从截图提取 Token 的采样顺序

按此顺序读图，每步只做一个判断，避免被细节带偏：

| 步 | 采样对象 | 判断方法 | 产出 |
|----|----------|----------|------|
| 1 | 页面大面积背景 | 取最暗/最亮的大块区域 | `--bg-page` |
| 2 | 卡片/面板底 | 比背景亮一档或半透明 | `--bg-panel` |
| 3 | 输入框/凹陷控件 | 比面板暗一档（深色系）或更白（浅色系） | `--bg-input` |
| 4 | 表头/标题条 | 常为渐变或高饱和色块 | `--bg-thead` |
| 5 | 主行动色 | 主按钮填充色 | `--primary` |
| 6 | 强调/激活色 | 激活 Tab、链接、发光线条 | `--accent` |
| 7 | 语义色 | 成功/警告/危险 | `--success/warning/danger` |
| 8 | 文字三级 | 标题、正文、辅助/占位 | `--text-1/2/3` |
| 9 | 边框 | 面板 1px 描边（常带主色微透明） | `--border`, `--border-glow` |
| 10 | 字号 | 以表格行高、按钮高反推字号 | 4–5 级阶梯 |
| 11 | 间距 | 以面板内边距为基准单位 | 4/8/12/16/24 |
| 12 | 组件清单 | 逐屏点数组件，标注状态 | 覆盖表 |

经验值：
- 深色 UI 的背景层次**只做三级**（页面 → 面板 → 控件），第四级叠加会糊成一团。
- 表头色一般 = 主色降饱和 + 降明度，可先取主色 HSL 后把 S 降至 55~70%、L 降至 22~35%。
- hover 态用主色 12~18% 透明度叠加，不做独立色值。
- 边框发光（`box-shadow: 0 0 .5rem rgba(accent,.35)`）用在「激活/选中」，不要全站铺。

## 2. 成套色板 A：深色科技风（指挥大屏 / 管理后台）

来源：目标标注识别软件截图，实测可用。

```css
:root{
  --bg-page:#0B1626;            /* 页面底 */
  --bg-panel:#0E2033;           /* 面板 */
  --bg-panel-trans:rgba(14,32,51,.92);
  --bg-input:#0A1B2E;           /* 输入框/下拉 */
  --bg-thead:linear-gradient(90deg,#0E3A5C,#123C63);
  --primary:#2E7CF6;            /* 动作 */
  --primary-deep:#1E5FD9;
  --accent:#35E1FF;             /* 状态/高亮 */
  --border:#1E4A6E;
  --border-glow:rgba(53,225,255,.35);
  --text-1:#D6E9FF;
  --text-2:#7FA3C4;
  --text-ph:#5E7F9C;
  --success:#33D1A0;
  --warning:#FFB020;
  --danger:#FF5C5C;
  --row-hover:rgba(30,111,255,.15);
}
```

配套装饰：
- 背景微网格：`repeating-linear-gradient` 双向 1px 线，透明度 3%。
- 四角/顶部氛围光：`radial-gradient(... rgba(accent,.08), transparent 60%)`。
- 切角造型：`clip-path:polygon(.75rem 0,100% 0,calc(100% - .75rem) 100%,0 100%)`。
- 标题发光：`text-shadow:0 0 .75rem rgba(53,225,255,.6)`。

字体：中文 `"Source Han Sans SC","Microsoft YaHei"`；数字/时间 `"DIN Alternate","Roboto Mono",monospace`（DIN 不一定可用，必须写回退）。

## 3. 成套色板 B：浅色企业风（B 端 SaaS）

```css
:root{
  --bg-page:#F5F7FA;
  --bg-panel:#FFFFFF;
  --bg-input:#FFFFFF;
  --bg-thead:linear-gradient(180deg,#FAFBFD,#F0F4F9);
  --primary:#2563EB;
  --primary-deep:#1D4ED8;
  --accent:#0EA5E9;
  --border:#E3E8F0;
  --border-glow:rgba(37,99,235,.25);
  --text-1:#1F2937;
  --text-2:#4B5563;
  --text-ph:#9CA3AF;
  --success:#12B76A;
  --warning:#F79009;
  --danger:#F04438;
  --row-hover:rgba(37,99,235,.04);
  --shadow-panel:0 1px 2px rgba(16,24,40,.06),0 1px 3px rgba(16,24,40,.10);
}
```

浅色系要点：层次靠**阴影 + 1px 边框**而非色阶；表头用中性灰渐变，主色只出现在动作与选中；圆角统一 6px。

## 4. 字号阶梯（2K 基准，1rem=16px）

| 角色 | 深色大屏 | 浅色后台 | 说明 |
|------|----------|----------|------|
| 页面主标题 | 24px / Bold / 字距 .25rem | 20px / Semibold | 大屏可加发光 |
| 面板标题 | 16px / Bold | 16px / Semibold | 配左侧色块或竖线 |
| 正文/表格 | 14px | 14px | 表格数字用等宽 |
| 辅助/标签 | 12–13px | 12–13px | 表头 13px |
| 状态栏/微信息 | 11px | 11–12px | 仅等宽数字 |

行高：正文 1.6，表格 1.4，标题 1.2。

## 5. 间距节奏

8px 栅格，允许 4 作为半档：

| 场景 | 值 |
|------|-----|
| 控件内水平 padding | 12px（小件 8px） |
| 面板内边距 | 16px |
| 表单控件间距 | 12px |
| 分区（面板之间） | 16px |
| 页面左右留白 | 16–24px |
| 表格行高 | 40px（紧凑 36px） |
| 按钮高 | 32px（小 28px） |
| 圆角 | 深色科技风 2–4px；浅色企业风 6px |

## 6. 2K 适配

```css
html{font-size:clamp(8px,0.625vw,16px);} /* 0.625vw = 16px @2560 */
```

- 设计宽度 W 时，根字号公式 `100vw/W*16`，用 `calc` + `clamp` 限制上下界。
- 所有尺寸写 `rem`；1px 边框写 `1px`（不缩放，保持锐利）。
- 表格外壳 `overflow-x:auto` + `table{min-width:...}` 兜底，避免压缩变形。
- 不给每个断点写媒体查询；只在大屏降级时补一条（如标题缩小）。
