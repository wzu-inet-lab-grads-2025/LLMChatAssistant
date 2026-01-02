# 项目 上下文

## 目的
智能网络运维助手是一个基于 NPLT 协议的 AI 对话和 RDT 可靠文件传输系统，旨在满足《高级计算机网络》课程大作业要求，同时提供实用的智能运维能力。

### 核心目标

#### 1. 应用层协议设计与实现（课程作业1）
- **NPLT 协议设计**: 设计并实现一个轻量级的二进制应用层协议（Network Protocol for LLM Transport）
  - 协议格式：Type(1B) + Seq(2B) + Len(2B) + Data(<=64KB)
  - 支持多种消息类型：聊天文本、Agent思考、文件传输、会话管理等
  - 心跳机制保持连接活性（默认90秒间隔，180秒超时）
  - 流式输出支持（实时显示AI生成内容）

- **实时AI对话应用**:
  - 客户端-服务器实时双向通信
  - 流式文本传输（边生成边显示）
  - Agent状态实时通知（思考、工具调用、生成中）
  - 会话历史管理和持久化

#### 2. 可靠数据传输协议设计与实现（课程作业2）
- **RDT 协议设计**: 设计并实现基于滑动窗口的可靠数据传输协议
  - 协议格式：Seq(2B) + Check(2B) + Data(<=1024B)
  - 运行在 UDP 之上，提供可靠传输
  - 滑动窗口大小：5，超时时间：0.1秒
  - CRC16 校验和确保数据完整性
  - 支持超时重传和乱序处理

- **可靠文件传输系统**:
  - 文件分块传输（每块最大1KB）
  - 断点续传支持
  - 大文件流式传输
  - 下载提议机制（服务端发起，客户端确认）

#### 3. 智能运维能力
- **ReAct Agent 智能体**:
  - 推理-行动循环模式
  - 多工具协同（命令执行、系统监控、语义搜索、文件操作）
  - 上下文感知（对话历史、上传文件）
  - 流式思考和状态通知

- **工具系统**:
  - `command_executor` - 安全的命令执行（路径白名单+黑名单）
  - `sys_monitor` - 系统资源监控（CPU、内存、磁盘）
  - `semantic_search` - 向量语义搜索（支持自动索引）
  - `file_upload` - 文件索引管理（支持代词引用）
  - `file_download` - 文件下载（支持RDT/HTTP混合）

#### 4. 会话管理系统
- **单用户多会话**:
  - 支持创建、切换、删除、列出多个独立会话
  - 每个会话独立的对话历史和上传文件
  - 会话自动命名（第3轮对话后触发AI命名）

- **历史持久化**:
  - 对话历史自动保存到磁盘
  - 支持会话恢复和继续
  - 工具调用记录和结果保存
  - 文件引用跨对话持久化

#### 5. 多客户端支持（架构设计）
- **CLI 客户端** (✅ 已完整实现):
  - 命令行界面（rich + prompt_toolkit）
  - NPLT 协议客户端（TCP连接、心跳、消息收发）
  - RDT 协议客户端（UDP文件下载）
  - 会话管理交互界面
  - 文件上传功能

- **Web/Desktop 客户端** (❌ 待实现):
  - HTTP 文件服务器代码已实现（未集成）
  - 预留 client_type 字段支持混合传输架构

### 技术价值
- **协议设计实践**: 从理论到实践，完整实现应用层协议和传输层协议
- **异步编程**: 使用 asyncio 实现高并发服务器
- **AI 集成**: 集成大语言模型，提供智能运维能力
- **向量检索**: FAISS 向量数据库，支持语义搜索
- **流式处理**: 流式输出和流式文件传输

## 技术栈
- **编程语言**: Python 3.11+
- **LLM 集成**: zai-sdk (智谱 AI), GLM-4-Flash (对话), Embedding-3-Pro (向量化)
- **向量存储**: numpy, faiss-cpu (语义搜索)
- **网络协议**: asyncio (异步IO), aiohttp (HTTP服务器,待集成)
- **终端UI**: rich, prompt-toolkit (支持中文输入法)
- **测试框架**: pytest, pytest-asyncio
- **构建工具**: hatchling, uv

