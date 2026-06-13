#!/usr/bin/env python3
"""
rnote_xhs.py — 小红书数据采集小工具(封装 rnote.dev API)

用途:为揭阳古城文创项目做市场调研时,从小红书批量采集笔记 / 商品 / 话题 / 用户数据,
并把笔记还原成可点击的原文链接,导出成 Markdown / JSON。

依赖:仅标准库(urllib / json),无需 pip 安装。

认证:rnote.dev 用 X-API-Key 头认证;注意必须带浏览器 User-Agent,否则 WAF 会返回 403。
   API Key 不要硬编码进仓库,从环境变量 RNOTE_API_KEY 读取:
       export RNOTE_API_KEY="sk-xxxx"

计费:所有 /api/v2/crawler/* 接口按次计费,默认 $0.01/次(促销 $0.008/次,美元)。
   每次成功调用响应里 "billed": true 表示已扣费。请有节制地采样。

用法示例:
   export RNOTE_API_KEY="sk-xxxx"
   # 搜索"博物馆文创"最热笔记,导出前 20 条带原文链接和 JSON 原始记录
   python3 rnote_xhs.py search "博物馆文创" --sort popularity_descending --out notes.md --json-out notes.json
   # 多关键词批量采样并合并去重
   python3 rnote_xhs.py sweep 文创 冰箱贴 集章本 香薰 帆布包 --pages 2 --out sweep.md --json-out sweep.json
   # 看当前热点选题(热点灵感 feed)
   python3 rnote_xhs.py hot --num 20
   # 搜索商品(带价格/销量)
   python3 rnote_xhs.py products "古城冰箱贴" --out products.md
   # 抽取爆帖一级评论,用于评论区归因
   python3 rnote_xhs.py comments NOTE_ID --sort-strategy like_count --out comments.md --json-out comments.json
   # 取视频笔记直链并下载(视频理解管线第①②步: 取链 -> 下载 -> 交给 whisper/抽帧)
   python3 rnote_xhs.py video NOTE_ID --download clip.mp4
"""
import argparse
import json
import os
import shutil
import sys
import time
import urllib.parse
import urllib.request

BASE = "https://rnote.dev"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"


def _key():
    k = os.environ.get("RNOTE_API_KEY")
    if not k:
        sys.exit("ERROR: 请先 export RNOTE_API_KEY=sk-xxxx")
    return k


def call(path, params=None, method="GET", body=None):
    """调用一个 rnote 接口,返回解析后的 dict。"""
    url = BASE + path
    if params:
        url += "?" + urllib.parse.urlencode({k: v for k, v in params.items() if v not in (None, "")})
    headers = {"X-API-Key": _key(), "User-Agent": UA, "Accept": "application/json"}
    data = None
    if body is not None:
        data = json.dumps(body).encode()
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        detail = e.read().decode(errors="ignore")
        return {"_http_error": e.code, "detail": detail}
    except Exception as e:
        return {"_error": str(e)}


# ---- 接口封装 ----
def search_notes(keyword, page=1, sort_type="general", note_type="不限", time_filter="不限"):
    # sort_type: general(综合) / time_descending(最新) / popularity_descending(最热)
    # time_filter: 不限 / 一天内 / 一周内 / 半年内
    return call("/api/v2/crawler/search/notes", {
        "keyword": keyword, "page": page, "sort_type": sort_type,
        "note_type": note_type, "time_filter": time_filter,
    })


def search_products(keyword, page=1):
    return call("/api/v2/crawler/search/products", {"keyword": keyword, "page": page})


def note_image(note_id):
    return call("/api/v2/crawler/note/image", {"note_id": note_id})


def note_video(note_id):
    """视频笔记详情。响应里带可下载的 mp4 直链(h264/h265 多码率 + backup_urls)。"""
    return call("/api/v2/crawler/note/video", {"note_id": note_id})


def note_comments(note_id, sort_strategy="like_count", cursor="", index=0, page_area="UNFOLDED"):
    # sort_strategy: latest_v2(最新) / like_count(最热)
    return call("/api/v2/crawler/note/comments", {
        "note_id": note_id,
        "cursor": cursor,
        "index": index,
        "pageArea": page_area,
        "sort_strategy": sort_strategy,
    })


