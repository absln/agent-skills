# 数据源目录与预检命令

> deep-research 技能的素材库。主文件 `SKILL.md` §2.1 / §2.3 只保留判据，完整清单与命令在此。

#### 2.1 完整数据源目录（分级）

> **可用性分级说明**（2026-08 实测）：
> - **✅ 直连可用**：本机无需代理可直接访问
> - **🔑 限流/需 key**：源有效，但无 token/key 时被限流或拒绝
> - **🌐 需代理**：国内网络直连不通/超时，需科学上网
> - **❌ 已移除**：源确实不可用，已从本目录删除

**一级：直连可用（优先使用）**

| 数据源 | API 地址 | 认证 | 最佳用途 |
|--------|---------|------|---------|
| Hacker News (Algolia) | `hn.algolia.com/api/v1` | 无 | 产品发布、技术讨论 |
| Reddit (Pushshift) | `api.pullpush.io/reddit` | 无 | 社区口碑、真实抱怨 |
| Lobste.rs | `lobste.rs/newest.json` | 无 | HN 替代，偏技术早期 |
| Dev.to | `dev.to/api` | 无 | 开发者博客、技术教程 |
| Stack Overflow | `api.stackexchange.com` | 无 | 技术方案对比、问题诊断 |
| PyPI | `pypi.org/simple` | 无 | Python 包下载量、版本 |
| npm | `registry.npmjs.org` | 无 | JS 包下载量、版本 |
| arXiv | `export.arxiv.org/api` | 无 | 学术论文、技术前沿 |
| NBER | `nber.org/search` | 无 | 经济/金融权威工作论文（页面解析） |

**二级：量化/金融专用（本技能补充，A 股调研优先）**

| 数据源 | API 地址 | 认证 | 最佳用途 |
|--------|---------|------|---------|
| 腾讯行情 | `qt.gtimg.cn/q={codes}` | 无 | A 股行情、指数历史 K 线（日/周/月）、PE/PB |
| 腾讯K线 | `web.ifzq.gtimg.cn/appstock/app/fqkline/get` | 无 | 指数/ETF 长周期历史数据（实证对比） |
| 中证指数 | `csindex.com.cn` | 无 | 红利/低波/等权指数业绩与编制方案（官方） |
| 雪球 | `xueqiu.com` | 无(反爬风险) | A 股价值/红利投资讨论 |
| 聚宽 | `joinquant.com/view/community` | 无 | A 股量化策略实证文章 |

> 金融/量化调研主题（股票策略有效性、因子实证、指数对比）**优先使用本档**：指数历史数据可直接做长周期对比实证（如价值 vs 基准），这是社区/学术源的强有力补充。

**二级·中文源（知识性 + 软件技术性，国内直连）**

> 中文主题调研（中文资料、国内技术生态、A 股之外的国内行业/产品/技术讨论）优先使用本档。多数源无公开 API，需**页面解析**（抓 HTML 后提取正文），反爬较严时降级用搜索引擎快照。

| 数据源 | 地址 | 类型 | 最佳用途 | 访问方式 |
|--------|------|------|---------|---------|
| 知乎 | `zhihu.com` | 知识/问答 | 深度知识、行业见解、技术讨论（需登录看全文，部分反爬） | 页面解析/搜索 |
| 百度百科 | `baike.baidu.com` | 知识/百科 | 中文概念定义、事实核查、词条 | 页面解析 |
| 简书 | `jianshu.com` | 知识/博客 | 中文技术教程、经验分享 | 页面解析 |
| CSDN | `csdn.net` | 软件技术 | 中文技术博客、教程、问题解决（国内最大技术社区） | 页面解析 |
| 博客园 | `cnblogs.com` | 软件技术 | 中文技术博客（老牌，质量较高） | 页面解析 |
| 掘金 | `juejin.cn` | 软件技术 | 前端/移动/后端技术文章、工程实践 | 页面解析 |
| SegmentFault 思否 | `segmentfault.com` | 软件技术/问答 | 中文技术问答、技术方案对比 | 页面解析 |
| 开源中国 OSCHINA | `oschina.net` | 软件技术 | 国内开源动态、技术资讯、开源项目 | 页面解析 |
| InfoQ 中文 | `infoq.cn` | 软件技术/资讯 | 国内技术会议、架构实践、技术趋势 | 页面解析 |
| Gitee | `gitee.com` | 代码托管 | 国内开源项目（GitHub 镜像/国内项目）、star 热度 | 页面解析/API |

> **中文源采集要点**：
> - 多数无公开 JSON API，统一走**页面解析**：`curl -sL -A "Mozilla/5.0 ..." {url}` 抓 HTML → 正则/BeautifulSoup 提取正文与标题。
> - **反爬注意**：知乎需登录看全文、CSDN 的 `blog.csdn.net` 子域返回 521（用主站 `csdn.net` 搜索入口）、百度百科偶有验证码。遇反爬降级用搜索引擎（必应/百度）快照或换源。
> - **交叉验证**：中文源权威性弱于学术/官方源，结论尽量与 GitHub/arXiv/官方文档交叉印证，避免单一中文博客作为唯一证据。

