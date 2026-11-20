# Bambu 可打印化 — 验证工具与关键细节

环境：WSL python3（numpy/scipy/trimesh/rtree/networkx/manifold3d）。所有工作文件放 `/mnt/d/...`。

## 1. 3MF 解析要点
- 3MF = ZIP。`3D/3dmodel.model`：`<resources><object>` 的 `<components>` 给出每个 component 的 12 数 transform；`<build><item>` 有整体缩放/平移。
- 网格数据可能放在 `3D/Objects/object_1.model`（超大 XML，直接 `ElementTree.fromstring` 整读最快，几十秒级别）。
- transform 语义：4×3 矩阵两种解释（行/列基）会给出不同结果 —— 以“文字是否正立/贴合”为准判定哪种正确。

## 2. 变换判定技巧
- 文字平面里“字形向上”的局部向量经 transform 后应映射为装配坐标的 +z（打印时 +z 朝上）。
- 若映射成 −z → 该解释会把字上下颠倒，弃用。
- 深度判据：文字实体沿壁法向的区间与墙面 [平面, 内] 的重叠量 = 切割深度。Bambu 负文字常见只重叠 ~0.2mm → 必须重贴/加深。

## 3. 布尔
```python
import trimesh
U = trimesh.boolean.union([box_mesh, patch_mesh], engine='manifold')
F = trimesh.boolean.difference([U, text1, text2], engine='manifold')
```
- 所有操作对象必须先 `process=False` 读取并验证水密；结果再 `remove_unreferenced_vertices()`。

## 4. 验证代码骨架

### 面水平统计（槽底可见性）
```python
nrm = np.cross(V[F[:,1]]-V[F[:,0]], V[F[:,2]]-V[F[:,0]])
nrm /= np.linalg.norm(nrm, axis=1, keepdims=True)
c  = V[F].mean(1)
sel = (nrm[:,1] < -0.9) & (x范围) & (z范围)   # 面向观察者(-y)的面
# 统计 c[sel,1] 的分布 → 表面层(y≈平面) + 槽底层(y≈平面+槽深)
```

### 射线首次命中（验证开通 / 无薄皮 / 不穿墙）
```python
orig = grid起点(面外); dirs = 沿壁法向
loc, idx, _ = m.ray.intersects_location(orig, dirs)
# 每个网格点取第一次命中 y; 期望: 字间距→表面层; 笔划→槽底(≈目标深度);
# 若首层出现≈壁厚/更深处大量命中 = 穿墙或未开通, 异常
```

### 横截面（墙完整性）
固定 z，对 (x,y) 网格从 y=−3 打 +x 射线，命中数奇偶=内部点 → 打印 ASCII 实心图：前几毫米应有连续实体、槽为浅缺口，后面仍是实体。

### ASCII 前视图（快速看清整体）
按 (x,z) 网格扫射线，把首次命中 y 分类成字符（平齐/浅槽/深凹/洞/无面），输出横向 ASCII 图，能立刻发现开口/异形区域。

## 5. 导出与复检
```python
m.export('xxx.3mf')   # 需要 networkx
s = trimesh.load('xxx.3mf')      # Scene → 取 geometry 里的 mesh
g = trimesh.Trimesh(vertices=…, faces=…)
assert g.is_watertight
print(g.extents, g.volume/1000)  # 应为目标打印尺寸 & 体积
```

## 6. 常用数值
- PLA 约 1.24 g/cm³ → 体积(cm³)×1.24 ≈ 克。
- 刻字：成品槽深目标 0.4~0.6mm；层高 0.2 时 = 2~3 层。
- 若来源工程有 plate 缩放 0.8，导出前把网格坐标整体 ×0.8 并平移，使 bbox=打印尺寸、底置 0。
