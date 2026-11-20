---
name: freecad-headless
description: 用 FreeCADCmd.exe 无头运行 Python 脚本完成 CAD 建模（参数化实体、布尔、齿轮、刻字、装配摆放），产出 FCStd/STL；当用户要求创建或修改 FreeCAD 模型、生成 .fcstd、做 CAD 布尔/齿轮/抽壳/刻字、或提到 FreeCAD/Part工作台/CAD 建模时自动启用。
---

# freecad-headless

> 本机 Windows FreeCAD 1.1.1（`FreeCADCmd.exe`）无头批量建模：全参数化、原生 FCStd、无 GUI 依赖。API 细节与可运行样例见 `refs/freecad-api-notes.md`。

---

## 适用场景

| 触发条件 | 说明 |
|---------|------|
| 从零生成零件/部件模型 | 壳体、齿轮、轴、盖帽等按尺寸参数化建模 |
| 已有 3MF/项目需转 CAD 或补充特征 | 布尔、掏空、开孔、凹/凸刻字 |
| 需要可继续编辑的交付物 | 产出原生 `.fcstd`（特征树可改） |
| 批量/多版本建模 | 改参数重跑脚本即可 |

| 不适用 | 原因 |
|--------|------|
| 纯网格后处理/水密修复/转 3MF | 用 `bambu-printable` 技能 |
| 复杂草图的交互式约束排布 | 无 GUI 难以迭代，提示用户在 FreeCAD 手工完成 |
| 确定切片/打印参数 | 属 Bambu/切片器范畴 |

---

## 执行步骤

### 0. 建模前几何与运动学预检（联动件必做）

齿轮/连杆/行星系等含啮合或相对运动的机构，先算后建：

- 齿轮啮合中心距 = (两轮分度圆直径之和)/2；齿数×模数先核对，勿按“分布半径”拍脑袋留孔
- 行星/差动系先写清“谁固定、谁输入、谁输出”：任两元件若被刚性同速连接则必自锁/卡齿（先做自由度校核）
- 关键孔位/中心距作为脚本顶部参数（不硬编码散落），改一处全局生效
- **配合尺寸从参考件实测，勿拍脑袋**：孔/轴/中心距等两件相配的尺寸，先从参考模型/实物 mesh 实测（如太阳轮中心孔实际 Φ15 而非想当然 Φ8），再留打印间隙（轴孔配合 0.2~0.5mm 单边、胶接可 0.25）；否则打印后装配失败（轴掉/塞不进）

### 1. 搭运行环境与日志

```
# 先定位安装根（以下二选一），下文用 <安装根> 指代
#   where FreeCADCmd.exe                       -> 取其所在目录
#   ls "/c/Program Files/FreeCAD 1.1/bin"
cd <安装根> && cmd.exe /c "FreeCADCmd.exe ./output/scratch/xxx.py"
```

- 控制台异常会被吞 → 脚本内写 UTF-8 日志 + `try/except: traceback.print_exc(file=LOG)`，跑完读日志
- 工作脚本放 `./output/scratch/`（相对项目根，与上方命令一致）

### 2. 建模骨架

```
Part::Box / Part::Cylinder 基元 + Placement 定位
布尔链: Part::Cut(Base,Tool) / Part::Fuse 逐级连接，每步保留下游引用
App::Part 容器分组; App::Link 做装配摆放副本
```

### 3. 按结构选用套路

```
抽壳盒子:   外 Box − 内 Box（内盒按壁厚/底厚内缩，控制开口面）
真渐开线齿轮: 用 involute_gear_points(module,teeth,pa) 生成齿形多边形
            → Part::Extrusion 挤出 → 轴孔 Cylinder Cut → 面槽 Box Cut
凹刻文字:   Draft.makeShapeString(中文须 TTF 绝对路径；**需活动文档**) → 挤出(带 0.05~0.1 越界)
            → Part::Cut; 成品凹深必须 ≥0.4~0.6mm 才可见
曲面刻字:   圆柱侧面必须**逐字环绕**(字面切于柱面、法向朝外)，整行平放会两侧浮空/扎进柱内；
            沉入量 > 字块半宽处弧矢高 R−√(R²−(w/2)²)，否则布尔不闭合
旋转体:     半剖面放在过轴的平面(XZ), Part::Revolution + Axis=(0,0,1)
螺丝/圆角:  提示用户在 GUI 完成(无头不稳)
```

### 4. 校验

