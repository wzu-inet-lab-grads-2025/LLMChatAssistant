# 数据模型: CLI客户端重构与验证

**功能**: CLI客户端重构与验证
**日期**: 2026-01-01
**状态**: 设计阶段

## 概述

本功能主要涉及目录结构重构，不引入新的数据实体。主要数据模型已存在于现有代码中，本文档记录这些模型以确保重构后数据结构保持一致。

## 核心数据模型

### 1. 会话 (Session)

**描述**: 表示一个用户与Agent的对话会话，包含会话状态、消息历史、上传文件等信息。

**Python类型定义**:
```python
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Optional

@dataclass
class Session:
    """用户会话数据模型"""

    # 基本属性
    session_id: str                    # 会话唯一标识 (UUID)
    client_type: str                   # 客户端类型: "cli" | "web" | "desktop"
    user_id: str                       # 用户标识
    created_at: datetime               # 创建时间

    # 会话状态
    messages: List["Message"] = field(default_factory=list)  # 消息历史
    uploaded_files: List["FileMetadata"] = field(default_factory=list)  # 已上传文件
    current_model: str = "glm-4-flash"  # 当前使用的模型

    # 元数据
    metadata: Dict = field(default_factory=dict)  # 其他元数据
```

**验证规则**:
- `session_id`: 必须是有效的UUID字符串
- `client_type`: 必须是 "cli"、"web" 或 "desktop" 之一
- `user_id`: 不能为空字符串
- `created_at`: 必须是有效的datetime对象
- `current_model`: 必须是有效的模型名称（如 "glm-4-flash", "glm-4.5-flash"）

**生命周期**:
- 创建: 用户启动客户端并连接到服务器时创建
- 更新: 每次发送/接收消息时更新
- 切换: 用户使用 `/switch` 命令时切换到其他会话
- 删除: 用户使用 `/delete` 命令时删除会话

### 2. 消息 (Message)

**描述**: 表示会话中的一条消息，可以是用户消息、助手回复或系统消息。

**Python类型定义**:
```python
@dataclass
class Message:
    """消息数据模型"""

    # 基本属性
    role: str                          # "user" | "assistant" | "system"
    content: str                       # 消息内容
    timestamp: datetime                # 时间戳

    # 可选属性
    tool_calls: Optional[List["ToolCall"]] = None  # 工具调用记录（可选）
    metadata: Dict = field(default_factory=dict)    # 元数据
```

**验证规则**:
- `role`: 必须是 "user"、"assistant" 或 "system" 之一
- `content`: 不能为空字符串（除了某些系统消息）
- `timestamp`: 必须是有效的datetime对象
- `tool_calls`: 仅当 role="assistant" 时可能存在

**消息类型示例**:
- 用户消息: `role="user", content="你好"`
- 助手回复: `role="assistant", content="你好！有什么我可以帮助你的吗？"`
- 系统消息: `role="system", content="欢迎连接到LLMChatAssistant服务器"`
- Agent思考: `role="assistant", content="[思考中...]", tool_calls=[...]`

### 3. 工具调用 (ToolCall)

**描述**: 记录Agent调用工具的详细信息。

**Python类型定义**:
```python
@dataclass
class ToolCall:
    """工具调用数据模型"""

    # 工具信息
    tool_name: str                     # 工具名称 (e.g., "semantic_search")
    arguments: Dict                    # 工具参数

    # 执行结果
    result: Optional[str] = None       # 执行结果（成功时）
    error: Optional[str] = None        # 错误信息（失败时）
    status: str = "pending"            # "pending" | "success" | "failed"

    # 时间信息
    duration_ms: Optional[float] = None  # 执行耗时（毫秒）
    timestamp: datetime = field(default_factory=datetime.now)
```

**验证规则**:
- `tool_name`: 必须是有效的工具名称（参见工具清单）
- `arguments`: 必须符合工具的参数定义
- `status`: 必须是 "pending"、"success" 或 "failed" 之一
- `duration_ms`: 必须是正数（如果存在）

**工具调用示例**:
```python
ToolCall(
    tool_name="semantic_search",
    arguments={"query": "数据库配置", "top_k": 5},
    result="config.yaml",
    status="success",
    duration_ms=125.5
)
```

### 4. 文件元数据 (FileMetadata)

**描述**: 记录上传文件的元数据信息。

**Python类型定义**:
```python
@dataclass
class FileMetadata:
    """文件元数据模型"""

    # 文件标识
    file_id: str                       # 文件唯一标识 (UUID)
    filename: str                      # 原始文件名
    size: int                          # 文件大小（字节）

    # 存储信息
    file_path: str                     # 服务器存储路径
    upload_time: datetime              # 上传时间

    # 索引信息
    indexed: bool = False              # 是否已创建向量索引
    index_path: Optional[str] = None   # 索引文件路径（如果已索引）

    # 用户说明
    user_note: Optional[str] = None    # 用户上传时附加的说明
```

