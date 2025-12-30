# 文件工具接口契约

**功能**: 003-file-tools-integration
**创建时间**: 2025-12-30

## 概述

本文档定义了三个文件操作工具的接口契约，包括方法签名、参数、返回值和错误处理。

---

## 1. FileUploadTool（文件上传工具）

### 1.1 工具元数据

```python
class FileUploadTool(Tool):
    name: str = "file_upload"
    description: str = "接收并保存用户上传的文件，支持自动索引"
    timeout: int = 30  # 上传+索引超时时间（秒）
```

### 1.2 execute() 方法签名

```python
def execute(
    self,
    filename: str,
    content: str,
    content_type: str = "text/plain",
    **kwargs
) -> ToolExecutionResult
```

### 1.3 参数

| 参数名 | 类型 | 必填 | 描述 | 验证规则 |
|--------|------|------|------|----------|
| filename | str | 是 | 原始文件名 | 不能包含路径遍历字符（../、..\\），不能为空 |
| content | str | 是 | 文件内容（Base64编码或纯文本） | 大小 ≤ 10MB |
| content_type | str | 否 | MIME类型 | 默认 "text/plain"，必须为文本类型 |

### 1.4 返回值

**成功时** (ToolExecutionResult):

```python
ToolExecutionResult(
    success=True,
    output=json.dumps({
        "file_id": "550e8400-e29b-41d4-a716-446655440000",
        "filename": "config.yaml",
        "size": 1024,
        "storage_path": "storage/uploads/550e8400/.../config.yaml",
        "indexed": True,
        "message": "文件已上传并建立索引"
    }),
    error=None,
    duration=5.2
)
```

**失败时** (ToolExecutionResult):

```python
# 文件过大
ToolExecutionResult(
    success=False,
    output="",
    error="文件大小超过限制 (10485760 > 10485760)"
)

# 类型不支持
ToolExecutionResult(
    success=False,
    output="",
    error="不支持的文件类型: application/x-executable (仅支持文本文件)"
)

# 路径遍历
ToolExecutionResult(
    success=False,
    output="",
    error="文件名包含非法字符: ../"
)
```

### 1.5 验证规则

```python
def validate_args(
    self,
    filename: str,
    content: str,
    content_type: str = "text/plain",
    **kwargs
) -> tuple[bool, str]:
    # 1. 文件名验证
    if "../" in filename or "..\\" in filename:
        return False, "文件名包含非法字符: ../"

    # 2. 内容大小验证
    content_bytes = content.encode('utf-8') if isinstance(content, str) else content
    if len(content_bytes) > 10 * 1024 * 1024:
        return False, f"文件大小超过限制 ({len(content_bytes)} > 10485760)"

    # 3. 内容类型验证
    allowed_types = ['text/plain', 'text/html', 'application/json', 'application/yaml', 'application/xml']
    if content_type not in allowed_types and not content_type.startswith('text/'):
        return False, f"不支持的文件类型: {content_type}"

    return True, ""
```

### 1.6 使用示例

**用户输入**: "上传文件 config.yaml"
**Agent 调用**:
```python
file_upload_tool.execute(
    filename="config.yaml",
    content="server:\n  port: 8080",
    content_type="application/yaml"
)
```

---

## 2. FileDownloadTool（文件下载工具）

### 2.1 工具元数据

```python
class FileDownloadTool(Tool):
    name: str = "file_download"
    description: str = "将服务器文件发送给用户下载"
    timeout: int = 20  # 下载超时时间（秒）
```

### 2.2 execute() 方法签名

```python
def execute(
    self,
    file_path: str,
    **kwargs
) -> ToolExecutionResult
```

### 2.3 参数

| 参数名 | 类型 | 必填 | 描述 | 验证规则 |
|--------|------|------|------|----------|
| file_path | str | 是 | 文件路径（绝对或相对） | 必须通过 PathValidator 验证 |

### 2.4 返回值

**成功时** (ToolExecutionResult):

```python
ToolExecutionResult(
    success=True,
    output=json.dumps({
        "file_id": "550e8400-e29b-41d4-a716-446655440000",
        "filename": "config.yaml",
        "size": 1024,
        "status": "offered",
        "message": "已向用户发送下载提议"
    }),
    error=None,
    duration=0.5
)
```

**失败时** (ToolExecutionResult):

```python
# 文件不存在
ToolExecutionResult(
    success=False,
    output="",
    error="文件不存在: /path/to/file"
)

# 路径越界
ToolExecutionResult(
    success=False,
    output="",
    error="路径不在白名单中: /etc/passwd"
)

# 黑名单匹配
ToolExecutionResult(
    success=False,
    output="",
    error="路径匹配禁止模式: */.env"
)
```

