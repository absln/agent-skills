# 类型定义与表单模板

> frontend-standards 技能的素材库。主文件 §7.3 / §8.1 保留契约约束与使用规则，完整代码在此，可直接复制到项目。

## 通用类型定义（types/common.ts）

> 信封 / 错误体 / 分页形状的唯一事实源是 `http-api-standards` §4–§6；此处只是 TS 映射，冲突以上游为准。

```typescript
// types/common.ts
// 信封 / 错误体 / 分页形状的唯一事实源是 http-api-standards §4–§6；此处只是 TS 映射，冲突以上游为准。

/** 请求参数：cursor 分页（新接口唯一选择） */
export interface CursorParams {
  cursor?: string | null;
  limit?: number;
  keyword?: string;
  sort_by?: string;
  sort_order?: 'asc' | 'desc';
}

/** 列表响应：具名列表键 + 游标。键名由调用点指定，禁止退化成 items/data/list */
export type ListResponse<K extends string, T> = { [P in K]: T[] } & {
  nextCursor: string | null;
  hasMore: boolean;
};
// type DiskList = ListResponse<'disks', Disk>    →  { disks: Disk[]; nextCursor; hasMore }

/** 单资源 / 命令响应：具名资源键 */
export type ItemResponse<K extends string, T> = { [P in K]: T };
// type DiskItem = ItemResponse<'disk', Disk>     →  { disk: Disk }
// type Removed  = ItemResponse<'removed', true>  →  { removed: true }

/**
 * offset 分页响应 —— 仅限历史接口与 el-pagination 兼容层
 * （见 refs/list-page-pattern.md）。新接口一律用 ListResponse，上游 §6 禁止泛化 items 键。
 */
export interface PageListResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}
```

## Element Plus 表单模板

```vue
<script setup lang="ts">
import { reactive, ref } from 'vue';
import type { FormInstance, FormRules } from 'element-plus';
import type { DiskCreate } from '@/types/disk';

const formRef = ref<FormInstance>();
const form = reactive<DiskCreate>({
  name: '',
  path: '',
  total_size: 0,
});

const rules: FormRules = {
  name: [
    { required: true, message: '请输入磁盘名称', trigger: 'blur' },
    { max: 50, message: '名称不超过50个字符', trigger: 'blur' },
  ],
  path: [
    { required: true, message: '请输入挂载路径', trigger: 'blur' },
  ],
  total_size: [
    { required: true, message: '请输入磁盘大小', trigger: 'blur' },
    { type: 'number', min: 1, message: '磁盘大小必须大于0', trigger: 'blur' },
  ],
};

async function handleSubmit() {
  if (!formRef.value) return;
  await formRef.value.validate();
  // 提交逻辑...
}
</script>
```