def user_posted(user_id, num=20, cursor=""):
    return call("/api/v2/crawler/user/posted", {"user_id": user_id, "num": num, "cursor": cursor})


def hot_inspiration(num=20, cursor=""):
    return call("/api/v2/crawler/creator/hot/inspiration/feed", {"num": num, "cursor": cursor})


def extract_comments(resp):
    """从 note/comments 响应里抽出标准化一级评论列表。"""
    data = ((resp or {}).get("data") or {}).get("data") or {}
    comments = data.get("comments") or []
    out = []
    for c in comments:
        out.append({
            "id": c.get("id") or c.get("comment_id"),
            "content": c.get("content") or c.get("text") or "",
            "liked": to_int(c.get("liked_count") or c.get("like_count")),
            "user": (c.get("user") or {}).get("nickname") or (c.get("user") or {}).get("nick_name"),
            "sub_comment_count": to_int(c.get("sub_comment_count") or c.get("sub_comment_count_l1")),
        })
    return out


# ---- 解析 helper ----
def note_url(note_id, xsec_token=None):
    """把 note_id(+ xsec_token)拼成可点击的小红书原文链接。
    没有 xsec_token 时裸链可能被风控拦截,但仍可作为引用。"""
    if xsec_token:
        return f"https://www.xiaohongshu.com/explore/{note_id}?xsec_token={xsec_token}&xsec_source=pc_search"
    return f"https://www.xiaohongshu.com/explore/{note_id}"


def to_int(x):
    if x is None:
        return 0
    s = str(x).strip().replace("+", "")
    try:
        if s.endswith(("万", "w", "W")):
            return int(float(s[:-1]) * 10000)
        return int(float(s))
    except ValueError:
        return 0


def extract_notes(resp):
    """从 search/notes 响应里抽出标准化笔记列表(含原文链接、封面图、互动数)。"""
    try:
        items = resp["data"]["data"]["items"]
    except (KeyError, TypeError):
        return []
    out = []
    for it in items:
        nc = it.get("note") or it.get("note_card") or {}
        if not nc.get("id"):
            continue
        imgs = nc.get("images_list") or []
        cover = None
        if imgs:
            im = imgs[0]
            cover = im.get("url") or im.get("url_size_large") or im.get("url_default")
        out.append({
            "id": nc.get("id"),
            "type": nc.get("type"),
            "title": nc.get("title") or "",
            "desc": (nc.get("desc") or "")[:200],
            "liked": to_int(nc.get("liked_count")),
            "collected": to_int(nc.get("collected_count")),
            "comments": to_int(nc.get("comments_count")),
            "shared": to_int(nc.get("shared_count")),
            "user": (nc.get("user") or {}).get("nickname") or (nc.get("user") or {}).get("nick_name"),
            "url": note_url(nc.get("id"), nc.get("xsec_token")),
            "cover": cover,
        })
    return out


def _find_first(o, key):
    """递归找第一个出现的 key 的值(响应嵌套层级会变,用这个抗结构漂移)。"""
    if isinstance(o, dict):
        if key in o:
            return o[key]
        for v in o.values():
            r = _find_first(v, key)
            if r is not None:
                return r
    elif isinstance(o, list):
        for v in o:
            r = _find_first(v, key)
            if r is not None:
                return r
    return None


def _find_note(resp):
    """定位第一条 note,兼容两种返回结构:
    - note/image: data.data[0].note_list[0]
    - note/video: data.data[0] 直接就是 note(没有 note_list 包层)。"""
    nl = _find_first(resp, "note_list")
    if isinstance(nl, list) and nl:
        return nl[0]
    inner = ((resp or {}).get("data") or {}).get("data")
    if isinstance(inner, list) and inner and isinstance(inner[0], dict):
        return inner[0]
    return None


def _collect_mp4(o, acc):
    """递归收集所有 .mp4 直链(保序)。"""
    if isinstance(o, dict):
        for v in o.values():
            _collect_mp4(v, acc)
    elif isinstance(o, list):
        for v in o:
            _collect_mp4(v, acc)
    elif isinstance(o, str) and ".mp4" in o and o.startswith("http"):
        acc.append(o)