## 项目约定

### 代码风格
- **语言偏好**: 默认使用中文，包括文档、注释、提交信息
- **格式化**: 遵循 PEP 8 规范
- **命名约定**:
  - 类名使用大驼峰（PascalCase）：`NPLTServer`, `ReActAgent`
  - 函数和变量使用小写下划线（snake_case）：`send_message`, `session_id`
  - 常量使用大写下划线（UPPER_SNAKE_CASE）：`MAX_DATA_LENGTH`, `PROTOCOL_VERSION`
- **注释**: 使用中文注释，关键逻辑必须添加注释说明

### 架构模式
- **协议分层**:
  - NPLT 协议（应用层）：Type(1B) + Seq(2B) + Len(2B) + Data(<=64KB)
  - RDT 协议（传输层）：Seq(2B) + Check(2B) + Data(<=1024B)
- **设计模式**:
  - ReAct Agent 模式（推理 + 行动）
  - 会话管理（单用户多会话支持）
  - 工具注册模式（CommandTool, MonitorTool, SemanticSearchTool）
- **代码结构**:
  - `clients/` - 客户端实现（cli完整实现, web/desktop待实现）
  - `server/` - 服务器实现（agent, nplt_server, rdt_server, storage, tools）
  - `shared/` - 共享代码（protocols, utils）
- **状态机设计**: NPLT 和 RDT 协议都使用明确的状态转移

### 测试策略
- **单元测试**: 每个模块都需要对应的单元测试
- **集成测试**: 重点测试协议交互和数据传输
- **真实实现**: 严格禁止虚假实现或占位符，所有功能必须真实可用
- **覆盖率要求**: 新功能测试覆盖率不低于 80%
- **测试文件位置**: `tests/` 目录下与源代码对应

### Git工作流
- **分支策略**:
  - `master` - 主分支，保持稳定可运行状态
  - 功能分支从 `master` 创建，完成后合并回 `master`
- **提交约定**: 使用约定式提交（Conventional Commits）
  - `feat:` 新功能
  - `fix:` 问题修复
  - `refactor:` 重构
  - `chore:` 构建/工具变更
  - `docs:` 文档更新
- **提交格式**: `<type>(<scope>): <description>`
  - 示例: `feat(storage): 实现 uploaded_files 持久化功能`
  - 示例: `fix(agent): 注入 session 对象到工具，修复文件引用问题`

## 领域上下文

### 前后端交互架构

#### 连接建立
1. **客户端发起连接** (CLI客户端已实现):
   - 使用 `asyncio.open_connection()` 建立TCP连接到服务器
   - 支持自动重连机制（最多3次，间隔2秒）
   - 连接成功后启动心跳线程和消息接收循环

2. **服务器接受连接**:
   - `asyncio.start_server()` 监听指定端口（默认9999）
   - 为每个连接创建独立的 `Session` 对象
   - 生成唯一 `session_id`（UUID格式）
   - 记录客户端地址和连接时间
   - 初始化 `ConversationHistory` 对象（加载已有历史或创建新历史）

#### 消息通信流程
1. **客户端发送消息** (CLI已实现):
   ```python
   # 构造 NPLTMessage 对象
   message = NPLTMessage(type=MessageType.CHAT_TEXT, seq=send_seq, data=data)
   # 编码并发送
   writer.write(message.encode())
   await writer.drain()
   # 更新发送序列号
   send_seq = (send_seq + 1) % 65536
   ```

2. **服务器接收处理**:
   - 读取消息头部（5字节固定长度）
   - 解析 Type, Seq, Len
   - 读取 Data 字段（根据Len确定长度）
   - 调用对应的处理器（chat_handler, model_switch_callback等）

3. **流式输出机制** (已实现):
   - 服务器先发送 `AGENT_THOUGHT` (stream_start) 标记
   - 持续发送 `CHAT_TEXT` 消息（每次10-50字符）
   - 发送空 `CHAT_TEXT` 消息作为结束标记
   - 客户端根据 `is_streaming` 状态实时显示内容

