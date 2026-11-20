# FreeCAD 1.1.1 无头建模 — API 事实表与配方（本机实测）

环境：Windows FreeCAD 1.1.1 `FreeCADCmd.exe`，WSL里用`cmd.exe /c "FreeCADCmd.exe /xxx.py"` 调用。

## API 事实（避免重复踩坑）

| 事项 | 结论 |
|---|---|
| 参数化实体 | `doc.addObject("Part::Box"/"Part::Cylinder", …)`；Box 用 `Length/Width/Height`，Cylinder 用 `Radius/Height`(轴=+Z)，再设 `Placement`。 |
| 布尔特征 | `Part::Cut`(`Base`,`Tool`) / `Part::Fuse`；链式；输入变→自动重算。 |
| 2D→3D 挤出 | **`Part::Extrude` 在无头环境不存在**。用 `Part::Extrusion`：`ex=addObject("Part::Extrusion"); ex.Base=<Part::Feature,含平面Face>; ex.Dir=App.Vector(0,0,h)`。 |
| 多边形→面 | 点表 `Part.makePolygon([App.Vector(x,y,z),…])`(不自闭就补一条边)→ `Part.Face(wire)` → 放进 `Part::Feature.Shape`。 |
| 旋转体 | `Part::Revolution`：`Source`=剖面 Feature，`Axis=App.Vector(0,0,1)`，`Angle=360`。剖面须在过轴平面：绕 Z 时剖面放 XZ 面，`x=半径,z=高`。**点序反→体积为负，翻转点序。** |
| Placement | 1.1 不支持 `App.Placement(rot, vec)` 构造 → `p=App.Placement(); p.Rotation=rot; p.Base=App.Vector(...)`。`App.Rotation(App.Vector(1,0,0),90)` 角度为度。 |
| 文字(中文) | `import Draft; Draft.makeShapeString(String=…, FontFile="C:/Windows/Fonts/STXINGKA.TTF", Size=…)`。用 Draft 挤出得到参数化 `Part::Extrusion`；改 String → 自动重算整链。 |
| 文字：字形取面 | `Draft.makeShapeString` **必须有活动文档**（否则报 `No active document. Aborting` 并返回 None）。取 `obj.Shape` 得 Compound 面（汉字的**内轮廓已处理成 hole**），`Shape.extrude(vec)` 即得实体；临时对象末尾 `doc.removeObject` 清掉。一字有分离部件（如「棒」）时挤出后是多个 Solid，需先 `fuse`。 |
| ❌ 别用 Bullseye 取字面 | `Part.makeFace(wires, "Part::FaceMakerBullseye")` 对「分离部件 + 洞」的汉字会静默算错：实测「如」面积 **161.9** vs 实际 **48.8mm²**（多部件并成一块、洞也没挖）。取面只走 Draft。 |
| **脚本入口** | `FreeCADCmd` 执行脚本时 `__name__` **不是** `"__main__"` → `if __name__ == "__main__": main()` 会让**整脚本静默不执行**（无输出、无报错，只回显版本号）。脚本一律顶格直跑。 |
| `Shape.transformShape(m, copy)` | 实测 **`copy=True` 也照样就地改原形状**（返回值是变换后的副本）→ 变换前先把要用的量（包围盒等）量成数值存下，别事后再读那些 Shape。 |
| 变换怎么给 | 除 Placement 外可选矩阵：`m = App.Matrix()` 后直接填 `m.A11…m.A44`（前三列 = 局部三轴、第 4 列 = 平移），再 `transformShape`。**右旋判定：`det(ex,ey,ez) = +1`**，否则出来是镜像文字。 |
| `optimalBoundingBox()` | 是**最小体积的斜 OBB**，不是 AABB：对「圆柱 Φ60 + 侧面凸字」算出 `YLength = 61.16`（真实 AABB 61.00）。尺寸校验用**网格 AABB**（`Mesh.addFacets(shape.tessellate(…))` 后 `.BoundBox`），与项目 `export_util.py` 口径一致。 |
| 导出的 STL 不能反读 | 走了 `decimate` 降采样的 STL 里，平面特征被合并、顶点被挪位 → 事后校验另取 `Shape.tessellate()` 的**全精度**网格（1.1.1 本就忽略 `tol`）。 |
| 容器/链接 | `doc.addObject("App::Part", name)`+`p.addObject(child)`；`child.ViewObject.Visibility=False` 隐藏中间件。装配预览=`App::Link`(`LinkedObject`=最终特征)+`Placement`。 |
| 调试 | 控制台只回显部分输出且吞异常 → 在脚本里开 UTF-8 日志文件+`traceback`。中文 Label/文件名 OK。 |
| STL 精度 | `shape.exportStl()` 默认太粗；用 `MeshPart.meshFromShape(LinearDeflection=0.12, AngularDeflection=0.5)`→`mesh.write()`。 |