### 2.5 验证规则

```python
def validate_args(
    self,
    file_path: str,
    **kwargs
) -> tuple[bool, str]:
    # 1. 路径白名单验证
    allowed, msg = self.path_validator.is_allowed(file_path)
    if not allowed:
        return False, msg

    # 2. 文件存在性验证
    if not os.path.exists(file_path):
        return False, f"文件不存在: {file_path}"

    # 3. 路径规范化
    normalized = os.path.normpath(file_path)
    if normalized != file_path:
        return False, f"路径已规范化: {normalized}"

    return True, ""
```

### 2.6 NPLT 协议交互

**下载提议** (DOWNLOAD_OFFER):
```python
{
    "file_id": "550e8400-e29b-41d4-a716-446655440000",
    "filename": "config.yaml",
    "size": 1024
}
```

**文件数据** (FILE_DATA):
- 分块传输，每块最大 65535 字节
- 等待用户确认后再传输

### 2.7 使用示例

**用户输入**: "把配置文件发给我"
**Agent 调用**:
```python
file_download_tool.execute(
    file_path="/home/zhoutianyu/tmp/LLMChatAssistant/storage/uploads/550e8400/config.yaml"
)
```

---

## 3. FileSemanticSearchTool（文件语义检索工具）

### 3.1 工具元数据

```python
class FileSemanticSearchTool(Tool):
    name: str = "file_semantic_search"
    description: str = "通过自然语言描述语义检索文件"
    timeout: int = 5  # 检索超时时间（秒）
```

### 3.2 execute() 方法签名

```python
def execute(
    self,
    query: str,
    top_k: int = 3,
    **kwargs
) -> ToolExecutionResult
```

### 3.3 参数

| 参数名 | 类型 | 必填 | 描述 | 验证规则 |
|--------|------|------|------|----------|
| query | str | 是 | 查询文本（自然语言描述） | 非空字符串 |
| top_k | int | 否 | 返回结果数量 | 范围 [1, 10]，默认 3 |

### 3.4 返回值

**成功时** (ToolExecutionResult):

```python
ToolExecutionResult(
    success=True,
    output=json.dumps({
        "message": "在 5 个已索引文件中找到 2 个相关结果",
        "results": [
            {
                "filename": "database_config.yaml",
                "filepath": "/home/config/database.yaml",
                "similarity": 0.92,
                "position": "chunk 1",
                "chunk": "database:\n  host: localhost\n  port: 5432"
            },
            {
                "filename": "README.md",
                "filepath": "/home/README.md",
                "similarity": 0.78,
                "position": "chunk 3",
                "chunk": "## 数据库配置\n使用 PostgreSQL 数据库..."
            }
        ]
    }),
    error=None,
    duration=1.2
)
```

**失败时** (ToolExecutionResult):

```python
# 无索引文件
ToolExecutionResult(
    success=True,
    output="当前没有已索引的文件。请确保白名单目录中有可索引的文件。",
    error=None
)

# 未找到结果
ToolExecutionResult(
    success=True,
    output="在 5 个已索引文件中没有找到相关内容。",
    error=None
)
```

### 3.5 验证规则

```python
def validate_args(
    self,
    query: str,
    top_k: int = 3,
    **kwargs
) -> tuple[bool, str]:
    # 1. 查询非空
    if not query or not query.strip():
        return False, "查询文本不能为空"

    # 2. top_k 范围验证
    if top_k < 1 or top_k > 10:
        return False, "top_k 必须在 1-10 之间"

    return True, ""
```

### 3.6 使用示例

**用户输入**: "搜索数据库配置文档"
**Agent 调用**:
```python
file_search_tool.execute(
    query="数据库配置",
    top_k=3
)
```

---

## 4. 串行工具调用示例

### 4.1 场景：先搜索再下载

**用户输入**: "把性能分析报告发给我"

**ReAct 循环执行**:

**第1轮 - 搜索文件**:
```python
# Agent 思考: 用户提到"性能分析报告"，需要先搜索文件
file_search_tool.execute(
    query="性能分析报告",
    top_k=3
)
# 返回: 找到文件 "/docs/perf_report.pdf"
```

**第2轮 - 下载文件**:
```python
# Agent 思考: 找到了文件，现在发送给用户
file_download_tool.execute(
    file_path="/docs/perf_report.pdf"
)
# 返回: 已发送下载提议
```

### 4.2 Agent 提示词示例