```
doc.recompute()
逐个最终实体打印 isValid / len(Solids) / Volume/1000(cm3) / BoundBox 尺寸
**闭合性校验（防零体积）**：每个 Solid 的 Shell 打印 isClosed()/isValid()——开放壳/非流形会导致切片器判定“零体积、对象被移除”
保存后另开一次文件 recompute 复核树与无报错

多实体交付额外校验:
- 每对象 BoundBox 三轴 Range>0(防 0 厚度扁平件)
- 若含装配副本: 两两包围盒不重叠、均在打印床内

尺寸基准不许用 Shape.BoundBox(虚高) 或 optimalBoundingBox()(最小体积**斜 OBB**，圆柱+凸字会算出 61.16 这种歪值)：
用网格 AABB = Mesh.addFacets(shape.tessellate(…)) 后 .BoundBox

刻字件额外反读校验(查体积/包围盒查不出的"镜像"错误)：
把字面三角面栅格化 → 与同字体 matplotlib TextPath 的轮廓算 IoU，并与**水平镜像版**对比；
正版明显高 ⇒ 字序/朝向正确且未镜像(实测正版 0.65~0.92 vs 镜像 0.23~0.47)
```

### 5. 导出

```
doc.saveAs("./docs/draft/名称.FCStd")        # 中文路径 OK
STL: MeshPart.meshFromShape(LinearDeflection=0.12,…) → mesh.write()
转 Bambu 可打印 3MF → 见 bambu-printable 技能
```

---

## 常见错误

| 问题 | 现象 | 处理 |
|------|------|------|
| 异常被吞 | 只见一行 Exception | 写日志文件 + traceback，跑完读日志 |
| `Part::Extrude` 不存在 | addObject 报 not a type | 用 `Part::Extrusion`（Base=面 Feature, Dir=向量） |
| Placement 构造报错 | TypeError: empty parameter list | `p=App.Placement(); p.Rotation=…; p.Base=Vector`（1.1 无 (Rot,Vec) 重载） |
| 旋转体体积为负 | 几何反了 | 反转剖面点序，或检查绕向 |
| 刻字看不见 | 成品凹深仅 ~0.2mm | 下沉文字使槽底成品 ≥0.4~0.6mm，验证墙未穿透 |
| 布尔破面 | 工具与被切面共面 | 工具做 epsilon 越界（表面外留 0.05~0.1） |
| 中文不出字 | ShapeString 失败 | 用 .ttf 不用 .ttc；`C:/Windows/Fonts/STXINGKA.TTF` |
| **整脚本静默不执行** | 只回显版本号，无输出无报错 | `FreeCADCmd` 下 `__name__ != "__main__"` → 去掉 `if __name__ == "__main__":` 守卫（创建脚本一律顶格直跑） |
| 汉字的笔画/洞被填实 | 面积虚高（实测「如」161.9 vs 实际 48.8mm²） | 别用 `Part.makeFace(wires, "Part::FaceMakerBullseye")` 取字面，改用 Draft ShapeString 的 `Shape` |
| 曲面刻字布尔不闭合/出薄片 | 字块两角悬在柱面外 | 沉入量 > 字块半宽处弧矢高 `R−√(R²−(w/2)²)`；平面字块只能**逐字切于**柱面贴 |
| 镜像文字 | 体积/包围盒全对，字却是反的 | 局部 x 轴取 `(−sinθ, cosθ, 0)`（外侧观者的右手方向）；自检 `det(ex,ey,ez)=+1`，交付前做字面反读 IoU |
| 变换后量到的包围盒是"已摆好"的坐标 | 尺寸校验值全错 | `transformShape(m, copy=True)` 实测**也会就地改原形状** → 变换前先把要用的量成数值存下 |
| 导出的网格被压扁成 0 厚度 | 下游/切片器报“无几何” | 底面归一化写 `z-zmin`（勿漏 zmin）；交付前校验每轴 Range>0 |
| 从 WSL 传 POSIX 路径给 Windows 程序 | exportStl 写到别处/出现 ASCII 件 | Windows 程序一律用 Windows 路径；读取时兼容 ASCII 与 Binary 两种 STL |
| 多部件交付混乱 | 版本/源文件不同步 | 建模总文件唯一（如工程名.FCStd），对象中文命名；打印件由其派生并校验尺寸 |
| 拿到别人的 FCStd 只有 Part::Feature 无参数 Shape | 改不了参数 | 冻结 Shape 无法微调，只能重建（Part 基元+布尔重写）；重建前先从旧 Shape 实测关键尺寸 |

---

## 输出

```
./docs/draft/xxx.FCStd                     # 主交付(特征树可编辑)
./docs/draft/零件名.stl                     # 每零件精细网格 STL
./output/scratch/*.py                    # 可复用建模脚本（与 §1 同一目录）
```

> 输出目录以**项目**的 `目录约定` / `README.md` 为准（如 `creator/output/`）；遇已有工程先按其现有导出工具口径（如 `export_util.py`），别另起一套。

> 详细 API 事实表、齿轮/旋转体/**曲面环绕刻字**配方、**字面反读校验**与本机实测脚本清单：`refs/freecad-api-notes.md`
