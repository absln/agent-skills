---
name: frontend-standards
description: 前端开发规范 — 覆盖 Vue 3 + TypeScript + Element Plus 技术栈的架构约定、编码规范、CRUD 工作流、组件设计、状态管理、API 对接、类型安全、界面质量与可访问性（a11y）门槛。所有前端开发任务均应遵循此规范；当编写/修改前端代码、审查 UI、做无障碍检查、设计走查或排查交互细节（焦点、键盘可达、深色模式、长文本截断）时自动启用。
---

# 前端开发规范

本文件是项目前端的**全域开发规范**，定义技术栈、架构约定、编码标准和 CRUD 工作流。所有前端代码编写任务都必须遵循此规范。

## 上游依赖（冲突优先级）

| 契约事实 | 唯一事实源 | 本文件角色 |
|---|---|---|
| 响应信封、错误体、状态码、分页 | `http-api-standards` §4–§6 | TS 侧类型映射 |
| URL 形状、JSON 字段名、查询参数命名（`id`/`size`/`cwd`） | `http-api-standards` §2 | 消费方 |
| 数据库列名（snake_case）/ 列类型 / 枚举值域 | `database-standards`、`docs/schemas/` | 消费方；列名→JSON 字段名的 camelCase 映射见上游 §2 |
| Vue / TS / Pinia / a11y 细节 | **本文件** | 事实源 |

本文件中的信封、错误体、分页类型只是上表的 TS 映射，**不重新定义形状**。口径不一致时以上游为准，按 bug 修正，不当作「项目约定」保留。

---

## 1. 技术栈

| 类别 | 技术 | 版本 |
|------|------|------|
| 框架 | Vue 3（Composition API） | ^3.x |
| 语言 | TypeScript | ^5.x |
| UI 组件库 | Element Plus | ^2.x |
| 状态管理 | Pinia | ^2.x |
| 构建工具 | Vite | ^5.x |
| 路由 | Vue Router | ^4.x |

### 1.1 架构风格

- **组件驱动开发**：页面 = 布局组件 + 业务组件 + 通用组件组合
- **关注点分离**：视图（`.vue`）→ 状态（`stores/`）→ 数据（`services/`），禁止在 `.vue` 中直接调用 axios
- **单向数据流**：组件通过 props 接收数据，通过 emit 向父组件发送事件；跨组件共享状态使用 Pinia Store
- **服务端状态优先**：UI 状态放 Pinia，服务端数据直接走 `services/` 层，不在 Store 中重复缓存

---

## 2. 目录结构约定

```
web/
├── src/
│   ├── assets/          # 静态资源（图片、样式）
│   ├── components/      # 通用组件（可跨页面复用）
│   ├── composables/     # 组合式函数（可复用逻辑）
│   ├── routers/         # 路由配置
│   │   └── index.ts     # 路由注册入口
│   ├── services/        # API 服务层（与后端接口一一对应）
│   │   └── {entity}.ts  # 实体 API 封装
│   ├── stores/          # Pinia 状态管理
│   │   └── {entity}.ts  # 实体 Store
│   ├── types/           # 全局类型定义
│   ├── utils/           # 工具函数
│   └── views/           # 页面组件
│       ├── {Entity}List.vue    # 列表页
│       └── {Entity}Form.vue    # 表单页（新建/编辑）
```

- **`components/` vs `views/`**：通用复用组件放入 `components/`，与路由对应的页面级组件放入 `views/`。
- **`services/` 职责**：仅封装 HTTP 调用，不包含业务逻辑或状态。
- **`stores/` 职责**：管理跨组件共享状态，包含业务逻辑。
- **`composables/` 职责**：封装可复用的有状态逻辑（如表单校验、列表筛选）。

---

## 3. 命名规范

### 3.1 文件命名

| 类型 | 规则 | 示例 |
|------|------|------|
| 页面组件 | PascalCase | `UserList.vue`、`DiskForm.vue` |
| 通用组件 | PascalCase | `SearchBar.vue`、`ConfirmDialog.vue` |
| Service 文件 | snake_case | `disk_service.ts`、`user_service.ts` |
| Store 文件 | snake_case | `disk.ts`、`auth.ts` |
| 类型文件 | snake_case | `disk.ts`、`common.ts` |
| 组合式函数 | camelCase | `usePagination.ts`、`useFormValidation.ts` |

### 3.2 标识符命名

| 类型 | 规则 | 示例 |
|------|------|------|
| 组件名 | PascalCase，多单词 | `DiskList`、`DiskFormDialog` |
| 组合式函数 | `use` 前缀 + PascalCase | `useDiskList`、`useFormSubmit` |
| 变量/函数 | camelCase | `diskList`、`handleSearch`、`fetchDisks` |
| 常量 | UPPER_SNAKE_CASE | `PAGE_SIZE`、`MAX_RETRY` |
| 类型/接口 | PascalCase | `Disk`、`DiskQuery`、`ListResponse<'disks', Disk>` |
| Props | camelCase | `visible`、`diskId` |
| Emits | kebab-case | `@update:visible`、`@submit-success` |

