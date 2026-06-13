# 知识图谱 schema(本 references/ 目录的统一结构约定)

> 本目录是一个 **markdown 支撑的知识图谱**:markdown 是真源,图是投影。
> 现在不上图数据库;等"读不动了 / 要程序化查询 / 要可视化"再写个 graphify 脚本把下面的
> frontmatter 边吐成图。**所有知识都是可证伪的主张,不是事实**——每条带生命周期,假设变了就翻。

## 三层文件
- `pipeline-detail.md` — **原理层**(为什么):耐久,几乎不过时。
- `invariants.md` — **检查层**(每个门必须满足什么):可机检,blocker 拦坑。
- `world-map.md` + `paths/*.md` — **选型层(世界地图)**:有哪些路、原理、实际效果差、何时选谁。

三层用 `[[wiki-link]]` / ID 交叉引用,合起来是一张图。

## 节点类型(node types)
| type | 含义 | 住在哪 |
|---|---|---|
| `Stage` | 管线阶段(图生3D / 绑骨 / 动画…) | world-map.md / paths 文件级 |
| `Path` | 某阶段下的一条选项(Tripo / UniRig / Mixamo重定向…) | paths/*.md 的 `###` 小节 |
| `Principle` | 底层原理(扩散→3D、LBS蒙皮…) | pipeline-detail.md |
| `Invariant` | 可机检不变量(INV-*) | invariants.md |
| `Axis` | 决策轴(绑骨就绪度、质量上限、授权…) | world-map.md |
| `Evidence` | **我们自己的实测**(A/B 结果)= 金标准 | paths 的"我们的实测"节 |

## 边类型(edge types)
`has-option`(Stage→Path) · `implements`(Path→Principle) · `alternative-to`(Path↔Path) ·
`rates`(Path×Axis→值,**带 source/date/confidence**) · `triggers`(Path/Stage→Invariant) ·
`supports`/`refutes`(Evidence→某条边/主张) · `deepens-into`(Path→子Path) ·
`supersedes`/`superseded_by`(主张修订链)

> **比较即边**:任何"X 在轴 Z 上优于 Y"都是一条带出处的 `rates`/比较边,不是无主的表格单元格。
> 表格只是这些边的人类可读投影。

## 生命周期字段(每个 Path / Invariant / 比较主张都带)
```
status:        proposed | validated | contested | deprecated
confidence:    high | medium | low
scope:         "这条主张在什么前提下为真"        # 最关键
falsifier:     "什么证据会推翻它"                # 自带证伪条件
evidence:      [[Evidence 节点]] / 外部来源(带日期)
last_validated: YYYY-MM-DD
supersedes / superseded_by: <id>                 # 修订时填,旧的标 deprecated 不删
```

## 写法约定(让将来 graphify 能机械解析)
每个 `Path` 小节下放一个 `node` 围栏块,例:
~~~
### Tripo
```node
type: Path
id: path/tripo
parent: stage/char-gen
implements: [principle/diffusion-to-3d, principle/multiview-constraint]
alternative-to: [path/meshy, path/rodin, path/hunyuan3d, path/trellis]
triggers: [INV-TRIPO-VER, INV-TRIPO-1, INV-TRIPO-2, INV-TRIPO-3]
status: validated
confidence: high
scope: "API i2m/mv;Q版角色"
falsifier: "出现几何/绑骨质量明显更优且同等可及的图生3D"
last_validated: 2026-06-09
```
~~~
散文(原理展开、我们的实测叙事)写在围栏块**之外**的正文里——图是骨架,散文是肉。

## 修订纪律(知识会变)
- **不静默改**:推翻一条主张时,先记 `refutes` + 把 status 翻 `contested`,再修订并标 `supersedes`。
  保住"它当初为什么错"的痕迹(2.5 bug 的价值正在于看见它怎么错的)。
- `last_validated` 过期(>90 天)或 `contested` 的主张 → 进 review workflow 的待复检清单。
- review workflow **只提议、不改文档**,人拍板。
