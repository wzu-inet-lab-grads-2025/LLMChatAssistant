# 大模型调用日志规范

## 新增需求

### 需求：LLM API 调用日志记录

服务器**必须**在 `llm.log` 中记录所有 LLM API 调用的详细信息，包括请求参数（模型、温度、最大 token 数、消息摘要）、完整响应内容（非流式）或流式输出的各个片段、调用耗时、token 使用情况以及所有错误信息。日志**应**使用合适的日志级别（DEBUG 用于详细信息，INFO 用于关键操作，ERROR 用于错误），以便于调试和问题追踪。

**Given** 服务器通过 LLM API 发起聊天请求
**When** 调用 `chat()` 或 `chat_stream()` 方法
**Then** 应在 `llm.log` 中记录请求信息，包括：
- 日志级别：DEBUG
- 内容：
  - 模型名称（model）
  - 温度参数（temperature）
  - 最大 token 数（max_tokens）
  - 消息数量（message count）
  - 每条消息的 role 和内容摘要（前100字符）
  - 调用时间戳

**示例**：
```
[2025-01-05 10:30:15] [DEBUG] [llm] LLM 请求开始
  模型: glm-4-flash
  Temperature: 0.7
  Max Tokens: 2000
  消息数: 3
  消息摘要:
    - system: 你是一个智能网络运维助手...
    - user: 帮我查看系统日志...
    - assistant: 好的，我来帮您查看...
```

### 场景：聊天响应日志（非流式）

**Given** LLM API 返回聊天响应（非流式）
**When** `chat()` 方法接收完整响应
**Then** 应在 `llm.log` 中记录响应信息，包括：
- 日志级别：INFO
- 内容：
  - 响应长度（字符数）
  - 响应摘要（前200字符）
  - 调用耗时（毫秒）
  - Token 使用情况（如果 API 返回）
  - 响应时间戳

**示例**：
```
[2025-01-05 10:30:16] [INFO] [llm] LLM 响应接收
  模型: glm-4-flash
  耗时: 1234ms
  响应长度: 256 字符
  Token 使用: prompt_tokens=150, completion_tokens=106, total=256
  响应摘要: 根据系统日志分析，发现以下问题...
```

### 场景：流式聊天日志

**Given** LLM API 返回流式聊天响应
**When** `chat_stream()` 方法接收流式数据块
**Then** 应在 `llm.log` 中记录流式输出信息，包括：
- 日志级别：
  - DEBUG：流式输出开始
  - DEBUG：每个数据块（可选，可能导致日志过多）
  - INFO：流式输出结束
- 内容：
  - 开始：流式输出开始标记、模型名称
  - 数据块：数据块长度、累计字符数
  - 结束：总字符数、总耗时、平均速度（字符/秒）、finish_reason

**示例**：
```
[2025-01-05 10:30:15] [DEBUG] [llm] 流式输出开始
  模型: glm-4-flash

[2025-01-05 10:30:15] [DEBUG] [llm] 流式数据块
  块大小: 25 字符
  累计: 25 字符

[2025-01-05 10:30:15] [DEBUG] [llm] 流式数据块
  块大小: 30 字符
  累计: 55 字符

[2025-01-05 10:30:16] [INFO] [llm] 流式输出结束
  模型: glm-4-flash
  总字符数: 256
  总耗时: 1234ms
  平均速度: 207 字符/秒
  完成原因: stop
```

### 场景：Embedding 请求日志

**Given** 服务器通过 LLM API 发起 embedding 请求
**When** 调用 `embed()` 方法
**Then** 应在 `llm.log` 中记录 embedding 信息，包括：
- 日志级别：INFO
- 内容：
  - 文本数量
  - 文本长度范围（最小/最大/平均）
  - 模型名称
  - 向量维度
  - 调用耗时

**示例**：
```
[2025-01-05 10:30:20] [INFO] [llm] Embedding 请求
  模型: embedding-3-pro
  文本数: 5
  长度范围: 最小=50, 最大=200, 平均=120
  向量维度: 1024
  耗时: 234ms
```

### 场景：LLM API 错误日志

**Given** LLM API 调用失败
**When** 捕获到异常
**Then** 应在 `llm.log` 中记录错误信息，包括：
- 日志级别：ERROR
- 内容：
  - 异常类型
  - 错误消息
  - 请求上下文（模型、参数摘要）
  - 堆栈信息（如果是不明错误）
  - 错误时间戳