#### 心跳保活 (已实现)
- **客户端**: 每90秒发送一次心跳（可配置）
- **服务器**: 检查最后心跳时间，超过180秒则断开连接
- **超时处理**: 关闭连接，清理Session资源

#### 文件上传交互 (已实现)
1. **上传流程**:
   - 客户端发送 `FILE_METADATA` 消息（包含filename, file_size, file_id）
   - 服务器创建存储目录 `storage/uploads/{file_id}/`
   - 客户端分块发送 `FILE_DATA` 消息（每块最大64KB）
   - 服务器接收并写入文件
   - 上传完成后，服务器将文件元数据添加到 `session.uploaded_files`
   - 同步到 `conversation_history.uploaded_files`（持久化）

2. **文件索引管理** (已实现):
   - 自动触发向量索引（如果文件在白名单中）
   - 记录文件元数据：file_id, filename, file_path, size, uploaded_at, indexed
   - 支持自然语言代词引用：
     - "这个文件" → 获取最新1个文件
     - "这两个文件" → 获取最新2个文件
     - "之前上传的" → 排除最新，获取其余文件
     - "我上传的日志文件" → 按文件类型过滤

3. **文件引用机制** (已实现):
   - Agent工具通过 `session.uploaded_files` 访问文件列表
   - `file_upload` 工具支持灵活的文件查询和引用
   - 文件路径用于后续的语义搜索和内容分析

#### 聊天上下文管理 (已实现)
1. **ConversationHistory 结构**:
   ```python
   {
     "session_id": "uuid",
     "messages": [
       {
         "role": "user|assistant|system",
         "content": "消息内容",
         "timestamp": "2025-01-02T12:00:00",
         "tool_calls": [],  # 工具调用记录
         "metadata": {}     # 元数据
       }
     ],
     "uploaded_files": [],  # 上传的文件列表
     "created_at": "2025-01-02T12:00:00",
     "updated_at": "2025-01-02T12:00:00"
   }
   ```

2. **上下文获取**:
   - `get_context(num_messages=20)` 获取最近N条消息
   - 格式化为 LLM API 所需格式：`[{"role": "...", "content": "..."}]`
   - 包含工具调用的结果（作为assistant消息的一部分）

3. **历史持久化**:
   - 每次对话后自动调用 `conversation_history.save()`
   - 保存到 `storage/history/{session_id}.json`
   - 会话切换时加载对应的历史文件

4. **历史记录作用**:
   - 提供完整的对话上下文给 Agent
   - 支持会话的恢复和继续
   - 记录工具调用过程和结果
   - 关联上传的文件（支持跨对话文件引用）

#### 会话管理交互 (已实现)
1. **会话列表**:
   - 客户端发送 `SESSION_LIST` 请求
   - 服务器返回所有会话的JSON列表（session_id, name, message_count, created_at）

2. **切换会话**:
   - 客户端发送 `SESSION_SWITCH` (session_id)
   - 服务器更新 `session_manager.current_session_id`
   - 加载对应会话的 `ConversationHistory`
   - 返回确认消息和会话信息

3. **创建/删除会话**:
   - `SESSION_NEW`: 创建新会话，返回新的session_id
   - `SESSION_DELETE`: 删除指定会话及其历史记录文件

4. **自动命名** (已实现):
   - 第3轮对话后触发 AI 自动命名会话
   - 使用 LLM 根据对话内容生成会话名称

#### 文件下载交互 (已实现)
1. **CLI客户端（RDT协议）** (已实现):
   - Agent生成文件后，服务器创建RDT会话
   - 服务器发送 `DOWNLOAD_OFFER` 消息（包含filename, size, checksum, download_token）
   - 客户端使用token连接RDT服务器（UDP 9998端口）
   - 通过滑动窗口协议传输文件

2. **Web客户端（HTTP协议）** (代码已实现,未集成):
   - HTTPFileServer 类已实现 (http_server.py)
   - 提供下载接口: `GET /api/files/download/{file_id}`
   - 支持CORS跨域请求
   - **注意**: HTTP服务器未在 main.py 中启动,Web客户端尚未实现

