# Agent Skills

## 仓库概览

所有技能遵循[Agent Skills](https://agentskills.io/)格式。技能随仓库一起版本管理。

`skills/` 是**唯一事实源**，每个子目录一个技能，入口为 `SKILL.md`。

## 技能清单

共 **33** 个技能，按职责分组。本段是技能清单的**唯一事实源**：`scripts/audit-skills.mjs` 会做磁盘 ↔ 本表双向比对，缺条目或多条目均报 error。

### 工程规范（5）

| 技能 | 一句话 |
|---|---|
| `http-api-standards` | HTTP 接口契约：URL/字段/参数命名、方法语义、错误体与响应信封、分页、OpenAPI 元数据 |
| `database-standards` | 数据库设计：JSONC Schema、类型映射、`$base` 继承、ref 外键、状态枚举、迁移规范 |
| `backend-python-standards` | Python 后端：项目结构、类型系统、异常处理、异步、FastAPI、数据访问、测试、安全 |
| `backend-rust-standards` | Rust 后端：Cargo workspace、错误分层、Tokio、Axum、SQLx、测试、安全 |
| `frontend-standards` | 前端：Vue 3 + TS + Element Plus 架构约定、CRUD 工作流、状态管理、a11y 门槛 |

### 阶段编排（4）

| 技能 | 一句话 |
|---|---|
| `system-design` | 想法 → 需求（编号+验收标准）→ 方案设计 → 任务分解，四阶段门禁 |
| `system-development` | 开发阶段入口：取任务 → 方案 → 编码 → 单测 → 集成 → 部署 → 提交 |
| `system-ui-design` | UI 原型：骨架线框 → 设计令牌 → 高保真单文件 HTML（字段取自真实契约） |
| `creative-pipeline` | 创作五步流程：需求确认 → 勘察 → 方案 → 制作 → 交付，含门禁与红线 |

### 元技能与项目管理（3）

| 技能 | 一句话 |
|---|---|
| `skill-creator` | 把项目经验/技术决策/重复模式提炼成标准技能文件 |
| `task-manager` | 项目管理 MCP 唯一入口 + 周报/季报/绩效生成、RTM、数据门禁巡检 |
| `weekly-report` | 周报 xlsx 版式规范与模板套用；取数生成流程走 `task-manager` §6 |

### 文档产出与可视化（7）

| 技能 | 一句话 |
|---|---|
| `docx-generation` | python-docx / Node docx 生成、读取、修复 Word（中文字体、题注、目录域、COM 校验） |
| `pptx-generation` | python-pptx 生成/改 PPT：16:9 版式库、模板套用、结构质检与 PDF 校验 |
| `pdf-generation` | reportlab + pypdf：md→PDF、合并拆分旋转、水印、加解密、表单填写、交付自检 |
| `docs-generate-china-standard` | GJB 国军标交付文档（SDP/STP/STRP/SRS/SDD 等 16 类） |
| `file-parser` | PDF/Word/PPT/Excel/图片/EPUB → 结构化 Markdown，带置信度与降级轨迹 |
| `drawio-skill` | 生成/编辑/校验可编辑 draw.io 图（架构、ERD、UML、C4、BPMN、网络） |
| `diagram-design` | 45 种 HTML + SVG 图（架构、时序、ER、泳道、象限、雷达、Venn…） |

### 语音 · 动画 · 视频（8）

| 技能 | 一句话 |
|---|---|
| `edge-tts` | uvx edge-tts 文字转语音：多语种音色、语速/音量/音调、字幕导出 |
| `speaker-diarization-cn` | 中文对话说话人分离与分轨（VAD + 基频 Viterbi + 滑窗嵌入 + 真值评测） |
| `lip-sync-pipeline` | 语音 → 口型帧序列、口型素材换装、过渡帧、说话/静音表演 |
| `asset-pack-contract` | 素材包契约：紧图+bbox、坐标空间、关节、尺寸归一化、质检门槛（**坐标/帧号索引唯一事实源**） |
| `opentoonz-headless-render` | tcomposer 无头渲染 .tnz：相机标定、xsheet 手术、逐帧像素验收 |
| `srt-whiteboard-animation` | SRT → 白板手绘动画：配图策略 → 线稿 → 分区揭示 → 渲染 MP4 |
| `video-transcript-downloader` | 下载视频/提取站点字幕，清洗时间轴与杂音标记生成段落式文本稿 |
| `native-subtitle-quote-image` | 视频 → 3:4 字幕长图：原生字幕截图 / 脚本字幕重绘，取帧裁切拼图质检 |

### CAD 与 3D 打印（2）

| 技能 | 一句话 |
|---|---|
| `freecad-headless` | FreeCADCmd 无头建模：参数化实体、布尔、齿轮、刻字、装配 → FCStd/STL |
| `bambu-printable` | 3MF/CAD → 单实体水密 STL/3MF：负实体布尔、凹刻深度、1:1 烘焙、穿墙检查 |

### 调研与逆向（3）

| 技能 | 一句话 |
|---|---|
| `deep-research` | 多源（HN/Reddit/GitHub/arXiv…）深度调研：采集 → 交叉验证 → 证据分级 → 报告 |
| `deepseek-web-search` | DeepSeek 搜索/Fetch API 联网检索与网页转 Markdown，可作 `deep-research` 兜底 |
| `web-reverse-engineering` | 录制网页真实交互逆认证与业务链：认证画像、端点表、操作链（自带录制器 + 消费ABot） |

### 仿真（1）

| 技能 | 一句话 |
|---|---|
| `machine-simulation` | 一句话 → 单 HTML 文件的可交互 3D 机器仿真（真实比例/材质）+ 20–30s 影片 |

## 安装

```bash
# 安装全部技能
npx skills add absln/agent-skills

# 只装指定的
npx skills add absln/agent-skills --skill <name1> --skill <name12>      # 按技能安装
```

`build-discovery-index.mjs` 产出 `dist/index.json` + 每技能产物（单文件 `.md` 或 `tar.gz`），由 `.github/workflows/publish-skills.yml` 在 `main` 上发 release，供宿主按 URL 拉取。

## 技能结构

```
skills/
  {skill-name}/           # kebab-case 目录名
    SKILL.md              # 必需
    scripts/              # 可选：可执行脚本
      {name}.sh           # Bash
      {name}.mjs          # Node
    refs/                 # 可选：按需加载的参考文档
    assets/ examples/ templates/ lib/
```

`skill-name` 须匹配 `^[a-z0-9]+(?:-[a-z0-9]+)*$` 且 ≤64 字符，全局唯一；`description` ≤1024 字符，写清触发场景。

只含 `SKILL.md` 的技能发布为单文件 `.md`；带辅助文件（`scripts/`、`refs/`、`assets/` 等）则打包为 `tar.gz`。

## 许可

本仓库与 `skills/` 下全部技能均为 **MIT**。许可全文**只在本仓库根放一份**（[`LICENSE`](LICENSE)），各技能目录不再各存副本；每个 `SKILL.md` 的 frontmatter 以 `license: MIT` 声明，便于单独分发时溯源。
