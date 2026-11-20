---
name: bambu-printable
description: 将 3MF/Bambu 工程、CAD/布尔模型整理为可直接在 Bambu Studio / 拓竹打印机打印的单实体水密 STL/3MF（负实体布尔合并、凹刻深度校验、打印尺寸 1:1 烘焙、水密与穿墙检查）；当提到 Bambu、拓竹、3MF、STL、切片、可直接打印、水密/watertight、负实体、布尔、plate scale、刻字深度时自动启用。
---

# bambu-printable

> 把“建模产物/下载工程”变成“拖进 Bambu Studio 就能打的单网格 1:1 文件”，并先自检（水密、槽深、不穿墙）。

---

## 适用场景

| 触发条件 | 说明 |
|---------|------|
| Bambu 工程文件含负实体/文字需固化 | 自行 CSG 成最终单网格 |
| 需要检查某模型能否正常打印 | 水密/破洞/薄壁/刻字深度/穿墙 |
| 从 CAD/STL 批量产出 3MF | 1:1 mm、多文件或多实体 |

| 不适用 | 原因 |
|--------|------|
| 无头参数化建模本身 | 用 `freecad-headless` 技能 |
| 切片参数/打印策略 | 输出建议即可，不做切片 |

---

## 执行步骤

### 1. 环境

```
python3 + numpy scipy trimesh rtree networkx manifold3d（缺则 `pip install --break-system-packages ...`）
工作目录选项目盘符下的实目录（WSL 用 `/mnt/<盘>/…`）：`/tmp` 每条命令结束即清空，产物不能放那里
```

### 2. 解析与坐标重建

```
3MF=ZIP: 3D/3dmodel.model(组件 transform + build item 缩放)
网格在 3D/Objects/object_1.model(XML 可达 80MB, 直接 ElementTree 解析)
逐组件套用 transform 还原到同一装配坐标系; 文字部分用“列向量”解释可保持正立
```

### 3. 布尔固化(负实体/文字必须自算)

```
final = union(所有正体积) − union(所有负体积), engine='manifold'
注意 build 缩放(常见 0.8): 最终网格直接乘缩放, 使成品=真实打印尺寸 1:1
```

### 4. 凹刻处理(可见性)

```
文字厚度实体与墙面重叠 <0.4mm → 必加深:
  a. 贴平: 字前表面贴齐墙面(外留 0.01)
  b. 加厚: 以贴合面为基准把厚度拉伸到目标(成品槽深≥0.4~0.6mm≈3层)
完成后用面统计确认槽底平层可见、墙背后实体完整(不穿透)
```

### 5. 验证

```
m.is_watertight; 体积/bbox 与预期一致
前视(-法向)面按 y 分层 → 应有 表面层 + 槽底层
射线法: 字区首次命中分布 = 表面(0) + 槽底(目标深度), 无首层深洞/穿透
横截面奇偶判定: 槽背后连续实体
```

### 6. 导出

```
trimesh m.export("…/名称.3mf")  (单实体, unit mm; 需 networkx)
或精细 STL; 导出后 load 回来复检 watertight/extents
```

### 6.5 手工 3MF 快速校验（无 trimesh 时）

```python
import zipfile, xml.etree.ElementTree as ET
NS='{http://schemas.microsoft.com/3dmanufacturing/core/2015/02}'
r=ET.fromstring(zipfile.ZipFile('x.3mf').read('3D/3dmodel.model'))
for o in r.findall(f'{NS}resources/{NS}object'):
    vs=o.find(f'{NS}mesh/{NS}vertices').findall(f'{NS}vertex')
    zs=[float(v.get('z')) for v in vs]
    assert max(zs)>min(zs), '0厚度: '+o.get('id')
print('OK')
```

### 7. 一板多件打包(同材料一次打印)

```
数量: 需要 N 份的零件(如行星轮×3、轴×4)在文件里建 N 个独立实例(每实例一个
      <object><mesh> + <item>), 不要布尔合并成一体
朝向(减少支撑/快速打印):
  - 圆柱/轴类: 竖放(轴沿打印 Z), 无支撑
  - 扁平板类: 平放(最大面朝打印床), 无支撑
  - 薄板/门板类: 竖放(长高面竖直), 轴套等竖直特征无支撑; 凸点/把手朝上或靠短桥接
  - 原则: 最大平面朝下、圆柱轴竖直、凸起朝上; 底部悬空小特征(如 R1 半球)可接受微支撑
布局: Bambu A1 = 256×256mm, 排布上限 ≤240mm 留边距(用户打印板更小则按其尺寸再收), 间隙≥6mm
自检: 实例两两包围盒无重叠; 全部在床内; 单个 3MF、单一材料 → 一次任务打完
布局拆分: 零件多时按用途拆 2~3 个打印件文件(如大板/小件/细长件), 数量写进文件名, 便于单独出盘与排错
```