**验证规则**:
- `file_id`: 必须是有效的UUID字符串
- `filename`: 不能为空，不能包含路径分隔符
- `size`: 必须 ≤ 10MB (10485760 字节)
- `file_path`: 必须在白名单范围内
- `indexed`: 布尔值

**文件类型限制**:
- 仅允许文本文件（.txt, .md, .py, .yaml, .json等）
- 禁止可执行文件（.exe, .sh, .bat）
- 文件大小限制：10MB

### 5. 客户端配置 (ClientConfig)

**描述**: 客户端的配置信息。

**Python类型定义**:
```python
@dataclass
class ClientConfig:
    """客户端配置模型"""

    # 服务器连接配置
    server_host: str = "127.0.0.1"     # 服务器地址
    server_port: int = 9999            # 服务器端口
    rdt_port: int = 9998               # RDT端口
    timeout: int = 30                  # 连接超时（秒）

    # 连接参数
    auto_reconnect: bool = True        # 自动重连
    max_retries: int = 3               # 最大重试次数

    # 客户端配置
    default_model: str = "glm-4-flash" # 默认模型
    max_file_size: int = 10485760      # 最大文件大小（10MB）
    log_level: str = "INFO"            # 日志级别

    # UI配置
    terminal_type: str = "auto"        # "auto" | "vscode" | "standard"
    stream_speed: float = 0.05         # 流式输出延迟（秒）
    enable_colors: bool = True         # 启用颜色
```

**配置文件加载顺序**（从高到低）:
1. 命令行参数（`--host`, `--port`等）
2. 当前目录配置文件（`./config/config.yaml`）
3. 用户目录配置文件（`~/.llmchat/config.yaml`）
4. 默认配置（内置在代码中）

## 数据流

### 会话创建流程

```
用户启动客户端
    ↓
连接到服务器 (TCP:9999)
    ↓
服务器创建新会话
    ↓
返回会话ID和欢迎消息
    ↓
客户端保存会话状态
```

### 消息发送流程

```
用户输入消息
    ↓
客户端通过NPLT协议发送到服务器
    ↓
服务器接收并处理
    ↓
Agent执行（可能调用工具）
    ↓
服务器通过NPLT协议返回回复（流式）
    ↓
客户端显示消息
    ↓
更新会话历史
```

### 文件上传流程

```
用户使用 /upload 命令
    ↓
客户端通过NPLT协议上传文件
    ↓
服务器接收文件并保存
    ↓
服务器自动创建向量索引
    ↓
服务器返回文件元数据
    ↓
客户端更新会话的uploaded_files
```

## 数据持久化

### 服务器端

- **会话存储**: 内存（可扩展为Redis）
- **文件存储**: `storage/uploads/`
- **向量索引**: `storage/vectors/`
- **日志**: `logs/`

### 客户端

- **配置文件**: `clients/cli/config/config.yaml`
- **本地日志**: `logs/`（与服务器共享）
- **无状态**: 客户端不持久化会话状态，由服务器管理

## 数据一致性

### 会话状态同步

- 客户端和服务器通过NPLT协议保持会话状态同步
- 每次消息交换后更新本地会话状态
- 切换会话时从服务器获取完整历史

### 协议版本检查

- 连接时验证客户端和服务器协议版本
- 主版本号不同时拒绝连接
- 次版本号向后兼容

## 重构影响分析

### 无影响

本重构不改变任何数据模型的结构，仅改变代码的组织方式：
- 数据模型定义保持不变
- NPLT和RDT协议格式保持不变
- 会话、消息、文件元数据的结构保持不变

### 测试验证

为确保重构后数据模型一致性，需要：
1. 测试所有涉及数据模型的功能
2. 验证序列化/反序列化正确性
3. 检查数据迁移（如果有）

## 附录

### 支持的模型列表

- `glm-4-flash`: 智谱AI免费模型（推荐用于测试）
- `glm-4.5-flash`: 智谱AI免费模型（性能更好）
- `glm-4`: 智谱AI付费模型（生产环境）

### 工具清单

参见项目章程v1.6.0的工具清单规范：
- sys_monitor: 系统资源监控
- command_executor: 执行系统命令
- semantic_search: 语义检索
- file_download: 文件下载准备
- file_upload: 文件索引管理

### 客户端类型

- `cli`: 命令行客户端（Python直接运行）
- `web`: Web客户端（由服务器提供）
- `desktop`: Desktop客户端（PyInstaller打包）

---

**下一步**: 创建API契约文档 ([contracts/](./contracts/))