## 常用配方

### 抽壳盒子(壁 t、底 tb、顶开口)
外 Box(L×W×H)；内 Box((L−2t)×(W−2t)×(H−tb)) 底抬到 z=tb；Cut。开口面=内盒顶到外盒顶。

### 真渐开线直齿轮
```python
def involute_gear_points(module, teeth, pa_deg=20.0):
    # rp=m·z/2; rb=rp·cos(pa); ra=rp+m; rr=rp−1.25m
    # 半齿厚角 h=π/(2z); 滚角 t=sqrt((r/rb)²−1); 极角 = β ± (t−atan(t))
    # 导侧 β=c−h−inv; 从侧(镜像) β=c+h+inv; 齿顶弧/齿根弧补齐 → 闭合点表
```
生成点表→Face→`Part::Extrusion` 高 6→中心孔 Cylinder Cut→端面槽 Box Cut。样例：`.\output\scratch\build_fidget.py`（m1、z20/z10）。

### 凹刻文字(在竖直壁面)
ShapeString 平面→挤出长度=深度+0.2，挤出端比壁面外多 0.05~0.1→`Part::Cut`。放置时注意：
- 文字必须**正立**（用真实变换逐点验证映射，行映射错误会上下颠倒）
- 成品凹深 = 文字实体伸入壁内的量；设计目标 ≥0.4~0.6mm(打印后)，否则几乎看不见
- 抽壳盒做文字区"盖旧字"：先 union 遮盖块(外表面与壁面平齐)再 cut 文字

### 圆柱侧面环绕刻字（凸字 / 凹字）
平的字贴不到弯的柱面，必须**逐字环绕**：每字单独挤成字块，字面**切于**柱面、法向沿半径朝外。

```python
θ_i = θ_center + degrees(x_i / R)       # 字行切向偏移 x_i 按「弧长」折算成角度
局部 x = (−sinθ, cosθ, 0)               # 切向：外侧观者的"向右"（θ 增大方向）→ 不镜像
局部 y = (0, 0, 1)                      # 竖直向上
局部 z = (cosθ, sinθ, 0)                # 径向朝外（凸字 +z 露出；凹字把字块沉进柱内再 cut）
基点   = (R·cosθ, R·sinθ, z_center)     # 字块自身中心落在柱面上
```

三个必须写进脚本自检的坑：

1. **沉入量 > 弧矢高**：`SINK > R − √(R²−(w/2)²)`（w = 单字宽）。字块是**平面**、柱面是**曲面**，
   离切点越远柱面越"退回"，`SINK` 不够 → 字块两角悬在柱面外 → 布尔不闭合/出薄片。
2. **切平面上点到轴线的距离不是常量**：`ρ = √((R+EMBOSS)² + x²)`，只有 `x ≈ 0`（字心）处才等于 `R+EMBOSS`。
   按「半径恰为 R+EMBOSS」去筛字面三角面会漏掉绝大多数；反读校验用**重心坐标密集采样 + 每格取最大半径**
   （顶面 > R 胜出，柱面恰为 R，侧壁在展开图里只有一条线宽）。
3. **字行居中**：位置用 `(i − (n−1)/2)·cell`。写成 `−W/2 + cell·(i+0.5)` 会整行偏 `gap/2`
   （5 字时中间那个字落到 91.7° 而非 90°，方位角与包围盒校验全跟着歪）。

### 校验：字面反读（字序 / 朝向 / 镜像，一次全验）

把成品实体的字面网格栅格化，与**同一字体文件、由 matplotlib `TextPath` 独立渲染**的轮廓算 IoU；
再与**水平镜像版**比一次。实测：

| 件 | 正版 IoU | 镜像 IoU |
|---|---|---|
| 圆柱侧面环绕凸字（柱面展开，逐字） | 0.72 ~ 0.76 | 0.33 ~ 0.47 |
| 立方体顶面凹字（顶视，逐字） | 0.65 ~ 0.92 | 0.23 ~ 0.47 |

正版明显更高 ⇒ 字序、朝向正确且未镜像。**这类"看着对、其实镜像"的错误，靠体积/包围盒校验查不出来。**

### 旋转体盖帽(ΦD 底座+圆顶+下接杆)
剖面在 XZ：`(0,0)→(D/2,0)→(D/2,h1)→[圆顶圆弧点 (r,y)]→(0,h2)`，绕 Z 旋转；杆=下方 `Part::Cylinder` 后 Fuse。
