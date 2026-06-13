# AR 3D 动画流程 — 深度技术原理与可复用代码模式

本文件是 SKILL.md 的展开。各阶段的"为什么/怎么实现",以及两个最有价值的可复用代码模式:
**几何动画评估器** 与 **R3F 绑骨驱动 + 道具跟手**。

> 配套:**`invariants.md`** 把下面每条原理绑成"可机检不变量 + 门禁检查项"——本文件讲为什么,那份讲"进每个门怎么自动拦住坑"。

## 目录
1. 各阶段技术原理
2. 代码模式 A：几何动画评估器(确定性 scrub + 正向运动学)
3. 代码模式 B：R3F 加载绑骨 GLB + 找骨 + 驱动 + 道具 parent 到手骨
4. 代码模式 C：Tripo API 全自动(见 scripts/tripo_gen.py)
5. AR/MindAR 与 iOS-WebKit 要点

---

## 1. 各阶段技术原理

**概念层(扩散模型)**：文生图从噪声按文本条件迭代去噪;图生图/参考条件把参考图编码进条件,
模型在去噪时"注意"参考 → 保持 IP 一致性。这就是对版角色必须用图生图(带参考)、纯文生锁不住既有长相的原因。

**图生3D(TRELLIS/Tripo 等生成式重建)**：输入图(可多视图)编码后,3D 生成网络预测一种 3D 表示
(结构化隐空间 / 3D 高斯 / 隐式占据场),再抽取带贴图网格(marching cubes + UV 贴图烘焙)。
重建的是输入图里的姿势(姿势烘进几何);多视图给更多约束 → 背面更可信。输出单个静态网格,需清理/减面。

**自动绑骨(UniRig / Tripo animate_rig)**：学习模型为任意网格预测骨架(关节层级)+ 蒙皮权重。
变形 = 线性混合蒙皮(LBS):顶点 v' = Σ_i w_i · (B_i · invBind_i) · v
(每根骨当前世界矩阵 B_i × 该骨逆绑定矩阵,按权重 w_i 加权)。
prerigcheck 先判定拓扑(biped 可绑)。极端姿势下自动蒙皮在肩/肘可能挤压。

**移动端优化**：① 网格简化(meshoptimizer 二次误差边坍缩,蒙皮感知→保权重);
② 贴图缩放+WebP/KTX2;③ 几何压缩(meshopt:量化顶点属性+熵编码,运行时解码器解)。
不用 Draco 是因为其常用解码器走 gstatic CDN(大陆可能被墙);meshopt 解码器随 three/drei 内置。

**基于图像光照 IBL(HDRI)**：HDRI 提供全向高动态范围辐射,经预滤波生成漫反射/镜面环境贴图,
给 PBR 材质真实环境光与反射 → 比纯方向光自然。

**骨骼动画**：pose 是各骨局部变换的函数。程序化=每帧直接写骨四元数;烘焙=glTF 动画轨(关键帧+插值),
three AnimationMixer 按时间采样驱动骨架。语义动作(倒茶)无现成 mocap → 必须手作(K 帧或程序化)。

**MindAR 图像追踪**：离线把目标图编译成多尺度特征点+描述子(`.mind`);运行时相机帧提特征→与目标匹配→
解 PnP 得相机相对目标的 6DoF 位姿矩阵→把 3D 内容按该位姿锚定到目标平面上。WebXR 非必需(纯 CV)。

---

## 2. 代码模式 A：几何动画评估器(最有价值的复用件)

把"动作准不准"变成可自动测的不变量。核心:**动画时间与挂钟解耦**(`pose=f(t)`,冻结 t 可复现),
用正向运动学读关键点世界坐标,断言语义关系(如"工具出口在目标正上方")。

