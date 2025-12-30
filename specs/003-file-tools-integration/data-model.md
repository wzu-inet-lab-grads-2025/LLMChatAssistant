# 数据模型: 文件操作工具集成到 Agent

**功能**: 003-file-tools-integration
**创建时间**: 2025-12-30

## 实体定义

### 1. UploadedFile（上传文件）

**用途**: 代表用户上传到服务器的文件，包含文件元数据和索引信息。

**字段**:

| 字段名 | 类型 | 必填 | 描述 | 验证规则 |
|--------|------|------|------|----------|
| file_id | str | 是 | 文件唯一标识（UUID） | 自动生成，36字符 |
| filename | str | 是 | 原始文件名 | 不包含路径遍历字符（../、..\\） |
| size | int | 是 | 文件大小（字节） | ≤ 10MB (10485760 字节) |
| content_type | str | 是 | 内容类型（MIME类型） | 仅允许文本类型（text/*、application/json、application/yaml等） |
| storage_path | str | 是 | 存储路径 | 绝对路径，格式: storage/uploads/{file_id}/{filename} |
| uploaded_at | datetime | 是 | 上传时间 | ISO 8601 格式 |
| vector_index_id | str \| None | 否 | 关联的向量索引 ID | 如果已索引则为非空 |

**状态转换**:

```
[上传中] → [已保存] → [已索引] → [已删除]
             ↓           ↓
          [索引失败]   [待删除]
```

**关系**:
- 一个 UploadedFile 可以关联零个或一个向量索引（vector_index_id）
- 一个 UploadedFile 可以被零次或多次文件下载操作引用

**复用说明**: 此实体已在 `src/storage/files.py` 中实现，无需重新定义。

---

### 2. DownloadOffer（文件下载提议）

**用途**: 代表 Agent 向用户发送的文件下载提议，需要用户确认后才会传输实际文件数据。

**字段**:

| 字段名 | 类型 | 必填 | 描述 | 验证规则 |
|--------|------|------|------|----------|
| file_id | str | 是 | 文件唯一标识 | 必须对应一个已存在的 UploadedFile |
| filename | str | 是 | 文件名 | 从 UploadedFile.filename 复制 |
| size | int | 是 | 文件大小（字节） | 从 UploadedFile.size 复制 |
| offered_at | datetime | 是 | 提议时间 | ISO 8601 格式 |
| status | str | 是 | 提议状态 | 枚举: "pending"、"accepted"、"rejected"、"expired" |

**状态转换**:

```
[pending] → [accepted] → [transferred]
    ↓
[rejected]
    ↓
[expired]
```

**验证规则**:
- file_id 必须通过 PathValidator 验证（路径在白名单内，不在黑名单中）
- 文件必须存在于 storage/uploads/{file_id}/{filename}

**新增说明**: 这是一个新实体，需要在 FileDownloadTool 中实现。

---

### 3. FileSearchResult（文件检索结果）

**用途**: 代表语义检索的匹配结果，包含文件信息、匹配内容和相似度评分。

**字段**:

| 字段名 | 类型 | 必填 | 描述 | 验证规则 |
|--------|------|------|------|----------|
| file_path | str | 是 | 文件路径 | 绝对路径，通过 PathValidator 验证 |
| filename | str | 是 | 文件名 | 从 file_path 提取 |
| chunk | str | 是 | 匹配的内容片段 | 最多 200 个字符 |
| similarity | float | 是 | 相似度评分 | 范围 [0.0, 1.0]，通常 ≥ 0.3 才返回 |
| metadata | dict | 是 | 额外元数据 | 包含 position（位置）、filepath（路径）等 |

**验证规则**:
- similarity 必须 ≥ 0.3（相似度阈值）
- file_path 必须指向已索引的文件
- chunk 不能为空字符串

**复用说明**: 此实体类似于现有的 SearchResult（src/storage/vector_store.py），可能需要扩展。

---

### 4. ToolCallContext（工具调用上下文）

**用途**: 代表串行工具调用的上下文信息，用于在多步骤操作中维护状态。

**字段**:

| 字段名 | 类型 | 必填 | 描述 | 验证规则 |
|--------|------|------|------|----------|
| user_request | str | 是 | 用户原始请求 | 非空字符串 |
| tool_calls | list | 是 | 已执行的工具调用列表 | 每个 ToolCall 对象 |
| current_step | int | 是 | 当前步骤编号 | 从 1 开始，≤ 5 |
| max_steps | int | 是 | 最大步骤数 | 默认 5 |
| intermediate_results | dict | 否 | 中间结果存储 | 用于传递上一个工具的结果 |

**使用场景**:
- 第1步: FileSemanticSearchTool.execute() 返回文件路径 → 存储到 intermediate_results
- 第2步: FileDownloadTool.execute() 从 intermediate_results 读取文件路径 → 执行下载

**复用说明**: 此上下文由 ReAct 循环隐式维护（agent.py:242 中的 current_message），无需显式定义新实体。

---

## 数据流图

### 文件上传流程

```
[客户端]
   ↓ (NPLT: FILE_METADATA + FILE_DATA)
[FileUploadTool.execute()]
   ↓ (验证: 类型、大小)
[UploadedFile.create_from_content()]
   ↓ (保存到 storage/uploads/{file_id}/)
[IndexManager.ensure_indexed()]
   ↓ (创建向量索引)
[VectorStore.add()]
   ↓ (返回: file_id, metadata)
[客户端] ← (确认: 文件已上传并索引)
```

### 文件下载流程

```
[用户请求] "把配置文件发给我"
   ↓
[ReAct 循环]
   ↓ (思考: 需要哪个文件？)
[FileSemanticSearchTool.execute()] (可选，如果用户只描述文件)
   ↓ (返回: file_path)
[FileDownloadTool.execute()]
   ↓ (验证: PathValidator.is_allowed())
[DownloadOffer] (创建下载提议)
   ↓ (NPLT: DOWNLOAD_OFFER)
[客户端] (用户确认)
   ↓ (NPLT: FILE_DATA)
[客户端] ← (文件数据)
```

### 语义检索流程

```
[用户请求] "搜索数据库配置文档"
   ↓
[FileSemanticSearchTool.execute()]
   ↓ (LLM: embed(query))
[QueryVector]
   ↓ (VectorStore.search_all())
[FileSearchResult[]]
   ↓ (格式化输出)
[用户] ← (文件列表 + 匹配片段)
```

### 串行工具调用流程

```
[用户请求] "把性能分析报告发给我"
   ↓
[ReAct 循环 - 第1轮]
   ↓ (思考: 需要先搜索文件)
[FileSemanticSearchTool.execute(query="性能分析报告")]
   ↓ (结果: file_path="/docs/perf_report.pdf")
[更新 current_message] "找到文件，准备下载..."
   ↓
[ReAct 循环 - 第2轮]
   ↓ (思考: 现在可以下载)
[FileDownloadTool.execute(file_path="/docs/perf_report.pdf")]
   ↓ (结果: 发送下载提议)
[用户确认] → [文件传输]
```

---

## 存储模型

### 文件系统结构

```
storage/
├── uploads/                    # 用户上传的文件
│   ├── {file_id}/             # 每个文件一个目录
│   │   ├── {filename}         # 实际文件内容
│   │   └── metadata.json      # 文件元数据
│   └── ...
│
└── vectors/                    # 向量索引
    ├── {file_id}.index        # 单文件索引
    └── manifest.json          # 索引清单
```

### metadata.json 格式

```json
{
  "file_id": "550e8400-e29b-41d4-a716-446655440000",
  "filename": "config.yaml",
  "size": 1024,
  "content_type": "application/yaml",
  "storage_path": "/home/zhoutianyu/tmp/LLMChatAssistant/storage/uploads/550e8400-e29b-41d4-a716-446655440000/config.yaml",
  "uploaded_at": "2025-12-30T12:34:56",
  "vector_index_id": "idx_550e8400-e29b-41d4-a716-446655440000"
}
```

---

## 验证规则总结

### 文件上传验证

1. **文件名验证**: 不包含 `../`、`..\\`、`/`、`\\`
2. **文件大小验证**: `size ≤ 10485760` (10MB)
3. **内容类型验证**: `content_type.startswith('text/')` 或在允许的类型列表中
4. **存储路径验证**: 必须在 `storage/uploads/` 目录下

### 文件下载验证

1. **路径白名单验证**: `PathValidator.is_allowed(file_path)` 返回 True
2. **路径黑名单验证**: 文件路径不匹配任何禁止模式（如 `*/.env`、`*/.ssh/*`）
3. **路径规范化**: `os.path.normpath(file_path)` 处理 `..` 和 `.`
4. **文件存在性验证**: `os.path.exists(file_path)` 为 True

### 文件检索验证

1. **查询非空**: `query.strip() != ""`
2. **索引存在**: `len(VectorStore.list_files()) > 0`
3. **相似度阈值**: `result.similarity ≥ 0.3`

---

## 性能考虑

### 索引创建

- **文件大小**: 10MB 文件索引大约需要 5-10 秒（取决于 API 延迟）
- **并发限制**: 建议同时索引的文件数 ≤ 3
- **重试机制**: 索引失败时重试 1 次

### 语义检索

- **查询延迟**: 90% 的请求应在 3 秒内完成
- **结果数量**: 默认返回 top_k=3 个结果
- **缓存策略**: 不缓存，每次查询都计算新的 query vector

### 文件传输

- **上传速度**: 5MB 文件在 30 秒内完成（含索引）
- **下载速度**: 5MB 文件在 20 秒内完成
- **分块大小**: NPLT 协议最大 65535 字节/包

---

## 错误处理

### 文件上传错误

| 错误类型 | 错误消息 | HTTP 状态码 | 处理方式 |
|----------|----------|-------------|----------|
| 文件过大 | "文件大小超过限制 (10MB)" | 413 | 拒绝上传，提示用户 |
| 类型不支持 | "不支持的文件类型: .exe（仅支持文本文件）" | 415 | 拒绝上传，提示用户 |
| 路径遍历 | "文件名包含非法字符: ../" | 400 | 拒绝上传，提示用户 |
| 索引失败 | "文件索引失败: API 错误" | 500 | 文件已保存但未索引，允许手动重试 |

### 文件下载错误

| 错误类型 | 错误消息 | HTTP 状态码 | 处理方式 |
|----------|----------|-------------|----------|
| 文件不存在 | "文件不存在: /path/to/file" | 404 | 提示用户检查路径 |
| 路径越界 | "路径不在白名单中: /etc/passwd" | 403 | 拒绝访问，记录日志 |
| 黑名单匹配 | "路径匹配禁止模式: */.env" | 403 | 拒绝访问，记录日志 |
| 磁盘读取失败 | "无法读取文件: 权限不足" | 500 | 返回服务器错误 |

