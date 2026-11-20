# 组件代码配方

所有片段基于深色科技风 Token（见 `design-tokens.md`），换成浅色系只需替换变量。尺寸均为 rem（1rem=16px@2K）。

## 1. 页面壳与切换

```html
<div class="app">
  <header class="topbar">…</header>
  <section class="page active" id="page-list">…</section>
  <section class="page" id="page-detail">…</section>
</div>
<script>
document.querySelectorAll('[data-page]').forEach(function(el){
  el.addEventListener('click',function(e){
    e.preventDefault();
    var id=el.getAttribute('data-page');
    document.querySelectorAll('.page').forEach(function(p){
      p.classList.toggle('active',p.id===id);
    });
    window.scrollTo(0,0);
  });
});
</script>
```

```css
.page{display:none;} .page.active{display:block;}
[data-page]{cursor:pointer;}
```

要点：页面容器只切 `display`，不销毁 DOM（保留滚动/表单状态，原型阶段够用）。

## 2. 顶栏：切角 Tab + 中央标题装甲板

```css
.tab{
  padding:0 1.25rem;height:2.375rem;line-height:2.375rem;font-size:.875rem;
  color:var(--text-2);background:linear-gradient(180deg,#123052,#0D2340);
  border:1px solid var(--border);border-bottom:none;
  clip-path:polygon(.75rem 0,100% 0,calc(100% - .75rem) 100%,0 100%);
  transition:all .2s;
}
.tab.active{
  color:var(--text-1);font-weight:bold;
  background:linear-gradient(180deg,#17548A,#0E3A5C);
  border-color:var(--accent);
  text-shadow:0 0 .5rem rgba(53,225,255,.5);
}
.title-plate{
  height:3.25rem;line-height:3rem;padding:0 4rem;font-size:1.5rem;font-weight:bold;
  letter-spacing:.25rem;
  background:linear-gradient(180deg,#133A5E,#0B1D33);
  clip-path:polygon(2rem 0,calc(100% - 2rem) 0,100% 100%,0 100%);
}
```

切角方向规则：Tab 用「上宽下窄」梯形（贴住内容区），标题用「上窄下宽」装甲板。`clip-path` 会裁掉 border，需要描边时用伪元素或 `filter: drop-shadow`。

## 3. 查询表单行

```css
.query-bar{display:flex;flex-wrap:wrap;gap:.75rem;padding:.875rem 1rem;
  background:var(--bg-panel-trans);border:1px solid var(--border);}
.input,.select{height:2rem;padding:0 .75rem;min-width:11rem;
  background:var(--bg-input);border:1px solid var(--border);border-radius:2px;
  color:var(--text-1);font-size:.8125rem;font-family:inherit;outline:none;}
.input:focus,.select:focus{border-color:var(--primary);
  box-shadow:0 0 .375rem rgba(46,124,246,.4);}
.select{appearance:none;background-image:
  linear-gradient(45deg,transparent 50%,var(--text-2) 50%),
  linear-gradient(135deg,var(--text-2) 50%,transparent 50%);
  background-position:calc(100% - 1rem) 50%,calc(100% - .75rem) 50%;
  background-size:.25rem .25rem;background-repeat:no-repeat;}
```

按钮：主 `linear-gradient(180deg,var(--primary),var(--primary-deep))` + 白字；次 `transparent + 1px var(--border)`，hover 转 accent。

## 4. 面板 + 标题条

```css
.panel{background:var(--bg-panel-trans);border:1px solid var(--border);}
.panel-head{display:flex;justify-content:space-between;align-items:center;
  height:2.75rem;padding:0 1rem;background:var(--bg-thead);
  border-bottom:1px solid var(--border-glow);}
.panel-title{display:flex;align-items:center;gap:.625rem;font-size:1rem;font-weight:bold;}
.panel-title::before{content:"";width:.875rem;height:.875rem;
  background:linear-gradient(135deg,var(--accent),#0E6FA8);
  clip-path:polygon(0 0,100% 0,100% 65%,65% 100%,0 100%);}
```