def extract_video(resp):
    """从 note/video 响应抽出标准化视频信息 + 最优 mp4 直链。
    优先 h264 的 master_url;失败回退到任意 .mp4。返回 None 表示没取到。"""
    n = _find_note(resp)
    if not n:
        return None
    # mp4 在不同笔记里位置不固定:有的在 n["video"],有的散在 note 别处。
    # 优先 video 字段,否则直接搜整条 note,稳。
    src = n.get("video") or n
    best = None
    h264 = _find_first(src, "h264")
    if isinstance(h264, list) and h264 and isinstance(h264[0], dict):
        best = h264[0].get("master_url") or (h264[0].get("backup_urls") or [None])[0]
    urls = []
    _collect_mp4(src, urls)
    seen = set()
    urls = [u for u in urls if not (u in seen or seen.add(u))]
    if not best and urls:
        best = urls[0]
    return {
        "id": n.get("id"),
        "title": n.get("title") or "",
        "desc": n.get("desc") or "",
        "user": (n.get("user") or {}).get("nickname"),
        "liked": to_int(n.get("liked_count")),
        "collected": to_int(n.get("collected_count")),
        "comments": to_int(n.get("comments_count")),
        "duration": _find_first(src, "duration"),
        "best_url": best,
        "all_urls": urls,
    }


def download_video(url, out, referer="https://www.xiaohongshu.com/"):
    """带浏览器 UA + Referer 下载视频直链(rednotecdn 防盗链需要)。"""
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Referer": referer})
    with urllib.request.urlopen(req, timeout=180) as r, open(out, "wb") as f:
        shutil.copyfileobj(r, f)
    return out


def notes_to_md(notes, title="小红书采样"):
    lines = [f"# {title}\n", f"共 {len(notes)} 条,按点赞降序。\n"]
    lines.append("| 关键词 | 赞 | 藏 | 评 | 类型 | 标题 | 原文链接 |")
    lines.append("|---|---|---|---|---|---|---|")
    for n in sorted(notes, key=lambda x: x["liked"], reverse=True):
        t = (n["title"] or n["desc"][:30]).replace("|", "/").replace("\n", " ")
        kw = (n.get("kw") or "").replace("|", "/")
        lines.append(f"| {kw} | {n['liked']} | {n['collected']} | {n['comments']} | {n['type']} | {t} | [链接]({n['url']}) |")
    return "\n".join(lines)