---

## 4. 组件设计原则

### 4.1 基本规则

- 优先使用 `<script setup>` + Composition API，禁止 Options API。
- 每个组件只负责一件事，超过 300 行考虑拆分。
- Props 和 Emits 必须有完整的 TypeScript 类型定义。
- 禁止在模板中使用 `any` 类型变量。

### 4.2 Props 定义模式

```typescript
interface Props {
  visible: boolean;
  diskId?: number;
  readonly title: string;
}

const props = withDefaults(defineProps<Props>(), {
  visible: false,
  diskId: undefined,
});
```

### 4.3 Emits 定义模式

```typescript
const emit = defineEmits<{
  'update:visible': [value: boolean];
  'submit-success': [];
}>();
```

### 4.4 组件通信规则

| 场景 | 方案 |
|------|------|
| 父子组件简单通信 | Props + Emits |
| 跨层级/全局状态 | Pinia Store |
| 兄弟组件通信 | 通过父组件或 Pinia Store |
| 跨组件逻辑复用 | Composables |

---

## 5. 状态管理规范（Pinia）

### 5.1 何时使用 Store

- **必须用 Store**：跨页面/组件共享的状态（如用户信息、权限、全局配置）。
- **建议用 Store**：与后端 CRUD 紧密绑定的实体列表状态。
- **不必用 Store**：仅单个组件内部使用的 UI 状态。

### 5.2 Store 结构

```typescript
// stores/disk.ts
import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import type { Disk } from '@/types/disk';
import { diskService } from '@/services/disk_service';

export const useDiskStore = defineStore('disk', () => {
  // State
  const list = ref<Disk[]>([]);
  const nextCursor = ref<string | null>(null);
  const hasMore = ref(false);
  const loading = ref(false);

  // Getters
  const activeDisks = computed(() => list.value.filter(d => d.status === 'active'));

  // Actions
  async function fetchList(params: CursorParams) {
    loading.value = true;
    try {
      const res = await diskService.list(params); // 已是解包后的信封，不再有 AxiosResponse.data
      list.value = res.disks;                     // 列表键与路径段同名（上游 §5/§6）
      nextCursor.value = res.nextCursor;
      hasMore.value = res.hasMore;
    } finally {
      loading.value = false;
    }
  }

  return { list, nextCursor, hasMore, loading, activeDisks, fetchList };
});
```

- 使用 Setup Store 语法（组合式），不使用 Options Store。
- Action 中的异步调用必须有 try-catch，`finally` 中重置 loading。

---

## 6. API 调用规范

### 6.1 Service 文件结构

```typescript
// services/disk_service.ts
import type { Disk, DiskCreate, DiskUpdate } from '@/types/disk';
import type { CursorParams, ItemResponse, ListResponse } from '@/types/common';

export const diskService = {
  // 信封形状见 types/common.ts（映射自 http-api-standards §5/§6）
  list(params: CursorParams): Promise<ListResponse<'disks', Disk>> {
    return api.get('/api/disks', { params });
  },
  get(id: number): Promise<ItemResponse<'disk', Disk>> {
    return api.get(`/api/disks/${id}`);
  },
  create(data: DiskCreate): Promise<ItemResponse<'disk', Disk>> {
    return api.post('/api/disks', data);
  },
  update(id: number, data: DiskUpdate): Promise<ItemResponse<'disk', Disk>> {
    return api.put(`/api/disks/${id}`, data);
  },
  delete(id: number): Promise<ItemResponse<'removed', boolean>> {
    return api.delete(`/api/disks/${id}`);
  },
};
```

- 每个实体一个 Service 文件，导出同名对象。
- 所有方法必须声明返回值类型。
- 查询参数使用 `{ params }` 传递，不手动拼接 URL。

### 6.2 错误处理

后端错误体唯一形状（见 `http-api-standards` §4）：

```typescript
export interface ApiError {
  code: number;    // 首 3 位 = HTTP 状态码，后 2 位为细分错因
  message: string; // 可直接展示给终端用户
}
```

- Service 层不捕获异常，将错误抛给调用方（Store 或组件）。
- Store 的 Action 中捕获异常：`message` 用于提示，`code` 用于分支，**禁止用 `message` 文本做逻辑判断**。
- 全局通过 Axios 拦截器统一处理 401（清 token + 跳登录）等通用错误；业务错误交给调用方 `catch` 提示。
- 错误提示取 `error.response?.data?.message`，兜底为「操作失败，请稍后重试」，不把 `error.message`（浏览器/网络措辞）直接抛给用户。