### 语义检索错误

| 错误类型 | 错误消息 | HTTP 状态码 | 处理方式 |
|----------|----------|-------------|----------|
| 查询为空 | "查询文本不能为空" | 400 | 提示用户输入查询 |
| 无索引文件 | "当前没有已索引的文件" | 404 | 提示用户先上传文件 |
| API 失败 | "语义检索失败: API 错误" | 500 | 返回服务器错误，记录日志 |

---

## 安全考虑

### 1. 路径遍历防护

- **问题**: 用户可能通过 `../../etc/passwd` 访问敏感文件
- **解决方案**: 使用 `PathValidator.is_allowed()` 验证所有路径，自动规范化路径

### 2. 文件类型验证

- **问题**: 用户可能上传恶意文件（.exe、.sh）
- **解决方案**: 验证 MIME 类型，仅允许文本类型和安全的文档类型

### 3. 文件大小限制

- **问题**: 大文件可能导致磁盘耗尽或索引超时
- **解决方案**: 限制文件大小 ≤ 10MB，在上传前验证

### 4. 并发上传控制

- **问题**: 恶意用户可能并发上传大量文件
- **解决方案**: 限制并发上传数量（建议 ≤ 10），检查磁盘空间

### 5. 索引注入防护

- **问题**: 恶意文件可能包含特殊字符导致索引失败
- **解决方案**: 文件内容验证，索引时捕获异常并记录

---

## 审计日志

所有文件操作必须记录到 `logs/file_operations.log`，格式：

```
[2025-12-30 12:34:56] [UPLOAD] file_id=xxx filename=config.yaml size=1024 status=success
[2025-12-30 12:35:10] [DOWNLOAD] file_id=xxx filename=config.yaml user=agent status=success
[2025-12-30 12:35:20] [SEARCH] query="数据库配置" results=3 duration=1.2s
[2025-12-30 12:35:30] [ACCESS_DENIED] path=/etc/passwd reason="路径不在白名单中"
```

日志字段：
- 时间戳: ISO 8601 格式
- 操作类型: UPLOAD、DOWNLOAD、SEARCH、ACCESS_DENIED
- 上下文信息: file_id、filename、size、status、reason
- 执行结果: success、failed、denied
