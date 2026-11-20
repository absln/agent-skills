# 列表页标准结构

列表页的典型实现模板。结构固定为**搜索区 → 操作栏 → 表格 → 分页**四部分。

> **分页口径**：本模板的 `el-pagination` + `store.total` 属 **offset 兼容层**，仅用于历史接口（`PageListResponse`）。新接口走 cursor（`http-api-standards` §6），分页区改为「上一页 / 下一页」，状态从 Store 的 `nextCursor` / `hasMore` 取，不要读 `total`。

```vue
<template>
  <div class="disk-list">
    <!-- 搜索区域 -->
    <el-form :model="query" inline>
      <el-form-item label="关键词">
        <el-input v-model="query.keyword" placeholder="搜索…" clearable />
      </el-form-item>
      <el-form-item>
        <el-button type="primary" @click="handleSearch">搜索</el-button>
        <el-button @click="handleReset">重置</el-button>
      </el-form-item>
    </el-form>

    <!-- 操作栏 -->
    <div class="toolbar">
      <el-button type="primary" @click="handleCreate">新建</el-button>
    </div>

    <!-- 表格 -->
    <el-table :data="store.list" v-loading="store.loading" border stripe>
      <el-table-column prop="name" label="名称" />
      <el-table-column prop="path" label="路径" />
      <el-table-column label="操作" width="200">
        <template #default="{ row }">
          <el-button link type="primary" @click="handleEdit(row)">编辑</el-button>
          <el-button link type="danger" @click="handleDelete(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- 分页 -->
    <el-pagination
      v-model:current-page="query.page"
      v-model:page-size="query.page_size"
      :total="store.total"
      @change="handleSearch"
    />
  </div>
</template>
```

## 要点

- 表格 `v-loading` 必须绑定 Store 的 loading 状态
- 删除操作必须有 `el-message-box` 二次确认
- 查询条件同步到 URL query，保证可刷新、可深链
- 超过 50 条数据改用 `el-table-v2` 或虚拟列表
- 空数据时给出空状态提示，不渲染空白表格
- cursor 接口的「下一页」按钮须 `:disabled="!store.hasMore"`，不要用 `nextCursor != null` 自行推断