#### 状态通知机制 (已实现)
- **Agent状态**: 实时发送思考、工具调用、生成状态
- **消息格式**: JSON格式字符串，包含 `type` 和 `content` 字段
- **状态类型**:
  - `thinking`: Agent正在思考
  - `tool_call`: 调用工具（包含工具名和参数）
  - `generating`: 正在生成回复

### NPLT 协议（Network Protocol for LLM Transport）
- 轻量级二进制协议，用于客户端-服务器实时通信
- 消息类型包括：CHAT_TEXT, AGENT_THOUGHT, DOWNLOAD_OFFER, FILE_DATA, FILE_METADATA, MODEL_SWITCH, SESSION_LIST, SESSION_SWITCH, SESSION_NEW, SESSION_DELETE 等
- 支持流式输出（STREAM_START, STREAM_CHUNK, STREAM_END）
- 心跳机制（默认 90 秒间隔）

### RDT 协议（Reliable Data Transfer）
- 基于滑动窗口的可靠数据传输协议
- 运行在 UDP 之上，提供可靠文件传输
- 窗口大小：5，超时：0.1 秒
- CRC16 校验和确保数据完整性

### ReAct Agent (已实现)
- 推理-行动循环模式
- 工具包括：
  - `command_executor` - 命令执行（支持路径验证）
  - `sys_monitor` - 系统监控（CPU、内存、磁盘）
  - `semantic_search` - 语义搜索（支持自动索引）
  - `file_upload` - 文件索引管理（代词引用）
  - `file_download` - 文件下载（支持RDT/HTTP混合）
- 支持流式思考和状态通知
- 通过 `session` 对象访问 `uploaded_files` 和上下文

### 会话管理 (已实现)
- **单用户多会话**: 支持一个用户创建和管理多个独立的对话会话
- **会话操作**: 创建新会话、切换会话、删除会话、列出所有会话
- **自动命名**: 第 3 轮对话后自动触发 AI 命名会话
- **历史持久化**: 会话历史自动保存到磁盘（storage/history/）
- **上下文隔离**: 不同会话之间的对话历史和文件完全隔离

### 客户端实现状态
- **CLI客户端**: ✅ 完整实现
  - NPLT客户端（连接、心跳、消息收发）
  - RDT客户端（文件下载）
  - 会话管理界面
  - 文件上传功能
  - 流式输出显示

- **Web客户端**: ❌ 未实现（目录为空）
  - HTTP服务器代码已实现，但未集成到 main.py
  - 前端界面待开发

- **Desktop客户端**: ❌ 未实现（目录为空）
  - 待开发

### 文件访问安全
- 路径白名单机制：仅允许访问指定目录
- 黑名单保护：禁止访问敏感文件（.ssh, .env, /etc/passwd 等）
- 自动索引：对白名单文件自动建立向量索引
- 命令输出限制：最大 100KB

## 重要约束
- **使用模式**: 单用户多历史会话，不涉及多用户并发访问
- **技术约束**:
  - Python 版本要求 >= 3.11
  - 单个数据包大小限制：NPLT <= 64KB, RDT <= 1KB
  - 最大客户端连接数：10（同一用户的不同客户端）
- **性能要求**:
  - 支持流式输出（实时显示 AI 生成内容）
  - 向量搜索响应时间 < 1 秒
  - 文件传输支持断点续传
- **安全约束**:
  - 严格的路径验证（白名单 + 黑名单）
  - 禁止命令注入（使用参数化执行）

## 外部依赖
- **智谱 AI API**: https://open.bigmodel.cn/
  - 模型：glm-4-flash（对话）, embedding-3-pro（向量化）
  - 需要 API Key（通过环境变量 ZAI_API_KEY 配置）
- **系统日志**: /var/log/*.log（仅读取）
- **配置文件**: config.yaml（项目根目录）
- **存储目录**:
  - `storage/vectors/` - 向量索引
  - `storage/uploads/` - 上传文件
  - `storage/history/` - 会话历史
  - `logs/` - 日志文件
