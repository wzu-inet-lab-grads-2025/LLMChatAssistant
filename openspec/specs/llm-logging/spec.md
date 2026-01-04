# llm-logging Specification

## Purpose
TBD - created by archiving change improve-logging. Update Purpose after archive.
## 需求
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