**三级：限流/需 key（可用但受限）**

| 数据源 | API 地址 | 认证 | 限制 | 最佳用途 |
|--------|---------|------|------|---------|
| GitHub | `api.github.com` | 无/Token | 60 req/h(无) / 5000(有) | 开源项目热度；**无 token 极易 403** |
| Semantic Scholar | `api.semanticscholar.org` | 无/key | 100 req/min(无)；**实测经常 429** | 论文引用网络 |
| NewsAPI | `newsapi.org` | 需 key | 100 req/day | 行业新闻 |
| GNews | `gnews.io/api/v4` | 需 key | 100 req/day | 全球新闻（中文支持好） |
| Product Hunt | `api.producthunt.com/v2` | 需 Token | GraphQL POST | 产品发布、用户评分 |

**四级：需科学上网（国内直连不通，非源本身失效）**

| 数据源 | 说明 | 使用前提 |
|--------|------|---------|
| Wikipedia | 国内 DNS 污染/超时 | 开代理后可直连 API |
| Hugging Face | 国内访问不稳定，实测超时 | 开代理后可用 |
| SSRN | 金融论文库，国内超时 | 开代理后可用 |
| NewsAPI | 国内不通（见三级需 key） | 代理 + key |

> **⚠️ 已移除**：`Investopedia`（Cloudflare 反爬 403，urllib 不可达，浏览器亦需复杂模拟）— 2026-08 确认确实无效。


## 预检命令

#### 2.3 预检命令

```bash
# 社区讨论
curl -sL "https://hn.algolia.com/api/v1/search?query={关键词}&tags=story&hitsPerPage=5"
curl -sL "https://api.pullpush.io/reddit/search/submission?q={关键词}&size=5"

# 代码生态（GitHub 无 token 易 403，失败即视为限流）
curl -sL "https://api.github.com/search/repositories?q={关键词}&sort=stars&per_page=5"
curl -sL "https://pypi.org/simple/{包名}/"  # 查具体包

# 问答/技术
curl -sL "https://api.stackexchange.com/2.3/search?order=desc&sort=votes&intitle={关键词}&site=stackoverflow&pagesize=5"

# 学术/知识
curl -sL "http://export.arxiv.org/api/query?search_query=all:{关键词}&max_results=5"
curl -sL "https://api.semanticscholar.org/graph/v1/paper/search?query={关键词}&limit=1"  # 限流时降级 arXiv

# 金融/量化（A 股调研优先）
curl -sL "https://qt.gtimg.cn/q=sh000300"  # 腾讯行情：指数/股票实时+PE/PB
curl -sL "https://web.ifzq.gtimg.cn/appstock/app/fqkline/get?param=sh000922,day,2020-01-01,2026-01-01,1000,qfq"  # 指数日K（实证对比）
curl -sL "https://www.csindex.com.cn/csindex-home/perf/index-perf"  # 中证指数官方
curl -sL "https://www.nber.org/search?q={关键词}"  # NBER 金融工作论文

# 中文源（知识性 + 软件技术性，页面解析）
curl -sL -A "Mozilla/5.0 (Windows NT 10.0; Win64; x64)" "https://baike.baidu.com/item/{关键词}"  # 百度百科词条
curl -sL -A "Mozilla/5.0 (Windows NT 10.0; Win64; x64)" "https://www.zhihu.com/search?type=content&q={关键词}"  # 知乎搜索（需登录看全文）
curl -sL -A "Mozilla/5.0 (Windows NT 10.0; Win64; x64)" "https://so.csdn.net/so/search?q={关键词}"  # CSDN 搜索（主站入口，勿用 blog.csdn.net）
curl -sL -A "Mozilla/5.0 (Windows NT 10.0; Win64; x64)" "https://www.cnblogs.com/search?q={关键词}"  # 博客园搜索
curl -sL -A "Mozilla/5.0 (Windows NT 10.0; Win64; x64)" "https://juejin.cn/search?query={关键词}"  # 掘金搜索
curl -sL -A "Mozilla/5.0 (Windows NT 10.0; Win64; x64)" "https://segmentfault.com/search?q={关键词}"  # 思否搜索
curl -sL -A "Mozilla/5.0 (Windows NT 10.0; Win64; x64)" "https://www.oschina.net/search?q={关键词}"  # OSCHINA 搜索
curl -sL -A "Mozilla/5.0 (Windows NT 10.0; Win64; x64)" "https://www.infoq.cn/search?keyword={关键词}"  # InfoQ 中文搜索
curl -sL -A "Mozilla/5.0 (Windows NT 10.0; Win64; x64)" "https://gitee.com/search?q={关键词}"  # Gitee 搜索

# 需代理的源（开代理后再测）
curl -sL "https://en.wikipedia.org/w/api.php?action=query&list=search&srsearch={关键词}&format=json"
curl -sL "https://huggingface.co/api/models?search={关键词}&sort=downloads&limit=5"
```