---

## 7. 类型安全

### 7.1 基本原则

- **禁止 `any` 类型**，除非有明确注释说明理由且标记 `HACK`。
- 所有函数参数和返回值必须声明类型。
- API 返回数据类型必须与后端 schema 一致，参考 `docs/schemas/` 下的 JSONC 文件。

### 7.2 类型定义位置

| 范围 | 位置 |
|------|------|
| 实体数据类型 | `types/{entity}.ts` |
| 请求/响应类型 | `types/{entity}.ts` |
| 通用类型（分页、响应包装） | `types/common.ts` |
| 组件内部 Props/Emits | 组件文件中定义 |

### 7.3 通用类型定义

> 完整代码见 `refs/types-and-forms.md` →「通用类型定义」。落地时必须守住三条：**信封/分页形状以 `http-api-standards` §4–§6 为唯一事实源**；列表键由调用点具名（`ListResponse<'disks', Disk>`），**禁止退化成 `items`/`data`/`list`**；`PageListResponse` 仅服务历史 offset 接口与 `el-pagination` 兼容层。

---

## 8. 表单规范

### 8.1 Element Plus 表单模式

> 完整模板（`el-form` + `FormInstance` + `FormRules` + 提交前 `validate()`）见 `refs/types-and-forms.md` →「Element Plus 表单模板」

- 必须使用 `el-form` 的 `validate()` 做提交前校验。
- 表单数据使用 `reactive`，规则使用 `FormRules` 类型。
- 校验规则在组件内定义，不抽离到外部。

---

## 9. 表格/列表页规范

### 9.1 列表页结构

结构固定为**搜索区 → 操作栏 → 表格 → 分页**四部分。完整模板见 [refs/list-page-pattern.md](refs/list-page-pattern.md)。

- 分页口径：数据源是 cursor 接口时用「上一页 / 下一页 + hasMore」（由 `nextCursor` 驱动）；`el-pagination` 的 `page`/`page_size` 只服务历史 offset 接口（`PageListResponse`），两套不得混用。

- 表格 `v-loading` 必须绑定 Store 的 loading 状态。
- 删除操作必须有 `el-message-box` 二次确认。
- 查询条件同步到 URL query，保证可刷新、可深链。
- 超过 50 条数据改用 `el-table-v2` 或虚拟列表。

---

## 10. 路由注册规范

```typescript
// routers/index.ts
import type { RouteRecordRaw } from 'vue-router';

const routes: RouteRecordRaw[] = [
  {
    path: '/disks',
    name: 'DiskList',
    component: () => import('@/views/DiskList.vue'),
    meta: { title: '磁盘管理', requiresAuth: true },
  },
  {
    path: '/disks/create',
    name: 'DiskCreate',
    component: () => import('@/views/DiskForm.vue'),
    meta: { title: '新建磁盘', requiresAuth: true },
  },
  {
    path: '/disks/:id/edit',
    name: 'DiskEdit',
    component: () => import('@/views/DiskForm.vue'),
    meta: { title: '编辑磁盘', requiresAuth: true },
  },
];
```

- 路由名使用 PascalCase，路径使用 kebab-case。
- 页面组件使用动态懒加载 `() => import(...)`。
- `meta.requiresAuth` 标记需要认证的路由。

---

## 11. CRUD 标准工作流

当需要新增一个实体的 CRUD 页面时，按以下步骤执行：

### 步骤 1：查阅数据模型
在 `docs/schemas/` 下找到对应 `{entity}.jsonc`，确认字段定义和类型。

### 步骤 2：定义类型
在 `types/{entity}.ts` 中定义实体类型、创建/更新 DTO 类型。

### 步骤 3：创建 Service
在 `services/{entity}_service.ts` 中封装 API 调用。

### 步骤 4：创建 Store（按需）
如需要跨组件共享状态，在 `stores/{entity}.ts` 中创建 Store。

### 步骤 5：创建列表页
创建 `views/{Entity}List.vue`，包含搜索、表格、分页、删除。

### 步骤 6：创建表单页
创建 `views/{Entity}Form.vue`，包含表单校验、提交、回退。

### 步骤 7：注册路由
在 `routers/index.ts` 中注册新建和编辑路由。

### 步骤 8：类型检查
运行 `vue-tsc --noEmit` 确保无类型错误。

## 输出文件（CRUD 场景）
- `types/{entity}.ts`
- `services/{entity}_service.ts`
- `stores/{entity}.ts`（可选）
- `views/{Entity}List.vue`
- `views/{Entity}Form.vue`
- `routers/index.ts`（更新）

---

## 12. 测试规范

### 12.1 测试工具

| 类别 | 技术 |
|------|------|
| 单元测试 | Vitest |
| 组件测试 | @vue/test-utils |
| E2E 测试 | Playwright |