```markdown
## 文件操作场景

**文件上传**: 用户说"上传文件"、"发送文件给你"
  → file_upload

**文件下载**: 用户说"下载文件"、"发给我"、"把XX文件发给我"
  → file_download

**文件检索**: 用户说"搜索XX文件"、"找找关于XX的文档"、"有没有XX文档"
  → file_semantic_search

**串行调用示例**:

用户: "把性能分析报告发给我"
TOOL: file_semantic_search
ARGS: {"query": "性能分析报告", "top_k": 3}
# 结果: 找到 /docs/perf_report.pdf

TOOL: file_download
ARGS: {"file_path": "/docs/perf_report.pdf"}
# 结果: 已发送下载提议
```

---

## 5. 工具注册表

### 5.1 工具注册

在 `ReActAgent.__post_init__()` 中注册新工具:

```python
self.tools = {
    "command_executor": CommandTool(...),
    "sys_monitor": MonitorTool(),
    "rag_search": RAGTool(...),
    # 新增文件工具
    "file_upload": FileUploadTool(...),
    "file_download": FileDownloadTool(...),
    "file_semantic_search": FileSemanticSearchTool(...)
}
```

### 5.2 工具描述更新

在 `_think_and_decide()` 的系统提示词中添加:

```markdown
**步骤1: 识别查询类型**
- 系统资源查询（CPU/内存/磁盘）→ sys_monitor（优先）
- 具体命令名执行 → command_executor
- 文档/代码搜索 → rag_search
- 文件上传 → file_upload
- 文件下载 → file_download
- 文件语义检索 → file_semantic_search
- 问候/闲聊 → 直接回答
```

---

## 6. 错误处理契约

### 6.1 通用错误处理

所有工具必须：

1. **验证参数**: 在 `validate_args()` 中验证所有输入
2. **返回明确错误**: 错误消息必须中文且明确指出问题
3. **记录日志**: 所有操作记录到 `logs/file_operations.log`
4. **超时控制**: 超过 `timeout` 秒返回超时错误

### 6.2 错误消息格式

```python
error = {
    "type": "ValidationError | FileNotFoundError | SecurityError | TimeoutError",
    "message": "中文错误消息",
    "details": {
        "file_path": "...",
        "reason": "..."
    }
}
```

### 6.3 日志格式

```python
# 成功操作
[2025-12-30 12:34:56] [UPLOAD] file_id=xxx filename=config.yaml size=1024 status=success

# 失败操作
[2025-12-30 12:34:56] [DOWNLOAD] file_path=/etc/passwd status=denied reason="路径不在白名单中"
```

---

## 7. 性能要求

### 7.1 响应时间

| 操作 | 目标时间 (90th percentile) |
|------|---------------------------|
| 文件上传 (含索引) | ≤ 30 秒 (5MB 文件) |
| 文件下载 | ≤ 20 秒 (5MB 文件) |
| 语义检索 | ≤ 3 秒 |

### 7.2 并发支持

| 操作 | 并发限制 |
|------|----------|
| 文件上传 | ≤ 10 同时 |
| 文件下载 | ≤ 20 同时 |
| 语义检索 | ≤ 50 同时 |

---

## 8. 安全要求

### 8.1 路径验证

- 所有文件路径必须通过 `PathValidator.is_allowed()`
- 路径必须规范化（`os.path.normpath()`）
- 拒绝包含 `..` 的路径

### 8.2 文件验证

- 文件大小 ≤ 10MB
- 文件类型必须是文本类型
- 文件名不能包含特殊字符（`;`, `&`, `|`, `>`, `<`, `` ` ``, `$`, `(`, `)`）

### 8.3 审计要求

- 所有文件操作必须记录日志
- 日志包含：时间戳、操作类型、文件路径、用户、结果
- 访问被拒绝时记录原因

---

## 9. 测试契约

### 9.1 单元测试

每个工具必须有单元测试覆盖：

- `test_validate_args_success()`: 验证有效参数
- `test_validate_args_failure()`: 验证无效参数
- `test_execute_success()`: 验证成功执行
- `test_execute_failure()`: 验证失败处理
- `test_timeout()`: 验证超时控制

### 9.2 集成测试

测试场景：

- 文件上传 → 自动索引 → 语义检索 → 下载
- 路径遍历攻击防护
- 大文件拒绝
- 不支持类型拒绝
- 并发上传处理

---

## 10. 版本控制

- **当前版本**: v1.0
- **兼容性**: 向后兼容现有的 Tool 基类
- **变更日志**:
  - v1.0 (2025-12-30): 初始版本，定义三个文件工具接口
