# 采集代码示例

> deep-research 技能的素材库。主文件 `SKILL.md` §3.3 / §3.4 只保留要点，完整可运行代码在此。

#### 3.3 简易 API 调用示例（通用版）

```python
import httpx, time

# -- 三源并行采集模板 --

async def collect_hn(query: str, hits_per_page: int = 5) -> list[dict]:
    """Hacker News 采集"""
    r = await httpx.get(
        "https://hn.algolia.com/api/v1/search",
        params={"query": query, "tags": "story", "hitsPerPage": hits_per_page}
    )
    return [{
        "source": "hn",
        "id": h["objectID"],
        "title": h["title"],
        "points": h["points"],
        "date": h["created_at"],
        "text": (h.get("story_text") or "")[:500],
    } for h in r.json().get("hits", [])]


async def collect_github(query: str, per_page: int = 5) -> list[dict]:
    """GitHub 项目采集"""
    r = await httpx.get(
        "https://api.github.com/search/repositories",
        params={"q": query, "sort": "stars", "per_page": per_page},
        headers={"Accept": "application/vnd.github.v3+json"}
    )
    return [{
        "source": "github",
        "id": i["full_name"],
        "name": i["name"],
        "stars": i["stargazers_count"],
        "description": i["description"],
        "url": i["html_url"],
        "language": i.get("language"),
        "last_push": i["pushed_at"],
    } for i in r.json().get("items", [])]


async def collect_stackoverflow(query: str, pagesize: int = 5) -> list[dict]:
    """Stack Overflow 采集"""
    r = await httpx.get(
        "https://api.stackexchange.com/2.3/search",
        params={
            "order": "desc", "sort": "votes",
            "intitle": query, "site": "stackoverflow",
            "pagesize": pagesize
        }
    )
    return [{
        "source": "stackoverflow",
        "id": i["question_id"],
        "title": i["title"],
        "votes": i["score"],
        "answers": i["answer_count"],
        "tags": i.get("tags", []),
        "url": i["link"],
        "accepted": i.get("accepted_answer_id") is not None,
    } for i in r.json().get("items", [])]


# 使用示例：并行采集三个数据源
async def parallel_search(query: str):
    async with httpx.AsyncClient() as client:
        hn_task = collect_hn(query)
        gh_task = collect_github(query)
        so_task = collect_stackoverflow(query)
        
        hn_results, gh_results, so_results = await asyncio.gather(
            hn_task, gh_task, so_task
        )
    
    return {
        "hn": hn_results,
        "github": gh_results,
        "stackoverflow": so_results,
        "total": len(hn_results) + len(gh_results) + len(so_results)
    }
```


#### 3.3.1 中文源采集示例（页面解析）

> 中文源多无公开 JSON API，统一走页面解析。核心：带 UA 抓 HTML → 用 BeautifulSoup/正则提取标题与正文。反爬严时降级搜索引擎快照。

```python
import httpx
from bs4 import BeautifulSoup

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

def collect_baike(word: str) -> dict:
    """百度百科词条（知识/概念定义）"""
    r = httpx.get(f"https://baike.baidu.com/item/{word}", headers=HEADERS, timeout=20)
    soup = BeautifulSoup(r.text, "html.parser")
    summary = soup.select_one("div.J-summary") or soup.select_one("div.lemma-summary")
    return {"source": "baike", "word": word,
            "summary": summary.get_text(strip=True)[:500] if summary else ""}

def collect_csdn(query: str, n: int = 5) -> list[dict]:
    """CSDN 搜索（用主站 so.csdn.net，勿用 blog.csdn.net 会 521）"""
    r = httpx.get("https://so.csdn.net/so/search",
                  params={"q": query}, headers=HEADERS, timeout=20)
    soup = BeautifulSoup(r.text, "html.parser")
    items = []
    for a in soup.select("a")[:n*3]:
        t = a.get_text(strip=True)
        href = a.get("href", "")
        if t and "blog" in href and len(t) > 8:
            items.append({"source": "csdn", "title": t, "url": href})
            if len(items) >= n:
                break
    return items

def collect_zhihu(query: str, n: int = 5) -> list[dict]:
    """知乎搜索（标题可抓，全文需登录，降级用标题+摘要判断）"""
    r = httpx.get("https://www.zhihu.com/search",
                  params={"type": "content", "q": query}, headers=HEADERS, timeout=20)
    soup = BeautifulSoup(r.text, "html.parser")
    return [{"source": "zhihu", "title": d.get_text(strip=True)[:120]}
            for d in soup.select(".ContentItem-title")[:n]]
```


#### 3.4 金融/量化采集示例（腾讯行情）

```python
import urllib.request
import json


def collect_index_kline(
    code: str, name: str, period: str = "day",
    start: str = "2012-01-01", end: str = "2026-01-01", n: int = 2000,
) -> dict:
    """拉取指数/ETF K线数据（腾讯，直连可用）。

    Args:
        code: 证券代码，如 sh000300（沪深300）、sh000922（中证红利）、h30269（中证红利低波）。
        period: day / week / month。
        start/end: 起止日期 YYYY-MM-DD。
        n: 最多返回根数（日K约 2000 根 ≈ 8 年，需更长历史用 week）。

    Returns:
        {name: {closes: [...], first: 起始日, last: 末日, total_ret_pct, annual_ret_pct}}
    """
    url = (f"https://web.ifzq.gtimg.cn/appstock/app/fqkline/get?param="
           f"{code},{period},{start},{end},{n},qfq")
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    data = json.loads(urllib.request.urlopen(req, timeout=15).read().decode())
    d = data.get("data", {})
    if isinstance(d, list) or not d:
        return {name: {}}
    key = list(d.keys())[0]
    kl = d[key].get("qfq" + period) or d[key].get(period) or []
    closes = [float(x[2]) for x in kl]
    if not closes:
        return {name: {}}
    total = (closes[-1] / closes[0] - 1) * 100
    n_years = len(closes) / (52 if period == "week" else 252)
    annual = ((closes[-1] / closes[0]) ** (1 / n_years) - 1) * 100 if n_years > 0 else 0
    return {name: {"closes": closes, "first": kl[0][0], "last": kl[-1][0],
                   "total_ret_pct": round(total, 1), "annual_ret_pct": round(annual, 1)}}


# 用法：策略有效性对比（价值 vs 基准）
# collect_index_kline("sh000922", "中证红利(价值)")  # 需与基准同期对比
# collect_index_kline("sh000300", "沪深300(基准)")
```