### 12.2 测试要求

- **关键页面**（登录、核心 CRUD、文件上传下载）必须有 E2E 测试
- **核心 composables 和 utils** 必须有单元测试
- **表单校验逻辑** 必须有单元测试覆盖所有校验规则
- 每个测试文件与被测文件同目录（co-location），文件名 `*.spec.ts` 或 `*.test.ts`

### 12.3 测试目录结构

```
web/src/
├── components/
│   └── FileUpload.spec.ts      # 组件测试
├── composables/
│   └── usePagination.test.ts   # composable 测试
├── utils/
│   └── format.test.ts          # 工具函数测试
└── views/
    └── __tests__/
        └── DiskList.test.ts    # 页面级测试
```

### 12.4 测试覆盖要求

| 测试类型 | 覆盖目标 | 说明 |
|---------|---------|------|
| 单元测试 | utils/composables 核心逻辑 | 边界条件、错误路径 |
| 组件测试 | 关键交互组件 | 渲染、事件、插槽 |
| E2E | 核心用户流程 | 登录→CRUD→登出 完整路径 |

---

## 13. 质量门槛

每次前端代码交付前必须满足：

| 检查项 | 标准 | 验证方式 |
|--------|------|----------|
| 类型安全 | 零 `any` 类型（或已标注 `HACK`） | `vue-tsc --noEmit` 无错误 |
| 构建通过 | 无编译错误 | `pnpm build` 或 `pnpm dev` 正常运行 |
| 语法检查 | 零 ESLint 错误 | `pnpm lint` |
| 组件行数 | 单组件 ≤ 300 行 | 人工检查 |
| 函数行数 | 单函数 ≤ 50 行 | 人工检查 |
| 错误处理 | 所有异步调用有 try-catch | Code Review |
| 无硬编码 | 配置、URL、密钥从环境变量/配置文件读取 | Code Review |
| 注释覆盖 | Service 和 Store 的公开方法有注释 | Code Review |
| 可访问性 | 图标按钮有 `aria-label`，表单控件有关联标签，焦点可见 | Code Review（见 §14） |
| 界面质量 | 无 §14.1 反模式速查表中的命中项 | Code Review（见 §14） |

---

## 14. 界面质量与可访问性

完整清单见 [refs/ui-quality-checklist.md](refs/ui-quality-checklist.md)（源自 Vercel Web Interface Guidelines，MIT，已适配 Vue 3 + Element Plus）。
以下为高频必查项，交付前逐条确认。

### 14.1 反模式速查

| 反模式 | 正确做法 |
|---|---|
| `<div @click>` 冒充按钮 | 改 `<button>` |
| 图标按钮无 `aria-label` | 补 `aria-label` |
| 表单输入无关联标签 | `el-form-item label` 或 `aria-label` |
| `outline: none` 无焦点替代 | 补 `:focus-visible` 样式 |
| `@paste` + `preventDefault` 禁粘贴 | 允许粘贴 |
| `transition: all` | 显式列属性 |
| 图片无 `width` / `height` | 补尺寸防 CLS |
| 大数组 `.map()` 不虚拟化 | `el-table-v2` / 虚拟列表 |
| 硬编码日期/数字格式 | `Intl.DateTimeFormat` / `Intl.NumberFormat` |
| flex 子项文本省略失效 | 补 `min-w-0` |
| 弹窗缺 `overscroll-behavior: contain` | 补，防滚动穿透 |
| 破坏性操作立即执行 | `ElMessageBox.confirm` 二次确认 |

### 14.2 Element Plus 特别注意

EP 已内置多数可访问性基础（表单标签关联、按钮键盘响应、焦点环、Message 的 `aria-live`），以下场景仍需手写：

- 纯图标按钮（`:icon` 无文字）→ 必补 `aria-label`
- `el-dialog` / `el-drawer` → 补 `overscroll-behavior: contain`
- 自定义按钮替代 EP 按钮 → 焦点样式与键盘事件需自行补全
- `el-table` 数字列 → 加 `tabular-nums`
- 深色模式 → `<html>` 设 `color-scheme: dark`，检查原生 `select`

### 14.3 路由与状态

- 筛选、分页、标签页等状态进 URL query（可刷新、可深链）
- 有未保存改动时用 `onBeforeRouteLeave` 拦截
- 导航用 `<router-link>`，保留 Ctrl/Cmd+点击新开标签能力

### 14.4 审查输出

按文件分组，`file:line` 格式，只写「问题 + 位置」，无寒暄：

```text
## src/views/DiskList.vue

src/views/DiskList.vue:42 - 图标按钮缺少 aria-label
src/views/DiskList.vue:58 - el-dialog 缺少 overscroll-behavior: contain
src/views/DiskList.vue:71 - transition: all → 显式列属性
```