## 5. 数据表格

```css
table{width:100%;border-collapse:collapse;min-width:75rem;}
thead th{height:2.5rem;padding:0 .75rem;text-align:left;font-size:.8125rem;font-weight:normal;
  background:var(--bg-thead);border-bottom:1px solid var(--border-glow);white-space:nowrap;}
tbody td{height:2.5rem;padding:0 .75rem;font-size:.875rem;
  border-bottom:1px solid rgba(30,74,110,.5);white-space:nowrap;}
tbody tr:nth-child(even){background:rgba(255,255,255,.02);}
tbody tr:hover{background:var(--row-hover);}
.link-op{display:inline-flex;align-items:center;gap:.25rem;margin-right:.75rem;
  color:var(--accent);font-size:.8125rem;cursor:pointer;}
.num{font-family:var(--font-num);}   /* 批号/时间/数值列 */
.empty{color:var(--text-ph);}        /* 空列统一 — */
```

复选框自绘（避免原生控件跳风格）：

```css
.checkbox{width:.9375rem;height:.9375rem;appearance:none;cursor:pointer;
  border:1px solid var(--border);background:var(--bg-input);border-radius:2px;}
.checkbox:checked{background:var(--primary);border-color:var(--primary);
  background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 16 16'%3E%3Cpath d='M3 8l3.5 3.5L13 5' stroke='%23fff' stroke-width='2' fill='none'/%3E%3C/svg%3E");}
```

## 6. 浮动卡片 / 弹窗 / 信息卡

```css
.info-card{position:absolute;top:4.25rem;left:50%;transform:translateX(-50%);
  width:14rem;padding:.625rem .875rem;background:rgba(5,10,8,.82);
  border:1px solid rgba(120,140,60,.4);font-size:.75rem;line-height:1.8;
  font-family:var(--font-num);color:#DCE88A;}
```

- 弹窗不做遮罩（原型演示时遮罩会挡住要展示的内容），用绝对定位贴目标。
- 层级列表：一级无缩进、二级 `margin-left:1rem`，圆点用 `::before` 伪元素定位。
- 选中态用语义色（如绿 `#3AE86A`）或主色，同屏只允许一处高亮。

## 7. 状态栏

```css
.status-bar{display:flex;align-items:center;height:1.875rem;
  background:rgba(10,20,35,.92);border:1px solid var(--border);
  font-size:.6875rem;color:var(--text-2);font-family:var(--font-num);
  overflow:hidden;white-space:nowrap;}
.status-bar span{padding:0 .875rem;border-right:1px solid rgba(30,74,110,.6);}
.status-bar span:last-child{margin-left:auto;border-right:none;}
```

## 8. 内联 SVG 图标

统一写法（24 视图框、`stroke:currentColor`、无填充）：

```html
<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
  <circle cx="12" cy="12" r="9"/><path d="M12 8v5M12 16v.5"/>
</svg>
```

尺寸由 CSS 控制（`.link-op svg{width:.875rem;height:.875rem}`），hover 时父级 `color` 变化即换色。

## 9. 提示条

```css
.alert{display:flex;align-items:center;gap:.625rem;height:2rem;padding:0 .875rem;
  background:#CFE9FB;color:#1B4E8A;font-size:.8125rem;border-radius:2px;}
.alert::before{content:"";width:.5rem;height:.5rem;border-radius:50%;background:var(--primary);}
```

深色界面里的浅色提示条是「截图里真实存在的反差点」，不要为了统一色系改成深色，否则信息层级丢失。

## 10. 分页

```html
<div class="table-footer">
  <span>共 <span class="total-num">2</span> 条数据</span>
  <select class="select" style="min-width:6.5rem;height:1.75rem;">
    <option>25 条/页</option><option>50 条/页</option><option>100 条/页</option>
  </select>
</div>
```

```css
.table-footer{display:flex;justify-content:flex-end;align-items:center;gap:.75rem;
  padding-top:.875rem;font-size:.8125rem;color:var(--text-2);}
.total-num{color:var(--primary);font-family:var(--font-num);}
```
