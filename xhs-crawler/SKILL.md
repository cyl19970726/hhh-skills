---
name: xhs-crawler
description: 用 rnote.dev API 采集小红书(RED)数据,做市场调研/选题/竞品扫描。支持搜索笔记/商品/用户、笔记与商品详情、评论、话题、用户主页、热点灵感 feed,并能把笔记还原成可点击原文链接。触发词:"小红书爬虫"、"采集小红书"、"小红书调研"、"xhs"、"rnote"、"文创选题数据"、"竞品笔记扫描"。
metadata:
  source: rnote.dev (小红书数据 API)
  cost: 按次计费,$0.01/次(促销 $0.008/次)
---

# xhs-crawler — 小红书数据采集(rnote.dev)

用 [rnote.dev](https://rnote.dev/docs) 的小红书数据 API 做市场调研、选题分析、竞品/达人扫描。
本目录的 `rnote_xhs.py` 是一个零依赖(纯标准库)的封装脚本,直接 `python3 rnote_xhs.py ...` 即可。

## 何时用

- 调研某品类/话题在小红书的热度、爆款笔记、互动结构(赞/藏/评)
- 找某品类商品的价格带与销量(`products`)
- 扫竞品/标杆账号的内容节奏(`user posted`)
- 看当前平台热点选题(`hot inspiration feed`)
- 把采集结果导成带**原文链接**的 Markdown 交付物

> ⚠️ 这是**只读采集 + 社交互动**接口。**没有"发帖/发布笔记"接口** —— 它能告诉你"发什么",不能替你"发出去"。发布仍需官方号/达人或第三方发布工具。

## 认证 & 计费(重要)

- 认证:HTTP 头 `X-API-Key: sk-xxxx`(或 `Authorization: Bearer sk-xxxx`)。
- **必须带浏览器 `User-Agent`**,否则 WAF 直接 403(python 默认 UA 会被挡)。
- API Key **不要写进仓库**,从环境变量读:`export RNOTE_API_KEY="sk-xxxx"`。
- 计费:所有 `/api/v2/crawler/*` 按次计费,默认 **$0.01/次**,促销 **$0.008/次**(美元)。
  响应里 `"billed": true` 表示已扣费。余额不足时返回 `{"detail":"余额不足，请充值后重试"}`。
- 充值/管理后台:`https://rnote.dev/admin/login`;定价页:`https://rnote.dev/pricing`;
  实时定价 API(免费、无需 key 也可看):`GET https://rnote.dev/api/public/pricing`。

## 快速开始

```bash
export RNOTE_API_KEY="sk-xxxx"

# 1) 搜"博物馆文创"最热笔记,导出带原文链接的 Markdown
python3 rnote_xhs.py search "博物馆文创" --sort popularity_descending --out notes.md

# 2) 一次扫多个文创品类,合并去重(做品类对比用),同时保留 JSON 原始记录
python3 rnote_xhs.py sweep 文创 冰箱贴 集章本 香薰 帆布包 钥匙扣 立体书签 \
  --pages 2 \
  --out sweep.md \
  --json-out sweep.json

# 3) 看当前热点选题
python3 rnote_xhs.py hot --num 20

# 4) 搜商品(带价格/销量)
python3 rnote_xhs.py products "古城冰箱贴" --out products.json

# 5) 抽取某条爆帖一级评论(用于评论区归因)
python3 rnote_xhs.py comments NOTE_ID \
  --sort-strategy like_count \
  --out comments.md \
  --json-out comments.json

# 6) 取视频笔记直链并下载(视频理解管线第①②步)
python3 rnote_xhs.py video NOTE_ID                      # 只打印 mp4 直链 + 元信息
python3 rnote_xhs.py video NOTE_ID --download clip.mp4  # 顺带下载(带 UA+Referer 绕防盗链)
```

也可以在 python 里 `import rnote_xhs` 直接用 `search_notes / extract_notes / note_url / note_video / extract_video / download_video` 等函数。

## 视频笔记 → 理解管线

`video` 子命令解决"取链 + 下载"(管线第①②步)。`note/video` 端点返回 h264/h265 多码率 mp4
直链(+ backup_urls);`extract_video()` 优先挑 **h264 master_url**,`download_video()` 带浏览器
**UA + Referer** 绕 rednotecdn 防盗链。拿到 mp4 后,后续理解(本仓库后续接):

1. **口播→文字**:`whisper clip.mp4 --language zh` → 逐字稿(工具名/卖点/讲解都在这)。
2. **画面→关键帧**:`ffmpeg -i clip.mp4 -vf "select=gt(scene,0.3)" -vsync vfr kf-%03d.jpg` → 让视觉模型读帧(屏幕字 OCR + 视觉风格)。
3. 逐字稿 + 关键帧 + desc + 评论 → 合成"视频拆解"。

## 接口清单(rnote.dev, base = `https://rnote.dev`)

### 爬虫 / 采集(GET,除标注外)
| 接口 | 用途 | 关键参数 |
|---|---|---|
| `/api/v2/crawler/search/notes` | 搜索笔记 ★最常用 | `keyword*`, `page`, `sort_type`(general/time_descending/popularity_descending), `note_type`(不限/视频笔记/普通笔记), `time_filter`(不限/一天内/一周内/半年内) |
| `/api/v2/crawler/search/products` | 搜索商品(价格/销量) | `keyword*`, `page` |
| `/api/v2/crawler/search/users` | 搜索用户/达人 | `keyword*`, `page` |
| `/api/v2/crawler/search/images` | 搜索图片 | `keyword*`, `page` |
| `/api/v2/crawler/note/image` | 图文笔记详情(正文/全部图) | `note_id*` |
| `/api/v2/crawler/note/video` | 视频笔记详情 | `note_id*` |
| `/api/v2/crawler/note/comments` | 笔记评论 | `note_id*`, `sort_strategy`(latest_v2/like_count) |
| `/api/v2/crawler/note/sub_comments` | 二级评论 | `note_id*`, `comment_id*` |
| `/api/v2/crawler/user/info` | 用户主页信息 | `user_id*` |
| `/api/v2/crawler/user/posted` | 用户发布的笔记 | `user_id*`, `cursor`, `num` |
| `/api/v2/crawler/user/faved` | 用户收藏的笔记 | `user_id*`, `cursor`, `num` |
| `/api/v2/crawler/product/detail` | 商品详情 | `sku_id*` |
| `/api/v2/crawler/product/review/overview` | 商品评论总览 | `sku_id*` |
| `/api/v2/crawler/product/reviews` | 商品评论列表 | `sku_id*`, `page` |
| `/api/v2/crawler/product/recommendations` | 商品推荐 | `sku_id*` |
| `/api/v2/crawler/topic/info` **(POST)** | 话题详情 | JSON body |
| `/api/v2/crawler/topic/feed` | 话题下笔记 | `page_id*`, `sort`(trend/time) |
| `/api/v2/crawler/search/groups` | 搜索群聊 | `keyword*` |
| `/api/v2/crawler/creator/inspiration/feed` | 推荐灵感(选题) | `cursor`, `tab` |
| `/api/v2/crawler/creator/hot/inspiration/feed` | 热点灵感(选题风向) ★ | `cursor`, `num` |

### 社交互动(POST,JSON body)
| 接口 | 用途 |
|---|---|
| `/api/v1/interaction/like` | 点赞笔记 |
| `/api/v1/interaction/collect` | 收藏笔记 |
| `/api/v1/interaction/follow` | 关注用户 |

## 响应结构 & 还原原文链接

`search/notes` 的响应是**三层嵌套**:`resp["data"]["data"]["items"]`,每个 item 的 `note` 字段是笔记卡。
笔记卡里有用的字段:`id`, `xsec_token`, `title`, `desc`, `type`(normal/video), `liked_count`,
`collected_count`, `comments_count`, `shared_count`, `user.nickname`, `images_list[].url`。

**原文链接**(需要 `xsec_token`,否则裸链常被风控拦):

```
https://www.xiaohongshu.com/explore/{note_id}?xsec_token={xsec_token}&xsec_source=pc_search
```

`rnote_xhs.py` 的 `extract_notes()` 已经帮你拼好 `url` 和 `cover`(封面图)。

## 实战提示

- **排序**:做"什么火"用 `popularity_descending`;做"最新趋势"用 `time_descending` + `time_filter=一周内`。
- **扩样**:`sweep --pages 2 --json-out raw.json` 可保留原始记录,后续做人工标签和去噪。
- **互动结构会说话**:收藏/点赞比高 = 攻略/工具型(用户想"存起来照着做");点赞高收藏低 = 冲动娱乐型。做文旅选题优先卡高收藏赛道。评论数高要继续看评论内容或原帖语境,不要只把评论数当正向热度。
- **省钱**:每个关键词搜 1 页(20 条)通常足够定性;要定量再翻页。`sweep` 一次扫多个品类便于横向对比。
- **去噪**:小红书搜索可能混入同名、泛娱乐、考试资料、无关商品等内容。报告里的均值和 Top 榜必须先经过人工标签,不要把 API 返回结果直接当结论。
- **数字单位**:互动数可能是 "1.2万" 这种字符串,`to_int()` 已处理。
- **合规**:采集数据仅供内部调研,不二次分发;对外结论尽量引用可核实的公开来源。

## 揭阳古城项目里的典型用法

```bash
# 多形式文创品类横扫(给产品矩阵立项)
python3 rnote_xhs.py sweep 冰箱贴 徽章 集章本 印章 香薰 帆布包 钥匙扣 胶带 明信片 立体书签 谷子 --out 文创品类扫描.md
# 揭阳本地认知 & 潮汕竞品(冷启动判断)
python3 rnote_xhs.py sweep 揭阳古城 揭阳旅游 进贤门 潮州古城 潮汕文创 --out 本地与竞品.md
# 热门 IP / 拟人化文物选题
python3 rnote_xhs.py sweep 显眼包文物 文物拟人 博物馆IP 故宫文创 甘肃省博 --out IP选题.md
```