### 8. 手工最小 3MF（无 trimesh 依赖的快速交付）

只有网格/STL、需“拖进切片器即用”时，可直接拼最小内联 3MF（ZIP 三个条目：`[Content_Types].xml`、`_rels/.rels`、`3D/3dmodel.model`）：

```
<model unit="millimeter" xmlns=3MF-core>
 <resources><object id="1..n" type="model">
   <mesh><vertices>…</vertices><triangles>…</triangles></mesh>
 </object>…</resources>
 <build><item objectid="n" transform="行主序12个数"/>…</build>
</model>

要点：
- 对象 id 用纯数字；**name 属性直接中文命名**：`<object id="1" name="恒星架" type="model">`（同零件多份 name 加序号“立柱1”…），Bambu 对象列表即显示中文，勿用 Object_1 默认名
- 网格先合并重复顶点再写 <triangle>；所有网格底面归一到 z=0，且每轴 Range>0（0 厚度会被判“无几何”）
- 同零件 N 份：同一个 <object> + N 个 <item>（不同 transform），勿复制顶点
- 细长件/门板类先绕 X 放平再烘焙坐标；数量/分组在文件名标注
- 生成后回读校验：解析 XML→每对象三轴 Range>0、索引无越界、实例两两不重叠且在床内

**唯一可靠结构 = 内嵌 mesh 单文件**（mesh 直接写在 3dmodel.model 的 <object> 内，ZIP 仅 [Content_Types].xml / _rels/.rels / 3D/3dmodel.model 三条目）。
**勿手工仿造切片器的多文件组件结构**（<component p:path+UUID> + 外部 object_N.model）：拼错即整文件“零体积、对象被移除”。
```

### 9. 导入切片器后的两类提示

- “3mf 文件配置无效，仅加载几何数据”：无切片器配置段所致，几何正常，选打印机/耗材后即可切片
- 提示无几何/加载失败：先查是否 0 厚度网格或非数字对象 id，再改最小内联格式重试

---

## 常见错误

| 问题 | 现象 | 处理 |
|------|------|------|
| 文字反了/太浅 | 正立性、深度都要验 | 用两种矩阵解释试算，选“正立+贴面”者；深度独立控制 |
| 导入尺寸不对 | 忘乘 plate 缩放 | bbox 应对齐打印尺寸(如 133.3×72.7×78.9) |
| 首层命中深洞 | 槽疑似穿墙 | 射线/截面查墙厚与槽深，别把 0.6 厚字在薄墙上打穿 |
| 3MF 导出报缺库 | ModuleNotFoundError | `pip install networkx` 后重导 |
| 多份同零件摆盘 | 误布尔合并成单一体 | 每实例单独 <object id>+<item>，保持可独立移动 |
| 壳体内腔朝下打印 | 需大量支撑/翻面 | 开口朝上(绕X 180°)再打包 |
| 导入提示“配置无效仅加载几何” | 无切片器配置段 | 正常提示，几何完好，选打印机/耗材后切片 |
| 导入提示“无几何对象” | 0 厚度网格或非数字对象 id | 归一化修 z；改用数字 id；回读校验 Range>0 |
| 仿切片器多文件格式失败 | 整文件打不开/零体积对象被移除 | 回退内嵌 mesh 单文件；object 加中文 name |
| FreeCAD Import.export 导 3mf 报成功但文件不存在 | FreeCAD 1.1 Import.export 有 bug | 改用 Mesh.export（产出内嵌结构，可靠） |

---

## 输出

```
./docs/draft/成品.3mf (或 .stl)   # 单实体、水密、1:1、可直接导入 Bambu
校验日志(体积/bbox/槽深/水密)
```

> 验证工具代码与变换/深度细节：`refs/mesh-verification.md`。
> 样例脚本（carve_direct.py / boolean.py / raycheck.py / slice2.py / pack_plate.py）属**项目侧产物**，按项目目录约定存放，不随本技能分发。