```ts
// 共享状态:埋点引用 + scrub 时间
const S = { scene: null, tip: null /*工具出口Object3D*/, targets: [] /*目标Object3D[]*/, scrub: null };

function applyPose(t) { /* 按 t 设各骨四元数(seat 静态 × pour 相位 slerp) */ }

// 一次调用扫描整段动画,返回轨迹 + 判定,无需渲染/截图
function sweep(t0=0, t1=CYCLE, step=0.2) {
  const tp = new THREE.Vector3(), cp = new THREE.Vector3(), samples = [];
  for (let t=t0; t<=t1; t+=step) {
    applyPose(t);
    S.scene.updateMatrixWorld(true);            // 正向运动学
    S.tip.getWorldPosition(tp);
    let best=Infinity, dy=0;
    for (const c of S.targets){ c.getWorldPosition(cp);
      const h=Math.hypot(tp.x-cp.x, tp.z-cp.z); if(h<best){best=h; dy=tp.y-cp.y;} }
    samples.push({t, e:pourAmount(t), horiz:+best.toFixed(3), dy:+dy.toFixed(3)});
  }
  const pour = samples.filter(s=>s.e>0.85);     // 动作发力相位
  const minH = Math.min(...pour.map(s=>s.horiz));
  return { minHoriz:minH, verdict:{ pass: minH<0.06 /*出口对准目标*/ && /*高于目标口*/ true } };
}
// 暴露给浏览器 eval / agent:window.__rig = { scrub:t=>S.scrub=t, sweep, setPose }
```
配合**运行时调参** `setPose(bone,[x,y,z])`(更新该骨偏移并重算 target),即可在**同一浏览器不导航**地
`eval(setPose…) → eval(sweep())` 快速数值收敛,再用确定性 scrub 抓连环图给视觉 agent 评美学。

## 3. 代码模式 B：R3F 加载绑骨 GLB + 驱动 + 道具跟手

```ts
const gltf = useGLTF("/model-opt.glb");         // drei 默认支持 meshopt
// 自适应取景:Tripo/skinned 包围盒可能偏 → 自己测量归一
const box=new THREE.Box3().setFromObject(gltf.scene); /* 缩放到目标高、居中 */
// 找骨(three 把 mixamorig:Xxx 的冒号去掉)
const map={ mixamorigRightArm:"rightArm", mixamorigRightHand:"rightHand", /*…*/ };
gltf.scene.traverse(o=>{ if(map[o.name]) rig[map[o.name]]={bone:o, rest:o.quaternion.clone()}; });
// 道具 parent 到手骨 → 自动跟手
rightHandBone.add(teapotGroup);
const tip=new THREE.Object3D(); tip.position.set(0.15,0,0); teapotGroup.add(tip); // 出口埋点
// 每帧
useFrame((s)=> applyPose(S.scrub ?? s.clock.elapsedTime));
```
提亮:`<Canvas onCreated={({gl})=>{gl.toneMapping=THREE.ACESFilmicToneMapping; gl.toneMappingExposure=1.5;}}>`。
挂载策略:`React.lazy` + WebGL 探测 + 无 WebGL 回落 2D。

## 4. 代码模式 C：Tripo API 全自动
见 `scripts/tripo_gen.py`(同目录)。命令:
- `python tripo_gen.py i2m <cut.png> <out.glb>`  图生模型(带贴图)
- `python tripo_gen.py prerig <i2m_task_id>`      判可绑性(RIGGABLE/biped)
- `python tripo_gen.py rig <i2m_task_id> <out.glb> mixamo`  自动绑骨(Mixamo 骨)
- `python tripo_gen.py animate <rig_task_id> <preset> <out.glb>`  套预置动作(idle/walk,**非自定义**)
- `python tripo_gen.py balance`  查余额
key 放 `.tripo-key`(gitignore)或环境变量 `TRIPO_KEY`。脚本含代理重试。
注:`animate_retarget` 的 preset 名需查 Tripo 文档;自定义动作不走它。

## 5. AR / iOS-WebKit 要点
- 容器 `absolute inset-0` 防 a-scene 塌成 width:0(iOS 黑屏头号雷)。
- `next.config`:`images:{ unoptimized:true }` 防 next/image iOS 空白。
- 陀螺仪需用户手势内 `DeviceOrientationEvent.requestPermission()`(iOS13+),触控兜底。
- 微信 WKWebView 默认无 `getUserMedia` → 相机 AR 当彩蛋 + 默认 2.5D/2D 降级,不阻断主流程。
- 音频单 MP3/AAC(OGG iOS 不解码),手势解锁,常静音兜底。
- 四版本一致:卡面/识别牌/`.mind`/URL。CI 绿 ≠ 识别可用,真机是最后一公里。
- 详尽排查见 `webar-mindar-ios` skill。