**示例**：
```
[2025-01-05 10:30:25] [ERROR] [llm] LLM API 调用失败
  模型: glm-4-flash
  异常类型: APIError
  错误消息: Invalid API key
  请求参数: temperature=0.7, max_tokens=2000, message_count=3
  堆栈: Traceback (most recent call last):
    File "/path/to/zhipu.py", line 93, in chat
      ...
```

### 场景：模型切换日志

**Given** 用户切换 LLM 模型
**When** 调用 `set_model()` 方法
**Then** 应在 `llm.log` 中记录模型切换，包括：
- 日志级别：INFO
- 内容：
  - 旧模型名称
  - 新模型名称
  - 切换时间戳

**示例**：
```
[2025-01-05 10:30:30] [INFO] [llm] 模型切换
  从: glm-4-flash
  到: glm-4-plus
```

## 新增需求

### 需求：独立的 LLM 日志记录器

系统**必须**提供独立的 LLM 日志记录器，使用 `get_llm_logger()` 函数获取。日志记录器**应**使用 `llm` 作为 logger 名称，输出到 `logs/llm.log` 文件，默认级别为 INFO。系统**必须**支持通过 config.yaml 配置 LLM 日志级别、日志文件名和日志目录。

#### 场景：LLM 日志记录器初始化

**Given** 需要记录 LLM API 调用
**When** 初始化日志系统
**Then** 应使用独立的 LLM 日志记录器：
- Logger 名称：`llm`（或 `server.llm`）
- 日志文件：`logs/llm.log`
- 默认级别：INFO
- 支持 DEBUG 级别用于详细的请求/响应追踪

#### 场景：LLM 日志配置

**Given** 需要调整 LLM 日志详细程度
**When** 修改配置文件
**Then** 应支持通过 `config.yaml` 配置：
- `logging.llm.level`: LLM 日志级别（DEBUG/INFO/WARNING/ERROR）
- `logging.llm.log_file`: LLM 日志文件名（默认 `llm.log`）
- `logging.llm.log_dir`: LLM 日志目录（默认 `logs`）

## 新增需求

### 需求：统一的 LLM 日志工具函数

系统**应**提供统一的 LLM 日志工具函数，用于记录请求、响应、流式输出和错误。这些工具函数**必须**自动格式化日志内容、处理敏感信息过滤、提供一致的日志格式，并支持自定义 logger 实例。工具函数**应**包括：`log_llm_request()`、`log_llm_response()`、`log_llm_stream_start()`、`log_llm_stream_chunk()`、`log_llm_stream_end()` 和 `log_llm_error()`。

#### 场景：使用日志工具函数

**Given** 需要记录 LLM 请求
**When** 调用日志工具函数
**Then** 应提供统一的日志工具函数：
- `log_llm_request(logger, model, messages, **kwargs)`：记录请求
- `log_llm_response(logger, response, duration)`：记录响应
- `log_llm_stream_start(logger, model)`：记录流式开始
- `log_llm_stream_chunk(logger, chunk, accumulated)`：记录流式数据块
- `log_llm_stream_end(logger, total_chars, duration, finish_reason)`：记录流式结束
- `log_llm_error(logger, error, context)`：记录错误

这些工具函数应：
- 自动格式化日志内容
- 处理敏感信息过滤
- 提供一致的日志格式
- 支持自定义 logger 实例

## 实现备注

1. **日志级别策略**：
   - DEBUG：详细的请求/响应内容（开发调试）
   - INFO：关键操作和摘要（生产环境）
   - WARNING：可恢复的问题（如 token 限制）
   - ERROR：API 调用失败

2. **性能考虑**：
   - 避免在流式输出中记录每个 chunk（可能导致日志爆炸）
   - 使用批量记录策略（如每10个chunk记录一次）
   - 或者只在 DEBUG 级别记录详细 chunk

3. **敏感信息保护**：
   - 不记录完整的用户输入内容（只记录摘要）
   - 不记录 API key（即使是在错误日志中）
   - 过滤系统提示词（system message）中的敏感配置

4. **日志格式建议**：
   - 使用多行格式提高可读性
   - 使用缩进对齐相关字段
   - 包含时间戳和调用上下文

5. **可观测性增强**：
   - 为每次 API 调用生成唯一 ID（request_id）
   - 在请求和响应日志中使用相同的 ID，便于关联
   - 支持按用户或会话过滤日志（如果需要）