# ---- CLI ----
def main():
    ap = argparse.ArgumentParser(description="小红书数据采集(rnote.dev)")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("search", help="搜索笔记")
    p.add_argument("keyword")
    p.add_argument("--sort", default="popularity_descending")
    p.add_argument("--pages", type=int, default=1)
    p.add_argument("--time-filter", default="不限")
    p.add_argument("--note-type", default="不限")
    p.add_argument("--sleep", type=float, default=1)
    p.add_argument("--out")
    p.add_argument("--json-out")

    p = sub.add_parser("sweep", help="多关键词批量采样合并去重")
    p.add_argument("keywords", nargs="+")
    p.add_argument("--sort", default="popularity_descending")
    p.add_argument("--pages", type=int, default=1)
    p.add_argument("--time-filter", default="不限")
    p.add_argument("--note-type", default="不限")
    p.add_argument("--sleep", type=float, default=1)
    p.add_argument("--out")
    p.add_argument("--json-out")

    p = sub.add_parser("products", help="搜索商品")
    p.add_argument("keyword")
    p.add_argument("--out")

    p = sub.add_parser("comments", help="获取笔记一级评论")
    p.add_argument("note_id")
    p.add_argument("--sort-strategy", default="like_count", choices=["default", "latest_v2", "like_count"])
    p.add_argument("--cursor", default="")
    p.add_argument("--index", type=int, default=0)
    p.add_argument("--page-area", default="UNFOLDED", choices=["UNFOLDED", "FOLDED"])
    p.add_argument("--out")
    p.add_argument("--json-out")

    p = sub.add_parser("hot", help="热点灵感 feed")
    p.add_argument("--num", type=int, default=20)

    p = sub.add_parser("video", help="取视频笔记直链(可下载),供视频理解管线")
    p.add_argument("note_id")
    p.add_argument("--download", help="把最优 mp4 下到该路径(带 UA+Referer)")
    p.add_argument("--json-out", help="保存原始响应 JSON")

    a = ap.parse_args()

    if a.cmd == "search":
        notes = []
        for pg in range(1, a.pages + 1):
            for n in extract_notes(search_notes(
                a.keyword,
                page=pg,
                sort_type=a.sort,
                note_type=a.note_type,
                time_filter=a.time_filter,
            )):
                n["kw"] = a.keyword
                n["page"] = pg
                notes.append(n)
            time.sleep(a.sleep)
        md = notes_to_md(notes, f"小红书「{a.keyword}」采样")
        _emit(md, a.out)
        _emit_json(notes, a.json_out)

    elif a.cmd == "sweep":
        seen = {}
        for kw in a.keywords:
            before = len(seen)
            for pg in range(1, a.pages + 1):
                for n in extract_notes(search_notes(
                    kw,
                    page=pg,
                    sort_type=a.sort,
                    note_type=a.note_type,
                    time_filter=a.time_filter,
                )):
                    if n["id"] not in seen:
                        n["kw"] = kw
                        n["page"] = pg
                        seen[n["id"]] = n
                time.sleep(a.sleep)
            print(f"  {kw}: 新增 {len(seen) - before} 条,累计 {len(seen)} 条", file=sys.stderr)
        md = notes_to_md(list(seen.values()), "小红书多关键词采样")
        _emit(md, a.out)
        _emit_json(list(seen.values()), a.json_out)

    elif a.cmd == "products":
        resp = search_products(a.keyword)
        _emit(json.dumps(resp, ensure_ascii=False, indent=1), a.out)

    elif a.cmd == "comments":
        resp = note_comments(
            a.note_id,
            sort_strategy=a.sort_strategy,
            cursor=a.cursor,
            index=a.index,
            page_area=a.page_area,
        )
        comments = extract_comments(resp)
        _emit_json(resp, a.json_out)
        lines = [f"# 小红书评论采样 {a.note_id}\n", f"共抽出 {len(comments)} 条一级评论。\n"]
        lines.append("| 赞 | 回复 | 评论 |")
        lines.append("|---|---|---|")
        for c in comments:
            text = (c["content"] or "").replace("|", "/").replace("\n", " ")
            lines.append(f"| {c['liked']} | {c['sub_comment_count']} | {text} |")
        _emit("\n".join(lines), a.out)

    elif a.cmd == "hot":
        resp = hot_inspiration(num=a.num)
        print(json.dumps(resp, ensure_ascii=False, indent=1)[:4000])

    elif a.cmd == "video":
        resp = note_video(a.note_id)
        _emit_json(resp, a.json_out)
        info = extract_video(resp)
        if not info or not info.get("best_url"):
            err = resp.get("_http_error") or resp.get("_error") or "结构未匹配(可能不是视频笔记/限流)"
            sys.exit(f"未取到视频直链: {err}")
        print(f"标题: {info['title']}")
        print(f"作者: {info['user']} | 赞 {info['liked']} / 藏 {info['collected']} / 评 {info['comments']}")
        if info.get("duration"):
            print(f"时长: {info['duration']}")
        print(f"最优直链(h264): {info['best_url']}")
        print(f"全部直链({len(info['all_urls'])}):")
        for u in info["all_urls"]:
            print("  " + u)
        if a.download:
            print(f"下载中 -> {a.download} ...", file=sys.stderr)
            download_video(info["best_url"], a.download)
            print(f"written -> {a.download}", file=sys.stderr)


def _emit(text, out):
    if out:
        with open(out, "w", encoding="utf-8") as f:
            f.write(text)
        print(f"written -> {out}", file=sys.stderr)
    else:
        print(text)


def _emit_json(obj, out):
    if not out:
        return
    with open(out, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)
    print(f"written -> {out}", file=sys.stderr)


if __name__ == "__main__":
    main()
